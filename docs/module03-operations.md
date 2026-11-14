# Module 03 setup, migrations, seeds, tests, and limitations

## Configuration and startup

Install the package into Python 3.11+ and use the repository root as the
working directory:

```powershell
python -m pip install -e .
$env:DATABASE_URL = "sqlite:///./agri_intelligence.db"
python -m alembic upgrade head
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`DATABASE_URL` controls both application and Alembic connections. If unset,
the application uses `sqlite:///./agri_intelligence.db`, relative to the
process working directory. SQLite connections enable foreign-key enforcement.
For a deployment, use an appropriately secured database URL supplied through
deployment configuration, not committed source.

`CORS_ORIGINS` is a comma-separated origin allowlist. The default `*` is
non-credentialed; an explicit list enables credentials. `*` cannot be mixed
with explicit origins. Production should use explicit trusted origins. The
API does not implement authentication or authorization.

## Migrations

The initial revision creates Phase 01 tables; the following revision adds
`recommendation_scenarios`. Apply all revisions with `alembic upgrade head`.
Use `alembic downgrade base` only against a disposable database: it removes
the schema. To isolate a local migration check, point `DATABASE_URL` at a
temporary SQLite file outside the repository or use an in-memory test engine.

## Repeatable seeds

Seeds receive a caller-owned SQLAlchemy session and do not commit:

```python
from backend.app.modules.agri_intelligence.db.session import SessionLocal
from backend.app.modules.agri_intelligence.seeds import seed_all

with SessionLocal() as session:
    result = seed_all(session)
    session.commit()
```

`seed_all` uses idempotent lookup/create helpers. It includes UNKNOWN crop
placeholders, UNKNOWN calendars and requirements, geographic country/province
references, and the institutional context sources documented in the Phase 01
guide. It currently seeds no crop varieties, verified crop facts, rotation
rules, or agroecological-zone classifications. Do not reinterpret empty seed
sets as proof that no such facts exist.

## Tests and isolated databases

From the repository root:

```powershell
python -m pytest
```

Database tests create temporary or in-memory SQLite engines and enable
`PRAGMA foreign_keys=ON`. Do not set test `DATABASE_URL` to the repository
root database. Tests should not create or alter `agri_intelligence.db`.

## Known gaps and limitations

- The original approved Module 03 five-phase specification is not present in
  this checkout, so its full acceptance criteria cannot be independently
  checked here.
- Module 01 farm/history and Module 04 visualization are absent. Farm context
  and crop history are supplied by API callers; ownership and provenance
  cannot be independently verified.
- Seed crop names are `UNKNOWN`; named varieties, local calendars, quantified
  requirements, locally validated rotations, and Peshawar Valley
  agroecological boundaries are not established.
- Climate suitability thresholds and pest/disease rules are not supported by
  seeded evidence. Their outcomes remain insufficient.
- No local yield, cost, profitability, water-footprint, or soil-health benefit
  model exists. Scenario scores are withheld unless required score components
  are explicitly available.
- API authentication/authorization, farm tenant isolation, data retention,
  and deployment database operations must be supplied by the deployment
  environment.
- PostgreSQL runtime behavior must be verified against a configured PostgreSQL
  instance; SQLite tests alone do not establish production runtime
  compatibility.
- Do not claim Phase 01–05 completion or production readiness until the
  approved specification is available and all corresponding criteria are
  verified by the project owner.
