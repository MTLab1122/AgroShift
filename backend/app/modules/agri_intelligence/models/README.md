# Agricultural intelligence database models

The models persist agricultural facts without inserting research values. Each
fact has one of the four `EvidenceStatus` values. `VERIFIED` and `PROVISIONAL`
facts require a `primary_evidence_id`; additional evidence is linked through
the fact-specific evidence association tables. The evidence record points to
an agricultural source when published material is its origin. Source
`review_status` is independent of every fact's evidence status.

Geographic applicability has three distinct meanings:

- `AgriculturalSource.geographic_applicabilities` describes where a source
  claims to apply.
- Calendar location fields and rotation-rule `geographic_scope` describe the
  applicability of a specific fact/rule; normalized rotation-rule scope rows
  retain explicit global, administrative, or agroecological applicability.
- `EvidenceGeographicScope` describes where an individual evidence record
  originated or was observed. Its `FARM` scope stores an opaque external farm
  identifier; it deliberately does not define or depend on another module's
  Farm model.

An explicit `GLOBAL` scope is stored as a scope association with no geographic
foreign key. No scope associations mean geographic applicability is unknown,
not global. `AgroecologicalZoneGeography` connects a zone to any number of
administrative areas while keeping zones independent from the administrative
hierarchy.

`EvidenceRecord.source_type` distinguishes farmer-provided, directly measured,
and published-source evidence. Published evidence requires `source_id`;
farmer-provided and measured evidence may be linked to an agricultural source
when one exists. The source-level `all_crops_flag` represents global crop applicability;
`SourceAllCropsApplicability` provides a unique explicit marker row. Narrow
crop, variety, and family applicability uses selector rows. Composite foreign
keys prevent narrow rows from coexisting with an all-crops source, and selector
uniqueness constraints prevent duplicate entries.

Calendar window fields use the recurring `MM-DD` form. Database checks validate
month/day, leap-day permissions, paired endpoints, and year-crossing flags;
ORM insert/update validation checks the same window semantics before persistence.
The SQLAlchemy attribute `metadata_json` maps to the required database column
name `metadata`, which SQLAlchemy reserves on declarative model classes.

See the [Phase 01 data-layer guide](../../../../../docs/agri-intelligence-phase-01.md)
for schema, repository, service, seed, setup, and known-data-gap usage.
