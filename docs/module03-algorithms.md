# Module 03 validation, rotation, scoring, and explanation

## Phase 02 validation

Validation returns checks, applicable rule identifiers, inputs, evidence
record IDs, source IDs, missing information, and limitations. Soil checks
compare explicit compatible values; a soil-type label by itself is not a
suitability claim. Water comparisons require compatible units and basis.
Calendar checks use stored windows and their geographic scope. Rotation
checks use stored crop-family/rule evidence and supplied history. Conflicting
or absent evidence does not become an unsupported recommendation.

Status precedence preserves hard infeasibility. Missing required information
is reported as `INSUFFICIENT_DATA`; when evidence-backed checks conflict, the
result is not promoted to feasible. Climate response thresholds and
pest/disease evidence are not present in the current data seed, so those
checks remain insufficient rather than inventing thresholds.

## Phase 03 scenarios and rotation

The existing-practice scenario evaluates supplied history as a baseline; it
is explicitly tagged `BASELINE_ONLY_NOT_A_RECOMMENDATION`. Pulse-inclusive
scenarios evaluate active chickpea, lentil, and mung-bean records individually
as candidates, without selecting one automatically. The soil-cover/forage
scenario remains insufficient until locally evidenced candidate species and
establishment, water, duration, and harvest/termination data exist.

`RotationEngine` delegates sequence evaluation to the validator, which checks
the supplied sequence against stored rotation rules and evidence. It does not
invent crop-family relationships or local rotation schedules.

Rotation rules apply only when an associated normalized geographic scope
matches the supplied `FarmContext`. `GLOBAL` is explicit; a rule with no scope
is not treated as global. Country, province/state, and district scopes apply
to stored administrative descendants only when all supplied country,
province/state, district, and locality IDs agree with the Country →
Province/State → District → Locality records. A locality scope matches only
that locality. Locality may be supplied directly, with its ancestors resolved
from those records. Missing, unknown, or inconsistent farm geography cannot
match a narrow administrative scope. Agroecological-zone scopes are evaluated
separately and match only the same stored zone ID; they are not treated as
administrative ancestors. Multiple normalized scopes on one rule are
alternative applicable locations.

## Phase 04 scoring and comparison

`PriorityWeights` contains four non-negative Decimal weights:
`climate_water`, `rotation`, `diversity`, and `farmer_priority`; their sum must
equal 1. Each corresponding score component is a Decimal from 0 to 100 or
unknown. The score is a weighted sum rounded to two decimal places using
`ROUND_HALF_UP`.

Scoring is withheld when status is `INFEASIBLE` or `INSUFFICIENT_DATA`, or
when any positively weighted component is missing. Missing values are never
imputed. Default weights are equal quarters and are provisional software
defaults, not farmer-preference research. Comparison ranks scenarios only
when all requested scenarios have a score and are feasible or conditionally
feasible; otherwise `ranked_scenario_ids` is empty with a limitation message.

The available components and equal default weights are a structural
comparison mechanism. No validated yield, profitability, water-footprint, or
soil-health benefit model is currently supplied, so the software does not
claim those quantitative impacts.

## Explanations

The explanation engine summarizes the stored feasibility status, score
availability, evidence references, missing information, and limitations. It
does not manufacture agronomic causes or recommendations absent from the
stored evaluation.
