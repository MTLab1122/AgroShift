# Module 03 API reference

All paths below are served by `backend.app.main`. Interactive OpenAPI docs are
available at `/docs` when the service is running.

## Crop data and validation

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/crops?active=true` | List crops; `active` may be `true`, `false`, or omitted to include both. |
| `GET` | `/api/v1/crops/{crop_id}` | Retrieve a crop and relationship identifiers. |
| `GET` | `/api/v1/crops/{crop_id}/calendar` | Retrieve persisted calendar records for a crop. |
| `POST` | `/api/v1/crops/validate` | Validate a crop against supplied context and stored evidence. |
| `POST` | `/api/v1/agriculture/validate-farm` | Evaluate caller-supplied candidate crops and history. |
| `POST` | `/api/v1/agriculture/validate-sequence` | Evaluate an ordered crop sequence and supplied prior history. |

Validation bodies use `CropValidationRequest`, `FarmValidationRequest`, and
`SequenceValidationRequest` from `schemas.validation`. Supply exactly one crop
reference (`crop_id` or `crop_identifier`) per selector. Farm measurements
require their units/basis where applicable. Farm/history data is caller
supplied; there is no Module 01 lookup in this repository.

## Recommendation scenarios

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/recommendations/generate` | Evaluate requested scenario types and persist scenario records. |
| `GET` | `/api/v1/recommendations/farm/{farm_id}?offset=0&limit=100` | List persisted scenarios for an opaque farm identifier. |
| `GET` | `/api/v1/recommendations/{scenario_id}` | Retrieve one scenario by UUID. |
| `POST` | `/api/v1/recommendations/compare` | Recalculate weighted scores and rank only eligible, completely scored scenarios. |
| `POST` | `/api/v1/recommendations/explain` | Produce and persist a status/evidence/missing-data explanation. |

Generation accepts `farm_id`, optional `farm_context`, `crop_history`,
`upcoming_season`, optional Module 02 `climate`, requested `scenario_types`,
and farmer `priorities`. It returns `RecommendationGenerationResult` with
scenario records, missing information, and limitations. The supported types
are `EXISTING_PRACTICE`, `PULSE_INCLUSIVE`, and `SOIL_COVER_FORAGE`.

Scenario generation is not an automatic planting instruction. A pulse
candidate is evaluated but not automatically selected. No local cover/forage
candidate is emitted without supported crop evidence. Incomplete evidence
produces `INSUFFICIENT_DATA`, not a fabricated score.

## Statuses and errors

Feasibility statuses are `FEASIBLE`, `CONDITIONALLY_FEASIBLE`, `INFEASIBLE`,
and `INSUFFICIENT_DATA`. Invalid requests return HTTP 422 using the shared
`ApiError` response. Missing records return 404. Database constraint conflicts
return HTTP 409 with a generic message and request identifier. Unexpected
errors return HTTP 500 without SQL or exception messages.

No authentication or authorization is implemented in this module. Do not
expose farm-specific endpoints directly to untrusted clients without an
external identity and ownership enforcement layer.
