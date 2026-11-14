# AgroShift

AgroShift is a modular agricultural decision-support backend. The current
repository contains Module 02 (NASA POWER climate data) and the Module 03
agricultural intelligence work in progress. Module 03 records evidence-backed
crop data, evaluates supplied facts, and persists transparent scenario
evaluations. It does not replace farmer or expert decisions.

## Documentation

- [Module 03 overview](backend/app/modules/agri_intelligence/README.md)
- [Architecture and integration boundaries](docs/module03-architecture.md)
- [API reference](docs/module03-api.md)
- [Database model, data dictionary, and evidence policy](docs/module03-data-model.md)
- [Validation, rotation, scoring, and explanations](docs/module03-algorithms.md)
- [Setup, migrations, seeds, tests, and limitations](docs/module03-operations.md)
- [Module 02 NASA data documentation](docs/data-sources.md)

The original approved Module 03 five-phase specification and Module 01/04
implementation are not present in this checkout. See the limitations document;
this README does not certify phase completion or production readiness.

## Local development

Requires Python 3.11 or newer. From the repository root, create and activate a
virtual environment, install the project, apply migrations, then start the API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:DATABASE_URL = "sqlite:///./agri_intelligence.db"
python -m alembic upgrade head
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The default database URL is file-backed at `./agri_intelligence.db`. Set
`DATABASE_URL` before starting the application or running migrations to select
another database. Tests use isolated SQLite databases; do not point test runs
at a user or development database.

Run the test suite with:

```powershell
python -m pytest
```

The interactive API reference is available at `/docs` while the local server
is running. Production deployments should configure `CORS_ORIGINS` with
explicit trusted origins and provide authentication and authorization at the
deployment boundary; this service currently does not implement user
authentication.
