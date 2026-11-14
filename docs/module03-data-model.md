# Module 03 data model, dictionary, and evidence policy

## Entity reference

| Entity | Purpose | Important relationships/constraints |
|---|---|---|
| `Crop` | Canonical crop record and evidence status. | Slug is unique; facts link to evidence. |
| `CropVariety` | Variety identifiers and crop relationship. | Linked to a crop; evidence status is independent. |
| `CropCalendar` | Recurring planting/harvest windows. | `MM-DD` dates, leap-year and cross-year flags, crop and optional administrative scope. |
| `CropRequirement` | Typed soil, water, climate, salinity, or nutrient requirement. | Requirement-specific checks; explicit units and evidence status. |
| `CropRotationRule` | Persisted rotation rule with explicit selectors and geographic scope. | May reference crops/families and normalized global, administrative, or zone scope. |
| `AgriculturalSource` | Bibliographic/source identity and review status. | Applicability represented separately from source facts. |
| `EvidenceRecord` | Provenance record for a fact. | Source type distinguishes farmer-provided, measured, and published material; published evidence requires a source. |
| `Country`, `ProvinceState`, `District`, `Locality` | Administrative hierarchy. | Calendar country/province/district relationships must agree. |
| `AgroecologicalZone` | Named zone reference. | Zone-to-geography associations do not redefine administrative boundaries. |
| `RecommendationScenario` | Persisted request-time evaluation and comparison output. | Stores caller farm ID, sequence, validation/evidence references, missing data, score and explanation. The farm ID is not a Module 01 FK. |

SQLAlchemy attribute `metadata_json` maps to the physical column `metadata`
because `metadata` is reserved by the declarative API. Scenario JSON columns
store structured input/output snapshots; Decimal values are serialized as
decimal strings in JSON to avoid precision loss.

## Evidence status

- `VERIFIED`: supported by a primary evidence record.
- `PROVISIONAL`: indirect or geographically limited support; not equivalent
  to local verification.
- `UNDER_REVIEW`: evidence has not completed review.
- `UNKNOWN`: no supported value is available.

`VERIFIED` and `PROVISIONAL` facts require primary evidence. Missing values
must remain missing. `UNKNOWN` is not a zero, default recommendation, or
verified fact. Source review status and fact-level evidence status are
separate concepts.

## Provenance fields and scope

An evidence record identifies its source type, optional source record,
publication details as available, and geographic origin/observation scope.
Evidence IDs and source references are returned with validation results when
available. Caller-provided history should include its `source_record_id` and
`evidence_record_ids`; absent provenance is reported as missing information.

Source crop applicability supports several distinct narrower crop, variety,
or family selectors. `ALL_CROPS` is stored as a separate explicit marker and
cannot coexist with narrower selectors for that source. Duplicate and
selector-exclusive entries are rejected at the database layer.

Geographic applicability is explicit. No scope is not equivalent to global
scope. Administrative records follow Country → Province/State → District →
Locality. Rotation validation accepts an optional locality ID in `FarmContext`
and resolves its administrative ancestors from these records. Country,
province/state, district, and locality scopes match a farm's corresponding
stored ancestor or exact locality only when supplied hierarchy IDs are
consistent; a narrow scope does not match when farm geography is missing or
inconsistent. Agroecological-zone scopes match the exact same zone ID and are
not administrative ancestors. Explicit `GLOBAL` scopes match without farm
geography, while rules with no normalized scope do not imply global
applicability. Multiple normalized scopes on one rotation rule are
alternatives. A calendar may be country-only or province-level; when more
than one administrative reference is present, the hierarchy must be consistent.
Evidence geographic scope describes the evidence, not necessarily every
location where a source can apply.

## Current seed evidence

The initial crop names were user-nominated, but crop facts are seeded with
`UNKNOWN` evidence status. The three institutional URLs in the Phase 01 seed
are retained as unreviewed context sources, not as evidence for crop
measurements, calendars, varieties, or local recommendations. No numeric
agricultural values or local validation are asserted. See the
[Phase 01 seed notes](agri-intelligence-phase-01.md#initial-seeds) for the
specific links and limits.
