# Module 03 architecture and integration contracts

## Ownership

Module 03 owns agricultural reference facts and their provenance, as well as
the validation and scenario-evaluation logic that consumes them. Its layers
are:

1. SQLAlchemy models and Alembic migrations for durable reference and scenario
   data.
2. Pydantic schemas for persisted model contracts and request/response data.
3. Repositories for session-scoped database operations.
4. Services for crop/calendar/research operations, feasibility checks,
   scenario creation, scoring, and explanation.
5. FastAPI routers registered by `backend.app.main`.

The Module 03 services receive caller-owned SQLAlchemy sessions. API handlers
own transactions for scenario generation, comparison, and explanation.
SQLite foreign-key enforcement is enabled by the application engine.

## Cross-module contracts

### Module 02 climate

Validation and scenario request schemas accept Module 02's `ClimateSummary`.
Climate values are reported as inputs and are not converted into local soil
measurements, crop requirements, or undocumented suitability thresholds.
Current Phase 01 seeds do not contain climate-response requirements; climate
checks report insufficient evidence where no compatible, evidence-backed
rule exists.

### Module 01 farms and history

Module 01 is not present in this checkout. `FarmContext`, `farm_id`, and
`CropHistoryItem` are request contracts only. The caller must supply them;
Module 03 does not query Module 01, validate ownership, or claim that supplied
history is independently verified. Scenario responses record this missing
integration as a limitation. `farm_id` is an opaque caller-supplied string,
not a foreign key to a farm table.

### Module 04 visualization

Module 04 is not present. The API returns JSON response schemas suitable for
client consumption, but no Module 04 client, event bus, or visualization
integration is implemented or claimed.

## Request and transaction flow

Crop reads and validation are handled by `api.py`. Recommendation generation,
scenario retrieval, comparison, and explanation are handled by
`recommendations_api.py`. Scenario generation writes evaluation records in
one database transaction; comparison persists its calculated score and
weights; explanation persists the generated explanation. Constraint errors
return a sanitized HTTP 409 response. Missing records return 404 responses.

## Deployment and security boundaries

The API currently has no authentication, authorization, tenant isolation, or
farm ownership checks. Deploy behind a trusted authentication/authorization
layer before exposing it to untrusted clients. Configure `CORS_ORIGINS` as a
comma-separated allowlist of trusted origins. Wildcard CORS does not enable
credentialed requests; wildcard mixed with explicit origins is rejected.
Error responses do not include database exception text or SQL details.

The application database default is file-backed SQLite. Configure
`DATABASE_URL` for the deployment database and apply Alembic migrations before
serving requests. Production database backup, retention, access control, and
monitoring are deployment responsibilities.
