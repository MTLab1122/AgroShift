# API contracts

The canonical cross-module JSON contracts are in `shared/schemas/`. Backend Pydantic models live in `backend/app/schemas/` and `backend/app/modules/nasa_data/schemas.py`; update those in coordination with the owning module when a shared contract changes.

- Use `/api/v1` for API routes; `/health` is the unversioned health probe.
- Encode dates as ISO `YYYY-MM-DD` and timestamps as ISO 8601.
- Store latitude and longitude as decimal degrees; latitude is north/south and longitude is east/west.
- Pair measurements with explicit units.
- Represent missing observations as `null` or a documented missing-data status. Never substitute zero or false for missing data.
- Distinguish NASA gridded/reanalysis products from on-farm sensors.
- Mark synthetic payloads with `is_demo_data: true` and include the prototype decision-support limitations.
- Return errors using the `ApiError` schema and propagate the request ID.
