from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Crop
from ..repositories import RecommendationScenarioRepository
from ..schemas.recommendations import (
    RecommendationGenerationRequest,
    RecommendationGenerationResult,
    RecommendationScenarioRead,
    ScenarioType,
)
from ..schemas.validation import (
    CropValidationRequest,
    FeasibilityStatus,
    FarmContext,
)
from .agricultural_validator import AgriculturalValidator
from .rotation_engine import RotationEngine
from .validation_rules import combine_statuses


_PULSE_SLUGS = ("chickpea", "lentil", "mung-bean")
ENGINE_VERSION = "module03-0.1.0"


class ScenarioGenerator:
    def __init__(self, session: Session):
        self.session = session
        self.validator = AgriculturalValidator(session)
        self.rotation_engine = RotationEngine(session)
        self.repository = RecommendationScenarioRepository(session)

    def generate(
        self, request: RecommendationGenerationRequest | dict
    ) -> RecommendationGenerationResult:
        if not isinstance(request, RecommendationGenerationRequest):
            request = RecommendationGenerationRequest.model_validate(request)
        farm = request.farm_context or FarmContext(farm_id=request.farm_id)
        records = []
        if ScenarioType.EXISTING_PRACTICE in request.scenario_types:
            records.append(self._existing_practice(request, farm))
        if ScenarioType.PULSE_INCLUSIVE in request.scenario_types:
            records.extend(self._pulse_candidates(request, farm))
        if ScenarioType.SOIL_COVER_FORAGE in request.scenario_types:
            records.append(self._cover_forage_candidate(request, farm))
        self.session.flush()
        return RecommendationGenerationResult(
            farm_id=request.farm_id,
            scenarios=[
                RecommendationScenarioRead.model_validate(record)
                for record in records
            ],
            missing_information=sorted({
                missing for record in records for missing in record.missing_information
            }),
            limitations=sorted({
                limitation for record in records for limitation in record.limitations
            } | {
                "Module 01 farm and crop-history interfaces are not present; all farm/history input is caller-supplied."
            }),
        )

    def _existing_practice(self, request, farm):
        history = request.crop_history
        if not history:
            return self.repository.create(
                self._base_record(
                    request,
                    ScenarioType.EXISTING_PRACTICE,
                    FeasibilityStatus.INSUFFICIENT_DATA,
                    missing=["Module 01 actual crop history"],
                    constraints=["BASELINE_ONLY_NOT_A_RECOMMENDATION"],
                )
            )
        sequence = self.rotation_engine.evaluate_sequence(
            {
                "sequence": [
                    item.model_dump(
                        include={"crop_id", "crop_identifier", "variety_id"},
                        exclude_none=True,
                    )
                    for item in history
                ],
                "prior_history": [],
                "farm_context": farm,
                "upcoming_season": request.upcoming_season,
                "climate": request.climate,
            }
        )
        repeated_ids = {}
        for item in history:
            if item.crop_id is not None:
                repeated_ids[item.crop_id] = repeated_ids.get(item.crop_id, 0) + 1
        repeat_flags = [
            f"Repeated crop ID {crop_id} occurs {count} times in supplied history; agronomic effect is not inferred."
            for crop_id, count in sorted(repeated_ids.items())
            if count > 1
        ]
        missing = list(sequence.missing_information)
        missing.extend(
            "source record ID and evidence record IDs for caller-supplied crop history"
            for item in history
            if not item.source_record_id or not item.evidence_record_ids
        )
        return self.repository.create(
            self._scenario_record(
                request=request,
                scenario_type=ScenarioType.EXISTING_PRACTICE,
                status=sequence.status,
                sequence=[item.model_dump(mode="json") for item in history],
                validation_results=[
                    result.model_dump(mode="json") for result in sequence.crop_results
                ] + [
                    result.model_dump(mode="json")
                    for result in sequence.transition_results
                ],
                evidence_references=self._evidence_references(sequence.crop_results),
                missing=missing,
                constraints=["BASELINE_ONLY_NOT_A_RECOMMENDATION"],
                risks=repeat_flags,
                duration_days=self._duration_map(sequence.crop_results),
            )
        )

    def _pulse_candidates(self, request, farm):
        crops = list(
            self.session.scalars(
                select(Crop).where(
                    Crop.slug.in_(_PULSE_SLUGS),
                    Crop.active.is_(True),
                ).order_by(Crop.slug)
            )
        )
        if not crops:
            return [
                self.repository.create(
                    self._base_record(
                        request,
                        ScenarioType.PULSE_INCLUSIVE,
                        FeasibilityStatus.INSUFFICIENT_DATA,
                        missing=["active crop records for chickpea, lentil, or mung bean"],
                        constraints=["No pulse crop is automatically selected."],
                    )
                )
            ]
        records = []
        for crop in crops:
            result = self.validator.validate_crop(
                CropValidationRequest(
                    crop_id=crop.id,
                    farm_context=farm,
                    upcoming_season=request.upcoming_season,
                    climate=request.climate,
                    prior_history=request.crop_history,
                )
            )
            decision = {
                "crop_id": crop.id,
                "slug": crop.slug,
                "decision": "NOT_AUTOMATICALLY_SELECTED",
                "validation_status": result.status.value,
                "reason": (
                    "Candidate was evaluated but requires explicit farmer and expert review."
                    if result.status is not FeasibilityStatus.INFEASIBLE
                    else "Candidate has at least one evidence-backed infeasibility."
                ),
                "missing_information": result.missing_information,
            }
            sequence = [
                item.model_dump(mode="json") for item in request.crop_history
            ] + [{"crop_id": crop.id, "slug": crop.slug, "candidate": True}]
            records.append(
                self.repository.create(
                    self._scenario_record(
                        request=request,
                        scenario_type=ScenarioType.PULSE_INCLUSIVE,
                        status=result.status,
                        sequence=sequence,
                        validation_results=[result.model_dump(mode="json")],
                        evidence_references=self._source_reference_payload(result),
                        candidate_decisions=[decision],
                        missing=result.missing_information,
                        constraints=[
                            "Candidate evaluation is not an automatic crop selection.",
                            "A locally validated pulse rotation rule is required before use as a recommendation.",
                        ],
                        limitations=result.limitations,
                    )
                )
            )
        return records

    def _cover_forage_candidate(self, request, _farm):
        return self.repository.create(
            self._base_record(
                request,
                ScenarioType.SOIL_COVER_FORAGE,
                FeasibilityStatus.INSUFFICIENT_DATA,
                missing=[
                    "evidence-supported local cover-crop or forage-crop candidate",
                    "establishment, water, duration, and harvest/termination data",
                ],
                constraints=[
                    "Harvested forage and non-harvested cover crops are distinct candidate types.",
                    "No candidate is selected without local evidence and sequence validation.",
                ],
                limitations=[
                    "No supported forage or cover-crop species is present in the Phase 01 seed."
                ],
            )
        )

    def _base_record(
        self,
        request,
        scenario_type,
        status,
        *,
        missing,
        constraints,
        limitations=None,
    ):
        return self._scenario_record(
            request=request,
            scenario_type=scenario_type,
            status=status,
            missing=missing,
            constraints=constraints,
            limitations=limitations,
        )

    def _scenario_record(
        self,
        *,
        request,
        scenario_type,
        status,
        sequence=None,
        validation_results=None,
        evidence_references=None,
        candidate_decisions=None,
        missing=None,
        constraints=None,
        risks=None,
        limitations=None,
        duration_days=None,
    ):
        farm = request.farm_context
        schedule = []
        windows = []
        if request.upcoming_season is not None:
            schedule.append({"season": request.upcoming_season})
        if farm is not None:
            if farm.planting_date is not None or farm.harvest_date is not None:
                windows.append({
                    "planting_date": farm.planting_date.isoformat()
                    if farm.planting_date else None,
                    "harvest_date": farm.harvest_date.isoformat()
                    if farm.harvest_date else None,
                })
        return {
            "scenario_id": str(uuid4()),
            "scenario_type": scenario_type,
            "farm_id": request.farm_id,
            "crop_sequence": sequence or [],
            "season_schedule": schedule,
            "planting_harvest_windows": windows,
            "duration_days": duration_days or {},
            "feasibility_status": status,
            "validation_results": validation_results or [],
            "evidence_references": evidence_references or [],
            "candidate_decisions": candidate_decisions or [],
            "benefits": [],
            "risks": risks or [],
            "constraints": constraints or [],
            "limitations": limitations or [],
            "missing_information": sorted(set(missing or [])),
            "priorities": request.priorities,
            "engine_version": ENGINE_VERSION,
        }

    @staticmethod
    def _evidence_references(results):
        return [
            reference.model_dump(mode="json")
            for result in results
            for reference in result.source_references
        ]

    @staticmethod
    def _source_reference_payload(result):
        return [
            {
                "evidence_record_ids": result.evidence_record_ids,
                "source": reference.model_dump(mode="json"),
            }
            for reference in result.source_references
        ]

    @staticmethod
    def _duration_map(results):
        return {
            str(result.crop_id): check.inputs["crop_duration_days"]
            for result in results
            for check in result.checks
            if check.check_code == "CROP_DURATION"
            and "crop_duration_days" in check.inputs
        }
