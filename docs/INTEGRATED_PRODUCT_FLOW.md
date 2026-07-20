# Integrated Product Intelligence Flow

The production `Coordinator` now ends every successful analysis with a
non-blocking `ProductIntelligenceAgent` after Knowledge Graph persistence.

```text
Deterministic analysis and report
  -> Knowledge Graph persistence
  -> structural governance
  -> semantic consistency
  -> Experience refresh and retrieval
  -> recommendation admission and ranking
  -> evidence-based decision arbitration
  -> optional narrative formatting
  -> one AgentContext.product_intelligence payload
```

The integrated payload contains Knowledge Graph quality, consistency gates,
Experience refresh and candidates, ranked recommendations, the selected or
abstained decision, narrative provenance, and a single execution status.

## Product behavior

- the statistical analysis and deterministic report remain authoritative;
- integration failures are recorded in `product_intelligence` but do not mark a
  valid analysis as invalid;
- inconsistent evidence blocks Experience, Recommendation, and Decision through
  existing gates;
- Narrative remains disabled unless `metadata.enable_narrative` is true;
- the entire product flow can be disabled for one run with
  `metadata.integrated_product_flow=false`;
- `metadata.experience_path` can isolate the local Experience store.

The dashboard timeline includes the final agent and appends a compact Product
Intelligence section with consistency status, admissible action count, selected
next best action, evidence score, and risk. The optional narrative never
replaces `AgentContext.final_report`.
