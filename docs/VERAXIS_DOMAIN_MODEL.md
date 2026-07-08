# Veraxis Domain Model

## Purpose

This document defines the conceptual domain model for the future Kernel-Oriented
Veraxis architecture.

It is a domain-level reference, not a description of already implemented runtime
classes.

## Domain Entities

### Agent

- Responsibility:
  execute a role-specific workflow using platform abstractions.
- Main attributes:
  `name`, `role`, `supported_capabilities`, `execution_policy`, `status`.
- Relationships:
  uses `Capability`, emits `Event`, reads `Memory`, interacts with `Kernel`.
- Practical example:
  an analytical agent that requests planning and reporting capabilities without
  directly orchestrating all engines.

### Capability

- Responsibility:
  expose a reusable platform function.
- Main attributes:
  `capability_id`, `name`, `version`, `input_contract`, `output_contract`,
  `execution_mode`, `deterministic`.
- Relationships:
  invoked by `Kernel`, used by `Agent`, may read `Memory` and `Knowledge`.
- Practical example:
  `anomaly_detection`, `analysis_planning`, `knowledge_reasoning`.

### Kernel

- Responsibility:
  coordinate platform execution through abstractions.
- Main attributes:
  `kernel_id`, `execution_context`, `capability_registry`, `policy_set`,
  `runtime_state`.
- Relationships:
  orchestrates `Capability`, `Memory`, `Knowledge`, `Reasoning`, `Decision`,
  and `Event`.
- Practical example:
  the future runtime boundary that replaces a hard-coded sequential coordinator.

### Event

- Responsibility:
  represent a meaningful platform lifecycle occurrence.
- Main attributes:
  `event_id`, `event_type`, `timestamp`, `source`, `payload_summary`,
  `correlation_id`.
- Relationships:
  emitted by `Agent`, `Capability`, or `Kernel`; may update `Memory`.
- Practical example:
  `analysis_completed`, `anomaly_detected`, `recommendation_generated`.

### Memory

- Responsibility:
  store reusable operational or analytical state.
- Main attributes:
  `memory_id`, `memory_type`, `scope`, `retention_policy`, `confidence`,
  `metadata`.
- Relationships:
  linked to `Analysis Run`, `Experience`, `Recommendation`, and `Event`.
- Practical example:
  analysis session memory or query history memory.

### Knowledge Node

- Responsibility:
  represent a graph entity inside the Knowledge Layer.
- Main attributes:
  `node_id`, `node_type`, `label`, `properties`.
- Relationships:
  connected by `Knowledge Edge`; may represent `Dataset`, `Insight`,
  `Anomaly`, `Root Cause`, `Recommendation`, or `Analysis Run`.
- Practical example:
  a node for a dataframe column or a past anomaly.

### Knowledge Edge

- Responsibility:
  represent an explicit graph relationship.
- Main attributes:
  `edge_id`, `source_id`, `target_id`, `relationship_type`, `properties`.
- Relationships:
  links `Knowledge Node` entities.
- Practical example:
  `ANALYZED_DATASET`, `DETECTED_ANOMALY`, `GENERATED_REPORT`.

### Analysis Run

- Responsibility:
  capture one analytical execution context and its outputs.
- Main attributes:
  `run_id`, `created_at`, `source_type`, `row_count`, `column_count`,
  `primary_metric`, `time_axis`, `status`.
- Relationships:
  uses `Dataset`, produces `Insight`, `Anomaly`, `Root Cause`,
  `Recommendation`, and `Decision`; updates `Memory`.
- Practical example:
  a run analyzing response time by status over time.

### Dataset

- Responsibility:
  represent the analyzed data source at a metadata level.
- Main attributes:
  `dataset_id`, `source_type`, `shape`, `columns`, `dtypes`, `privacy_policy`.
- Relationships:
  belongs to `Analysis Run`, contains `Metric`, may map to `Knowledge Node`.
- Practical example:
  a CSV upload with operational ticket and time columns.

### Metric

- Responsibility:
  represent a business or analytical measure.
- Main attributes:
  `metric_id`, `name`, `semantic_role`, `dtype`, `aggregation_family`,
  `is_primary`.
- Relationships:
  belongs to `Dataset`, referenced by `Insight`, `Anomaly`, `Recommendation`.
- Practical example:
  `response_time`, `activation_days`, `monthly_revenue`.

### Insight

- Responsibility:
  represent an explainable analytical finding.
- Main attributes:
  `insight_id`, `title`, `summary`, `confidence`, `evidence_type`.
- Relationships:
  produced by `Analysis Run`, may reference `Metric`, `Anomaly`, or
  `Recommendation`.
- Practical example:
  “response time degradation is concentrated in specific segments”.

### Anomaly

- Responsibility:
  represent a statistically significant abnormal pattern.
- Main attributes:
  `anomaly_id`, `type`, `severity`, `confidence`, `affected_metric`,
  `affected_period`.
- Relationships:
  produced by `Analysis Run`, explained by `Root Cause`, referenced by
  `Recommendation`.
- Practical example:
  an SLA violation spike in a specific time window.

### Root Cause

- Responsibility:
  represent a structured possible explanation for one or more anomalies.
- Main attributes:
  `root_cause_id`, `title`, `hypothesis`, `severity`, `confidence`,
  `affected_metrics`.
- Relationships:
  explains `Anomaly`, linked to `Analysis Run`, may inform `Decision`.
- Practical example:
  “possible operational backlog causing persistent response-time degradation”.

### Recommendation

- Responsibility:
  represent a proposed analytical or operational next step.
- Main attributes:
  `recommendation_id`, `step`, `priority`, `reason`, `source`, `confidence`.
- Relationships:
  produced by `Reasoning` or `Decision`, linked to `Analysis Run`,
  `Experience`, `Metric`, or `Root Cause`.
- Practical example:
  “segment the primary metric by status and channel”.

### Decision

- Responsibility:
  capture an explicit prioritized action or conclusion selected by the platform.
- Main attributes:
  `decision_id`, `decision_type`, `priority`, `rationale`, `confidence`,
  `status`.
- Relationships:
  derived from `Recommendation`, informed by `Reasoning`, `Knowledge`,
  `Memory`, and `Experience`.
- Practical example:
  choosing the next analytical action to validate a suspected root cause.

### Experience

- Responsibility:
  represent accumulated reusable analytical practice.
- Main attributes:
  `experience_id`, `pattern`, `effectiveness_score`, `usage_count`,
  `domain_scope`, `reliability`.
- Relationships:
  derived from `Memory`, linked to `Recommendation`, `Decision`,
  and `Analysis Run`.
- Practical example:
  a known effective segmentation strategy for response-time investigations.

### Experience Store

- Responsibility:
  persist deterministic analytical experience locally without raw data.
- Main attributes:
  `store_id`, `schema_version`, `experiences`, `last_refresh_at`, `privacy_policy`.
- Relationships:
  stores `Experience`, queried by `Experience Query`, refreshed from
  `Knowledge Node` and `Analysis Run`.
- Practical example:
  a local JSON store with reusable patterns for recurring response-time issues.

### Domain Pack

- Responsibility:
  inject domain-specific logic without changing the core platform.
- Main attributes:
  `pack_id`, `domain_name`, `kpis`, `patterns`, `terminology`,
  `strategy_rules`, `version`.
- Relationships:
  enriches `Capability`, influences `Reasoning`, informs `Decision`,
  shapes `Recommendation`.
- Practical example:
  a telepedaggio pack with domain KPIs and strategy rules.

## Relationship Diagram

```text
Kernel
  |
  +--> Capability <------------------- Agent
  |         |
  |         +--> Event
  |         |
  |         +--> Memory -------> Experience
  |         |
  |         +--> Experience Store ----> Experience
  |         |
  |         +--> Knowledge Node <---- Knowledge Edge ----> Knowledge Node
  |                                  |
  |                                  +--> Dataset
  |                                  +--> Analysis Run
  |                                  +--> Insight
  |                                  +--> Anomaly
  |                                  +--> Root Cause
  |                                  +--> Recommendation
  |
  +--> Analysis Run ----> Dataset ----> Metric
  |          |               |
  |          +--> Insight    +--> Domain Pack influences context
  |          +--> Anomaly
  |          +--> Root Cause
  |          +--> Recommendation ----> Decision
  |
  +--> Memory / Knowledge / Reasoning / Decision orchestration
```

## Modeling Notes

- `Agent` is an execution actor, not the owner of cross-module orchestration.
- `Capability` is the preferred unit of reuse in the target platform.
- `Kernel` is the future runtime center.
- `Knowledge Node` and `Knowledge Edge` remain the graph abstraction for
  analytical structure.
- `Experience` is not the same as history; it is history interpreted into
  reusable analytical value.
- `Experience Store` must remain metadata-only and must not persist raw rows.

## Status

This is a target domain model for V2.1.1 foundation work.

It should guide future abstractions, ADRs, and interface design.
