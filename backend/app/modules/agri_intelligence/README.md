# Module 03 — Agricultural Intelligence

Module 03 owns the agricultural reference-data layer, evidence provenance,
request-time crop/farm/sequence validation, and persisted scenario comparison
and explanation. Its implementation follows the unknown-preserving Phase 01
data policy described in the [Phase 01 guide](../../../../docs/agri-intelligence-phase-01.md).

## Components

- `models/`: SQLAlchemy 2.x crop, variety, calendar, requirement, source,
  evidence, geography, zone, rotation-rule, and recommendation-scenario models.
- `schemas/`: create/update/read contracts and request/result validation.
- `repositories/`: caller-session CRUD and scenario persistence.
- `services/`: database services; Phase 02 validators; Phase 03 scenario
  generation and rotation-rule evaluation; Phase 04 weighting, comparison,
  and explanation.
- `seeds/`: idempotent evidence/source and reference-data seeds.
- `api.py`, `recommendations_api.py`: Module 03 HTTP routes.

Module 03 uses the existing SQLAlchemy session infrastructure and Alembic
history. Repositories/services accept a caller-owned `Session`; transaction
commit/rollback belongs to the caller. API handlers manage transactions for
persisted scenario operations.

## Interfaces

Module 02's `ClimateSummary` schema is accepted as optional climate context.
The validator does not infer a farm's soil or water properties from climate.
The repository does not contain Module 01's farm/history service or Module
04's visualization client. Farm context and crop history are therefore
caller-supplied request data and are explicitly marked as such in scenario
limitations. No external farm records are fetched or persisted as Module 01
entities.

Start at the repository [README](../../../../README.md), then see:

- [Architecture and integration boundaries](../../../../docs/module03-architecture.md)
- [API reference](../../../../docs/module03-api.md)
- [Data model and evidence policy](../../../../docs/module03-data-model.md)
- [Algorithm and scoring methods](../../../../docs/module03-algorithms.md)
- [Operations and known limitations](../../../../docs/module03-operations.md)

This documentation does not assert completion of any phase. The approved
original five-phase specification is not available in this checkout; review
the acceptance criteria with the project owner before claiming completion.
