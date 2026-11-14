# AgroShift Agricultural Intelligence: Phase 01 Data Layer

This document describes the Phase 01 agricultural reference-data layer in
`backend/app/modules/agri_intelligence`. It complements, and does not replace,
the existing model documentation.

## Scope and dependencies

The module uses the existing SQLAlchemy 2.x declarative models and Alembic
revision. It owns crop reference data, evidence provenance, source applicability,
crop calendars and requirements, rotation-rule records, and agricultural
geography. It does not retrieve climate observations, calculate feasibility,
or make crop recommendations.

Use the configured session factory in `db/session.py`. Repositories and
services receive a caller-owned SQLAlchemy `Session`; they flush changes but do
not commit or close the session. The caller owns transaction boundaries.

## Models, schemas, and repositories

Create, update, and read schemas are exported from `schemas`. Crop, variety,
calendar, requirement, rotation-rule, source, evidence, administrative
geography, agroecological-zone, and normalized geographic-scope schemas retain
the model's field names and enum values. Create schemas validate field ranges,
selector exclusivity, evidence requirements, date windows, and geography-scope
selectors. Repository updates validate the merged persisted record, so a
partial update cannot bypass a multi-field constraint or null a required field.

Repositories are exported from `repositories`. They provide create, get, list,
update, and delete operations for crops, varieties, calendars, requirements,
rotation rules, sources, evidence, geography, zones, and normalized
geographic-scope records. Missing IDs raise `RecordNotFoundError`; SQLAlchemy
integrity failures remain visible to the caller.

Services are exported from `services`:

- `CropDatabaseService` manages crops and varieties.
- `CropCalendarService` manages and filters calendar records by crop,
  administrative geography, zone, and evidence status.
- `AgriculturalResearchService` manages sources and evidence records.

The services do not implement Phase 02 feasibility or recommendation logic.

```python
from backend.app.modules.agri_intelligence.db.session import SessionLocal
from backend.app.modules.agri_intelligence.schemas import CropCreate
from backend.app.modules.agri_intelligence.services import CropDatabaseService

with SessionLocal() as session:
    crop = CropDatabaseService(session).create_crop(
        CropCreate(slug="example-crop", evidence_status="UNKNOWN")
    )
    session.commit()
```

## Evidence and provenance policy

`EvidenceStatus` values are `VERIFIED`, `PROVISIONAL`, `UNKNOWN`, and
`UNDER_REVIEW`. `VERIFIED` and `PROVISIONAL` records require a primary evidence
record. `UNKNOWN` means the module has no supported value; it must not be
presented as verified. `UNDER_REVIEW` is not a synonym for verified.

Each evidence record identifies whether its origin is farmer-provided,
directly measured, or a published source. Published-source evidence requires a
linked `AgriculturalSource`. Evidence geographic scopes describe the origin or
observation scope of that evidence. Source review status is independent of
fact-level evidence status.

Source applicability may contain multiple distinct crop, variety, or family
selectors. `ALL_CROPS` is represented by its dedicated marker and must not
coexist with narrower selectors for that source. Duplicate and incompatible
selectors are rejected by database constraints as well as schema validation.

## Geographic hierarchy

Administrative records follow `Country -> ProvinceState -> District ->
Locality`. Calendar records may have country-only or province-level scope;
when multiple levels are supplied, their foreign-key hierarchy must agree.
An absent location is unknown applicability, not global applicability.
Explicit global applicability is represented by a `GLOBAL` scope record where
the model supports normalized scopes. Agroecological zones are separate
entities linked to administrative areas through association records; they do
not replace or alter the administrative hierarchy.

The demonstration seed currently creates only the country and province
references for Pakistan and Khyber Pakhtunkhwa. It does not assert a Peshawar
district/locality boundary or classify the Peshawar Valley as an agroecological
zone.

## Initial seeds

Run the repeatable seed function inside the caller's transaction:

```python
from backend.app.modules.agri_intelligence.db.session import SessionLocal
from backend.app.modules.agri_intelligence.seeds import seed_all

with SessionLocal() as session:
    result = seed_all(session)
    session.commit()
```

The current seed includes:

- Eight user-nominated crop names: wheat, maize, rice, sugarcane, mustard,
  chickpea, lentil, and mung bean. Their evidence status is `UNKNOWN`; no
  scientific names, families, numerical measurements, or agronomic validation
  are inferred.
- Explicit `UNKNOWN` calendar placeholders and `UNKNOWN` placeholders for
  soil, water, temperature, salinity, and nutrient requirement categories.
  These contain no planting dates or numeric measurements.
- Country/province reference rows for Pakistan and Khyber Pakhtunkhwa.
- Three unreviewed institutional context sources:
  - University of Agriculture, Peshawar, Faculty of Crop Production Sciences:
    <https://www.aup.edu.pk/faculty/faculty-of-crop-production-sciences>.
    Its page describes faculty activities and wheat/maize seed production but
    names no varieties or agronomic values; it is not linked as evidence for a
    seeded crop fact.
  - Pakistan Agricultural Research Council, wheat planning meeting news:
    <https://www.parc.gov.pk/NewsDetail/YzZmNTE3MWUtMDUzNS00ZDMxLThlYTQtMWFmN2JmMWQ0YzY0>.
    This is meeting context, not a crop recommendation.
  - FAO in Pakistan: <https://www.fao.org/pakistan/en/>. This is a country
    office landing page, not crop-specific evidence.

The seed creates no variety, rotation rule, or agroecological-zone records.
Available references do not provide supported variety identifiers, locally
validated rotation rules, or a reliable Peshawar Valley zone classification.
Fodder and cover-crop species are not added because none were individually
identified and evidenced. Re-running `seed_all` does not duplicate its rows.

## Setup and migrations

Install the project's declared dependencies in its Python environment, then
run the existing initial Alembic revision before using the repositories:

```powershell
$env:DATABASE_URL = "sqlite:///./agri_intelligence.db"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The engine reads `DATABASE_URL` and retains its normal file-backed default when
the variable is not set. Tests use isolated SQLite databases with foreign-key
enforcement; they should not use the repository-root database.

## Known gaps and limitations

- Local crop calendars, named varieties, quantified crop requirements, local
  rotation rules, and agroecological-zone boundaries remain unverified.
- `UNKNOWN` seed placeholders represent missing information only; they are not
  agronomic guidance and do not imply a global geographic scope.
- Source URLs are preserved as references, but the listed institutional pages
  are not treated as evidence for values they do not contain.
- The original approved Module 03 five-phase specification was not present in
  the inspected workspace. This document and the implemented scope therefore
  cannot certify that every original Phase 01 acceptance criterion is met.
