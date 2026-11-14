# Module integration checklist

## Branch and ownership

| Module | Branch | Owned area |
| --- | --- | --- |
| 01 — Farm management | `feature/farm-module` | Farm profile and location workflows |
| 02 — NASA climate | `feature/nasa-data` | `backend/app/modules/nasa_data/` and climate source docs |
| 03 — Agro engine | `feature/agro-engine` | `backend/app/modules/agro_engine/` and crop catalog |
| 04 — Analytics | `feature/analytics` | Analytics and reporting UI |
| 05 — Integration | `feature/integration` | Shared contracts, core middleware/gateway, QA, CI, and integration docs |

Do not overwrite files owned by another module. Discuss contract changes with each affected owner before merging.

## Pull request checks

- Confirm the PR targets the team-designated integration branch. At the time this checklist was written, the remote contains only `feature/nasa-data`; `main` and `develop` are not available. Do not invent a production baseline or merge target. Establish `develop` from the agreed stable baseline before using it as the shared PR target.
- Keep all API routes under `/api/v1`, except `/health`.
- Validate request and response payloads against the shared JSON Schemas and corresponding Pydantic models.
- Preserve request IDs and return the canonical `ApiError` shape for errors.
- Keep ISO dates, decimal-degree coordinates, explicit measurement units, and nulls for missing observations.
- Label synthetic data with `is_demo_data: true`; keep NASA grid data distinct from on-farm sensor observations.
- Include decision-support limitations; do not claim guaranteed yield or profit outcomes.
- Run backend tests and the frontend production build.
- Confirm `.env`, secrets, credentials, local databases, and machine-specific paths are not committed.

## Suggested merge order

After the team establishes the shared `develop` branch, integrate the climate data foundation first, then farm management, agro intelligence, analytics, and finally integration changes that depend on the merged interfaces. Resolve conflicts in coordination with the relevant owners; do not merge over an active module branch.
