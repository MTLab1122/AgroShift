# AgroShift architecture

AgroShift is a modular monorepo. The current checked-in backend and frontend stack is authoritative; new modules should integrate with the existing interfaces rather than replace them with a different framework.

## Runtime shape

```text
Vite + React frontend
        |
        | HTTP / JSON, X-Request-ID
        v
FastAPI application (backend/app/main.py)
        |
        +-- request tracing and response telemetry
        +-- /api/v1 NASA climate router
        +-- /api/v1 agro-engine router
                 |
                 +-- live NASA POWER client
                 +-- live-to-demo fallback gateway
        |
        +-- shared Pydantic contracts in backend/app/schemas/
            and backend/app/modules/nasa_data/schemas.py
```

## Repository boundaries

| Area | Responsibility |
| --- | --- |
| `backend/app/core/` | Request tracing, NASA configuration, and live/demo gateway |
| `backend/app/modules/nasa_data/` | NASA data acquisition, normalization, aggregation, and climate routes |
| `backend/app/modules/agro_engine/` | Farm/climate comparison and recommendations |
| `backend/app/schemas/` | Farm, comparison, and recommendation models |
| `shared/schemas/` | JSON Schema contracts used to validate cross-module payloads |
| `frontend/` | Existing React + Vite user interface |
| `data/demo/` | Explicitly labeled synthetic/demo fixtures |
| `tests/` | Unit, integration, and acceptance tests |

Keep module implementations in their owned paths. Shared-contract changes should be coordinated with affected module owners.

## API conventions

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health` | Basic service health |
| GET | `/api/v1/health` | Module readiness and diagnostics |
| GET | `/api/v1/climate/summary` | Normalized climate summary |
| GET | `/api/v1/climate/history` | Climate time series and aggregates |
| POST | `/api/v1/recommendations/generate` | Farm analysis and crop scenarios |

All errors use the `ApiError` contract and carry a request ID when available. Responses include tracing headers. Coordinates use decimal degrees, dates use ISO `YYYY-MM-DD`, and missing observations stay `null`; zero is a valid observation and must not be used as a missing-data sentinel.

NASA POWER values represent gridded observations/reanalysis, not on-farm sensor measurements. Demo fallback responses must remain explicitly labeled and recommendations are decision support only, with no guaranteed yield or profit outcomes.
