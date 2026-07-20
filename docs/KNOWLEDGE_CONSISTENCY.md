# Knowledge Consistency

Milestone 8 evaluates semantic truth constraints only after structural
validation has produced consumable accepted records. It remains deterministic,
offline-first, and separate from migration and repair.

## Core rules

The initial core rules verify:

- confidence values are numeric and between zero and one;
- `analysis_run.created_at`, when present, is ISO-8601;
- root causes have anomaly evidence through an edge or explicit reference.

Errors produce `inconsistent`; warnings produce `degraded`; a structurally
inadmissible graph is `not_evaluated`. Reports contain rule ids, counts,
locations, and privacy-safe evidence.

## Domain Pack rules

Domain Packs can contribute additive `DomainPackConsistencyRules`. Rule ids must
use `domain_pack.<pack_id>.` and must be globally unique when composed with core
and other pack rules. A pack cannot replace or shadow a core rule.

## Downstream admission

The report exposes separate `can_inform_experience` and
`can_inform_recommendations` gates. Semantic errors close both gates; warnings
remain admissible. Experience refresh and recommendation generation accept the
report explicitly and return `blocked_by_consistency` without mutating stores
when admission is denied.
