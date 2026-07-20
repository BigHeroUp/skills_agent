# Recommendation Engine

Milestone 9 introduces a deterministic next-best-action engine. It ranks
explicit candidates; it does not invent actions with an LLM.

Each candidate carries action, reason, confidence, evidence strength, urgency,
risk, domain, compatible contexts, provenance ids, and source. The default
policy combines confidence, evidence, and urgency, then applies a risk penalty.

Before scoring, admission filters reject candidates that:

- fall below the context confidence threshold;
- exceed the maximum accepted risk;
- target another domain;
- do not support the active analytical context.

Ranking is stable and returns the score, priority, evidence ids, policy id, and
policy version. A closed Knowledge Consistency recommendation gate rejects all
candidates before ranking.

`candidates_from_experience()` adapts existing Experience Engine output while
preserving source experience ids as evidence provenance.
