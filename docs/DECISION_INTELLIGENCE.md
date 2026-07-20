# Decision Intelligence Layer

Milestone 10 formalizes deterministic arbitration across analytical strategies,
anomaly responses, root-cause actions, and ranked recommendations.

Evidence carries a typed origin, strength, reliability, confidence, and stable
id. Its score is the product of those three quality factors. Decision options
reference evidence ids, declare a source, base confidence, action, and risk.

The versioned policy combines:

- option base confidence;
- average evidence score adjusted for missing evidence;
- source priority;
- risk penalty.

Options without available evidence or below the minimum policy score are
rejected. The engine selects the highest stable score or explicitly abstains.
Each ranked result exposes present and missing evidence ids, source, risk, and
score. A closed Knowledge Consistency gate blocks arbitration entirely.

The engine does not execute the selected action and does not use an LLM.
