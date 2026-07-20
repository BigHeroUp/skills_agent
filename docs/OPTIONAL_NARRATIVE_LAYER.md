# Optional LLM Narrative Layer

Milestone 12 adds an optional facade for executive summaries, professional
rewrites, and natural explanations. The deterministic input remains the
authoritative source in every result.

The layer is disabled by default. When disabled, unavailable, over budget,
offline, or above its input limit, it returns the exact deterministic text.
Results always expose whether an LLM was used, the model when applicable, any
gateway error, and policy provenance.

## Safety boundaries

- critical requests are blocked before any model call;
- prompts prohibit new facts, numbers, causes, recommendations, or decisions;
- common raw-data keys such as `dataframe`, `raw_rows`, and `records` are
  rejected recursively;
- only explicitly supplied, JSON-safe facts enter the prompt;
- the existing gateway retains call budgets, cache, model parameter handling,
  and deterministic fallback.

The layer formats content. It never changes Knowledge Graph validation,
consistency gates, recommendation ranking, decision arbitration, or action
execution.
