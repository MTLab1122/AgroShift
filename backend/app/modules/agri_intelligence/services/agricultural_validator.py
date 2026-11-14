from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    AgriculturalSource,
    AgroecologicalZone,
    Country,
    Crop,
    CropCalendar,
    CropVariety,
    District,
    EvidenceRecord,
    Locality,
    ProvinceState,
)
from ..models.enums import EvidenceStatus
from ..schemas.validation import (
    CropHistoryItem,
    CropSelector,
    CropValidationRequest,
    CropValidationResult,
    FarmContext,
    FarmValidationRequest,
    FarmValidationResult,
    FeasibilityStatus,
    SequenceValidationRequest,
    SequenceValidationResult,
    SourceReference,
    ValidationCheck,
)
from .calendar_validator import scope_matches, validate_calendar
from .crop_family_validator import validate_crop_family_transition
from .soil_validator import validate_soil
from .validation_rules import (
    SUPPORTED_EVIDENCE_STATUSES,
    combine_statuses,
    missing_check,
)
from .water_validator import validate_water


class AgriculturalValidator:
    def __init__(self, session: Session):
        self.session = session

    def validate_crop(
        self, request: CropValidationRequest | dict
    ) -> CropValidationResult:
        if not isinstance(request, CropValidationRequest):
            request = CropValidationRequest.model_validate(request)
        crop, error = self._resolve_crop(
            CropSelector(
                crop_id=request.crop_id,
                crop_identifier=request.crop_identifier,
                variety_id=request.variety_id,
            )
        )
        farm_id = request.farm_context.farm_id if request.farm_context else None
        if crop is None:
            check = missing_check(
                "CROP_IDENTIFICATION",
                error or "Crop could not be identified.",
                ["an active crop matching the supplied ID or exact slug/name"],
                inputs={
                    "crop_id": request.crop_id,
                    "crop_identifier": request.crop_identifier,
                },
            )
            return CropValidationResult(
                status=FeasibilityStatus.INSUFFICIENT_DATA,
                farm_id=farm_id,
                checks=[check],
                inputs=request.model_dump(mode="json", exclude={"climate"}),
                missing_information=check.missing_information,
            )

        checks = self._crop_checks(
            crop,
            request.variety_id,
            request.farm_context,
            request.upcoming_season,
            request.climate,
            request.prior_history,
        )
        evidence_ids = sorted({
            evidence_id for check in checks for evidence_id in check.evidence_record_ids
        })
        sources = self._source_references(evidence_ids)
        return CropValidationResult(
            status=combine_statuses([check.status for check in checks]),
            crop_id=crop.id,
            crop_slug=crop.slug,
            farm_id=farm_id,
            checks=checks,
            inputs={
                "farm_context": (
                    request.farm_context.model_dump(mode="json")
                    if request.farm_context else None
                ),
                "upcoming_season": request.upcoming_season,
                "climate_context": self._climate_metadata(request.climate),
                "prior_history_count": len(request.prior_history),
                "history_provenance_note": (
                    "History is caller-supplied and is not independently retrieved from Module 01."
                    if request.prior_history else None
                ),
            },
            evidence_record_ids=evidence_ids,
            source_references=sources,
            missing_information=sorted({
                missing for check in checks for missing in check.missing_information
            }),
            limitations=sorted({
                limitation for check in checks for limitation in check.limitations
            } | {
                "Module 01 farm data is not installed; request context is caller-supplied and not independently verified."
            }),
        )

    def validate_farm(
        self, request: FarmValidationRequest | dict
    ) -> FarmValidationResult:
        if not isinstance(request, FarmValidationRequest):
            request = FarmValidationRequest.model_validate(request)
        if not request.candidate_crops:
            return FarmValidationResult(
                farm_id=request.farm_id,
                results=[],
                status=FeasibilityStatus.INSUFFICIENT_DATA,
                missing_information=["candidate_crops"],
            )
        results = [
            self.validate_crop(
                CropValidationRequest(
                    crop_id=selector.crop_id,
                    crop_identifier=selector.crop_identifier,
                    variety_id=selector.variety_id,
                    farm_context=request.farm_context
                    or FarmContext(farm_id=request.farm_id),
                    upcoming_season=request.upcoming_season,
                    climate=request.climate,
                    prior_history=request.crop_history,
                )
            )
            for selector in request.candidate_crops
        ]
        return FarmValidationResult(
            farm_id=request.farm_id,
            results=results,
            status=combine_statuses([result.status for result in results]),
            missing_information=sorted({
                missing for result in results for missing in result.missing_information
            }),
        )

    def validate_sequence(
        self, request: SequenceValidationRequest | dict
    ) -> SequenceValidationResult:
        if not isinstance(request, SequenceValidationRequest):
            request = SequenceValidationRequest.model_validate(request)
        previous: list[tuple[Crop, CropVariety | None]] = []
        prior_history_items = list(request.prior_history)
        crop_results = []
        transition_checks = []
        unresolved_history = []
        for item in prior_history_items:
            history_crop, error = self._resolve_crop(item)
            if history_crop is None:
                unresolved_history.append(error or "unresolved prior crop")
                continue
            history_variety = (
                self.session.get(CropVariety, item.variety_id)
                if item.variety_id is not None else None
            )
            previous.append((history_crop, history_variety))
        for selector in request.sequence:
            crop, _error = self._resolve_crop(selector)
            if crop is None:
                unresolved = self.validate_crop(
                    CropValidationRequest(
                        crop_id=selector.crop_id,
                        crop_identifier=selector.crop_identifier,
                        variety_id=selector.variety_id,
                        farm_context=request.farm_context,
                        upcoming_season=request.upcoming_season,
                        climate=request.climate,
                        prior_history=prior_history_items,
                    )
                )
                crop_results.append(unresolved)
                continue
            variety = (
                self.session.get(CropVariety, selector.variety_id)
                if selector.variety_id is not None else None
            )
            crop_results.append(
                self.validate_crop(
                    CropValidationRequest(
                        crop_id=crop.id,
                        variety_id=selector.variety_id,
                        farm_context=request.farm_context,
                        upcoming_season=request.upcoming_season,
                        climate=request.climate,
                        prior_history=prior_history_items,
                    )
                )
            )
            if unresolved_history:
                transition_checks.append(
                    missing_check(
                        "CROP_FAMILY_ROTATION",
                        "Prior crop history could not be fully resolved.",
                        unresolved_history,
                    )
                )
                unresolved_history.clear()
            elif previous:
                transition_checks.append(
                    validate_crop_family_transition(
                        self.session, previous[-1:], crop, variety, request.farm_context
                    )
                )
            previous.append((crop, variety))
        statuses = [
            result.status for result in crop_results
        ] + [check.status for check in transition_checks]
        return SequenceValidationResult(
            status=combine_statuses(statuses),
            crop_results=crop_results,
            transition_results=transition_checks,
            missing_information=sorted({
                missing
                for result in crop_results for missing in result.missing_information
            } | {
                missing
                for check in transition_checks for missing in check.missing_information
            }),
            limitations=sorted({
                limitation
                for result in crop_results for limitation in result.limitations
            } | {
                limitation
                for check in transition_checks for limitation in check.limitations
            }),
        )

    def _crop_checks(
        self,
        crop: Crop,
        variety_id: int | None,
        farm: FarmContext | None,
        season: str | None,
        climate,
        prior_history: list[CropHistoryItem],
    ) -> list[ValidationCheck]:
        variety = self.session.get(CropVariety, variety_id) if variety_id else None
        if variety_id is not None and (variety is None or variety.crop_id != crop.id):
            identification = missing_check(
                "CROP_IDENTIFICATION",
                "The requested variety does not belong to the identified crop.",
                ["a variety ID belonging to the selected crop"],
                inputs={"crop_id": crop.id, "variety_id": variety_id},
            )
        else:
            identification = ValidationCheck(
                check_code="CROP_IDENTIFICATION",
                status=(
                    FeasibilityStatus.CONDITIONALLY_FEASIBLE
                    if crop.evidence_status is EvidenceStatus.PROVISIONAL
                    else (
                        FeasibilityStatus.FEASIBLE
                        if crop.evidence_status is EvidenceStatus.VERIFIED
                        else FeasibilityStatus.INSUFFICIENT_DATA
                    )
                ),
                detail="Crop identified by exact ID, slug, or case-insensitive common name.",
                inputs={
                    "crop_id": crop.id,
                    "slug": crop.slug,
                    "evidence_status": crop.evidence_status.value,
                },
                evidence_record_ids=(
                    [crop.primary_evidence_id]
                    if crop.primary_evidence_id is not None else []
                ),
                missing_information=(
                    ["verified crop identity or taxonomy"]
                    if crop.evidence_status not in SUPPORTED_EVIDENCE_STATUSES else []
                ),
                limitations=["Name normalization uses exact matches only; no fuzzy inference."],
            )

        previous = []
        history_missing = []
        for item in prior_history:
            absent_evidence = [
                evidence_id for evidence_id in item.evidence_record_ids
                if self.session.get(EvidenceRecord, evidence_id) is None
            ]
            if absent_evidence:
                history_missing.append(
                    f"existing evidence records for history item: {absent_evidence}"
                )
            previous_crop, error = self._resolve_crop(item)
            if previous_crop is None:
                history_missing.append(error or "unresolved crop-history item")
            else:
                previous_variety = (
                    self.session.get(CropVariety, item.variety_id)
                    if item.variety_id is not None else None
                )
                if previous_variety is not None and previous_variety.crop_id != previous_crop.id:
                    history_missing.append("history variety does not belong to its crop")
                else:
                    previous.append((previous_crop, previous_variety))
            if not item.source_record_id or not item.evidence_record_ids:
                history_missing.append(
                    "source record ID and evidence record IDs for caller-supplied crop history"
                )
        family_check = validate_crop_family_transition(
            self.session, previous[-1:], crop, variety, farm
        )
        if history_missing and family_check.status is not FeasibilityStatus.INFEASIBLE:
            family_check = family_check.model_copy(
                update={
                    "status": FeasibilityStatus.INSUFFICIENT_DATA,
                    "missing_information": sorted(
                        set(family_check.missing_information + history_missing)
                    ),
                }
            )

        duration_check = self._validate_duration(
            crop, variety, farm, season
        )
        pest_check = missing_check(
            "PEST_DISEASE_CONTINUITY",
            "Pest and disease continuity cannot be evaluated because no pest/disease evidence model is available.",
            ["supported pest and disease records for crop sequences"],
            limitations=["No pest or disease risk is inferred from crop identity alone."],
        )
        return [
            identification,
            self._geography_check(farm),
            validate_soil(self.session, crop.id, variety_id, farm),
            validate_water(self.session, crop.id, variety_id, farm),
            validate_calendar(
                self.session, crop.id, variety_id, farm, season
            ),
            duration_check,
            family_check,
            pest_check,
            self._climate_check(climate, farm),
        ]

    def _geography_check(self, farm: FarmContext | None) -> ValidationCheck:
        if farm is None:
            return missing_check(
                "GEOGRAPHY",
                "Farm geography was not supplied.",
                ["country, province, district, locality, or agroecological-zone ID"],
            )
        provided = {
            "country_id": farm.country_id,
            "province_state_id": farm.province_state_id,
            "district_id": farm.district_id,
            "locality_id": farm.locality_id,
            "agroecological_zone_id": farm.agroecological_zone_id,
        }
        if all(value is None for value in provided.values()):
            return missing_check(
                "GEOGRAPHY",
                "Farm geography was not supplied.",
                ["country, province, district, or agroecological-zone ID"],
            )
        errors = []
        country = self.session.get(Country, farm.country_id) if farm.country_id else None
        province = (
            self.session.get(ProvinceState, farm.province_state_id)
            if farm.province_state_id else None
        )
        district = self.session.get(District, farm.district_id) if farm.district_id else None
        locality = self.session.get(Locality, farm.locality_id) if farm.locality_id else None
        zone = (
            self.session.get(AgroecologicalZone, farm.agroecological_zone_id)
            if farm.agroecological_zone_id else None
        )
        if farm.country_id and country is None:
            errors.append("country_id does not identify a stored country")
        if farm.province_state_id and province is None:
            errors.append("province_state_id does not identify a stored province")
        if farm.district_id and district is None:
            errors.append("district_id does not identify a stored district")
        if farm.locality_id and locality is None:
            errors.append("locality_id does not identify a stored locality")
        if farm.agroecological_zone_id and zone is None:
            errors.append("agroecological_zone_id does not identify a stored zone")
        if province is not None and country is not None and province.country_id != country.id:
            errors.append("province_state_id belongs to a different country")
        if district is not None and province is not None and district.province_state_id != province.id:
            errors.append("district_id belongs to a different province")
        if district is not None and country is not None:
            district_province = self.session.get(ProvinceState, district.province_state_id)
            if district_province is not None and district_province.country_id != country.id:
                errors.append("district_id belongs to a different country")
        if locality is not None and district is not None and locality.district_id != district.id:
            errors.append("locality_id belongs to a different district")
        if locality is not None:
            locality_district = self.session.get(District, locality.district_id)
            if locality_district is not None:
                locality_province = self.session.get(
                    ProvinceState, locality_district.province_state_id
                )
                if province is not None and locality_district.province_state_id != province.id:
                    errors.append("locality_id belongs to a different province")
                if (
                    country is not None
                    and locality_province is not None
                    and locality_province.country_id != country.id
                ):
                    errors.append("locality_id belongs to a different country")
        return ValidationCheck(
            check_code="GEOGRAPHY",
            status=(
                FeasibilityStatus.INSUFFICIENT_DATA
                if errors else FeasibilityStatus.FEASIBLE
            ),
            detail=(
                "Supplied geographic IDs have inconsistent or missing database references."
                if errors
                else "Supplied geographic IDs resolve and the available administrative hierarchy is consistent."
            ),
            inputs=provided,
            rules_applied=["Validate supplied geographic IDs against Module 03 administrative records."],
            missing_information=errors,
            limitations=[
                "Module 01 farm location is not available; supplied location values are not independently verified."
            ],
        )

    def _validate_duration(
        self,
        crop: Crop,
        variety: CropVariety | None,
        farm: FarmContext | None,
        season: str | None,
    ) -> ValidationCheck:
        durations = []
        evidence_ids = []
        statuses = []
        if (
            variety is not None
            and variety.duration_days is not None
            and variety.evidence_status in SUPPORTED_EVIDENCE_STATUSES
            and variety.primary_evidence_id is not None
        ):
            durations.append(variety.duration_days)
            evidence_ids.append(variety.primary_evidence_id)
            statuses.append(variety.evidence_status)
        calendars = list(
            self.session.scalars(
                select(CropCalendar).where(
                    CropCalendar.crop_id == crop.id,
                    (CropCalendar.variety_id.is_(None))
                    | (CropCalendar.variety_id == (variety.id if variety else None)),
                    CropCalendar.growing_duration_days.is_not(None),
                )
            )
        )
        for calendar in calendars:
            if (
                calendar.evidence_status in SUPPORTED_EVIDENCE_STATUSES
                and calendar.primary_evidence_id is not None
                and farm is not None
                and (season is None or (
                    calendar.season is not None
                    and calendar.season.casefold() == season.casefold()
                ))
                and scope_matches(calendar, farm)[0]
            ):
                durations.append(calendar.growing_duration_days)
                evidence_ids.append(calendar.primary_evidence_id)
                statuses.append(calendar.evidence_status)
        if farm is None or farm.season_duration_days is None:
            return missing_check(
                "CROP_DURATION",
                "Crop duration cannot be compared with the available season duration.",
                ["farm_context.season_duration_days"],
                inputs={"upcoming_season": season},
            )
        if not durations:
            return missing_check(
                "CROP_DURATION",
                "No evidence-backed duration is available for this crop or variety.",
                ["VERIFIED or PROVISIONAL crop duration with primary evidence"],
                inputs={"season_duration_days": farm.season_duration_days},
            )
        if len(set(durations)) != 1:
            return missing_check(
                "CROP_DURATION",
                "Applicable evidence-backed crop durations disagree.",
                ["a consistent crop duration for the requested variety and geography"],
                inputs={"duration_values_days": sorted(set(durations))},
            )
        duration = durations[0]
        if duration > farm.season_duration_days:
            status = FeasibilityStatus.INFEASIBLE
        elif EvidenceStatus.PROVISIONAL in statuses:
            status = FeasibilityStatus.CONDITIONALLY_FEASIBLE
        else:
            status = FeasibilityStatus.FEASIBLE
        return ValidationCheck(
            check_code="CROP_DURATION",
            status=status,
            detail=(
                "Evidenced crop duration exceeds the supplied season duration."
                if status is FeasibilityStatus.INFEASIBLE
                else "Evidenced crop duration fits within the supplied season duration."
            ),
            inputs={
                "crop_duration_days": duration,
                "season_duration_days": farm.season_duration_days,
            },
            rules_applied=["Compare days directly; no duration conversion is applied."],
            evidence_record_ids=sorted(set(evidence_ids)),
            limitations=["Duration does not establish harvest yield or operational feasibility."],
        )

    @staticmethod
    def _climate_metadata(climate) -> dict | None:
        if climate is None:
            return None
        return {
            "farm_id": climate.farm_id,
            "source": climate.source,
            "product_or_dataset": climate.product_or_dataset,
            "start_date": climate.start_date,
            "end_date": climate.end_date,
            "retrieved_at": climate.retrieved_at,
            "is_demo_data": climate.is_demo_data,
            "missing_data": climate.missing_data.model_dump(),
            "parameters": [parameter.model_dump() for parameter in climate.parameters],
        }

    def _climate_check(self, climate, farm: FarmContext | None) -> ValidationCheck:
        if climate is None:
            return missing_check(
                "CLIMATE",
                "No Module 02 climate summary was supplied.",
                ["Module 02 climate summary for the relevant farm and period"],
            )
        metadata = self._climate_metadata(climate) or {}
        if farm is None or farm.farm_id is None or climate.farm_id != farm.farm_id:
            return missing_check(
                "CLIMATE",
                "Climate observations cannot be tied to the supplied farm context.",
                ["matching farm identity in farm and climate contexts"],
                inputs=metadata,
            )
        if climate.is_demo_data:
            return missing_check(
                "CLIMATE",
                "Synthetic demo climate is not used to determine agricultural feasibility.",
                ["non-demo climate observations for the relevant period"],
                inputs=metadata,
                limitations=["Demo climate is excluded from all feasibility conclusions."],
            )
        return missing_check(
            "CLIMATE",
            "Climate provenance and coverage were inspected, but no crop-response thresholds with compatible units and time bases are defined.",
            ["evidence-backed crop climate thresholds with compatible units and period"],
            inputs=metadata,
            limitations=[
                "No climate suitability score or crop-response conclusion is inferred from observed means alone."
            ],
        )

    def _resolve_crop(
        self, selector: CropSelector
    ) -> tuple[Crop | None, str | None]:
        crop = None
        if selector.crop_id is not None:
            crop = self.session.get(Crop, selector.crop_id)
        else:
            identifier = selector.crop_identifier.strip()
            crop = self.session.scalar(
                select(Crop).where(Crop.slug == identifier)
            )
            if crop is None:
                matches = list(
                    self.session.scalars(
                        select(Crop).where(
                            func.lower(Crop.common_name) == identifier.casefold()
                        )
                    )
                )
                if len(matches) == 1:
                    crop = matches[0]
                elif len(matches) > 1:
                    return None, "Crop common name is ambiguous; use an exact crop ID or slug."
        if crop is None or not crop.active:
            return None, "No active crop matches the supplied exact identifier."
        if selector.variety_id is not None:
            variety = self.session.get(CropVariety, selector.variety_id)
            if variety is None or variety.crop_id != crop.id:
                return None, "Variety does not exist or is not associated with the selected crop."
        return crop, None

    def _source_references(self, evidence_ids: list[int]) -> list[SourceReference]:
        references = {}
        for evidence_id in evidence_ids:
            evidence = self.session.get(EvidenceRecord, evidence_id)
            if evidence is None or evidence.source_id is None:
                continue
            source = self.session.get(AgriculturalSource, evidence.source_id)
            if source is not None:
                references[source.id] = SourceReference(
                    source_id=source.id,
                    organization=source.organization,
                    title=source.title,
                    publication_url=source.publication_url,
                    review_status=source.review_status,
                )
        return [references[key] for key in sorted(references)]
