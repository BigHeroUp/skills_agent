# Template Learning Loop

## Failure Taxonomy

| Defect ID | Categoria | Sintomi | Ipotesi Root Cause | Agenti Impattati |
|---|---|---|---|---|

Categorie suggerite:
- Comportamento prompt ambiguo
- Validazione tool insufficiente
- Policy di rifiuto debole
- Deriva dello schema output
- Sforamento latenza o budget

## Modello Di Prioritizzazione

Assegnare score a ogni difetto:

- Impatto (1-5)
- Frequenza (1-5)
- Effort fix (1-5, inverso)
- Rischio regressione (1-5, inverso)

Esempio score priorita:

`(impatto * frequenza) + effort_fix_inverso + rischio_regressione_inverso`

## Template Proposta Patch

```yaml
proposal_id:
affected_agents: []
defect_cluster:
change_type: prompt|tool-contract|policy|evaluation
minimal_diff_summary:
hypothesis:
expected_metric_delta:
required_tests: []
rollback_trigger:
```

## Piano Di Rollout

- Gruppo canary:
- Gruppo control:
- Finestra osservazione:
- Gate di successo:
- Condizioni abort:

## Revisione Post-Change

- Quali metriche sono migliorate?
- Quali metriche sono peggiorate?
- Tenere, revertire o iterare?
