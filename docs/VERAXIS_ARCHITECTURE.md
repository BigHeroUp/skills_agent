# Veraxis Kernel-Oriented Architecture

## Purpose

This document defines the target architecture for Veraxis beyond the current
Coordinator-based pipeline.

It does not describe a runtime feature already shipped in the repository.

It defines the architectural direction for a capability-oriented, offline-first,
kernel-driven analytical platform.

## Why Move Beyond the Current Coordinator

The current architecture is centered on a sequential `Coordinator` that invokes
concrete agents in a fixed Hub & Spoke pipeline.

That model is effective for the current product stage because it is simple,
traceable, and deterministic.

It also has clear long-term limits:

- orchestration logic is centralized in a workflow object rather than a system kernel;
- agents depend on concrete execution flow;
- extensibility is pipeline-oriented rather than capability-oriented;
- memory, reasoning, and decision responsibilities are distributed across modules
  without a unifying execution abstraction;
- future UI, CLI, API, and SDK surfaces would all need to bind to the same
  pipeline rather than to a stable kernel contract.

The target state is a **Kernel-Oriented Veraxis** architecture.

## Current Coordinator vs Future Kernel

| Dimension | Current Coordinator | Future Veraxis Kernel |
| --- | --- | --- |
| Primary role | Execute a predefined sequence of agents | Orchestrate capabilities, memory, reasoning, and decision flows |
| Extensibility model | Add or reorder agents in a pipeline | Register and compose capabilities dynamically |
| Coupling style | Workflow-level coupling | Contract-driven orchestration through abstractions |
| Execution style | Sequential Hub & Spoke | Capability-oriented, event-aware kernel orchestration |
| System boundary | Pipeline runtime | Platform runtime |
| Memory integration | Point-to-point | Kernel-mediated |
| Decision integration | Distributed | Explicit kernel-governed |

## Why Capability-Oriented Design

Veraxis must evolve from “a pipeline of agents” into “a platform of analytical
capabilities”.

That shift is required because:

- different product surfaces will need the same analytical capabilities;
- capabilities should be reusable without embedding knowledge of the full pipeline;
- reasoning, memory, and decision services should be invoked as platform
  primitives, not as side effects of agent sequence;
- enterprise evolution requires stable platform contracts before heavy feature expansion.

A capability-oriented system allows Veraxis to expose:

- dataset profiling;
- analytical planning;
- statistical analysis;
- anomaly detection;
- root cause analysis;
- knowledge querying;
- reasoning over prior analyses;
- recommendation generation;
- report composition.

Each of these should become a first-class platform capability.

## Why Agents Must Not Know Other Modules Directly

Agents should not directly know or coordinate concrete engines because that
creates long-term fragility:

- hard-coded module knowledge reduces replaceability;
- cross-module awareness increases hidden coupling;
- testing becomes workflow-specific instead of contract-specific;
- future eventing and API-driven invocation become harder to stabilize.

In the target architecture, agents should depend on:

- capability contracts;
- memory abstractions;
- kernel-issued execution context;
- event contracts;
- decision interfaces.

This enables the kernel to remain the orchestration boundary.

## Target Layer Model

```text
+-------------------------------------------------------------------+
| UI / CLI / API / SDK Layer                                        |
| Human interfaces and integration surfaces                         |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Domain Pack Layer                                                 |
| Domain-specific rules, vocabulary, KPIs, templates, policies      |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Learning Layer                                                    |
| Confidence evolution, feedback learning, experience progression   |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Decision Layer                                                    |
| Prioritization, recommendation selection, decision support        |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Inference Layer                                                   |
| Optional narrative, language assistance, future LLM integrations  |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Reasoning Layer                                                   |
| Deterministic reasoning, comparison, planning-to-decision logic   |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Knowledge Layer                                                   |
| Knowledge Graph, lineage, query, mapping, graph governance        |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Memory Layer                                                      |
| Analysis memory, session memory, query history, experience state  |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Event Layer                                                       |
| Event contracts, lifecycle signals, state transitions             |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Capability Layer                                                  |
| Analytical capabilities exposed as platform primitives            |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
| Veraxis Kernel                                                    |
| Runtime orchestration, policy enforcement, execution governance   |
+-------------------------------------------------------------------+
```

## Layer Responsibilities

### Veraxis Kernel

The kernel becomes the runtime center of the platform.

It is responsible for:

- capability discovery and invocation;
- execution policy;
- orchestration contracts;
- context propagation;
- error isolation;
- deterministic execution governance;
- coordination of memory, knowledge, reasoning, and decision layers.

### Capability Layer

The capability layer exposes reusable analytical functions as platform contracts.

Examples:

- dataset profiling capability;
- analytical planning capability;
- anomaly detection capability;
- reasoning capability;
- reporting capability.

### Event Layer

The event layer defines platform lifecycle signals without forcing a full
distributed architecture.

Examples:

- dataset loaded;
- validation completed;
- planning completed;
- anomaly detected;
- recommendation generated;
- report finalized.

This creates an evolution path toward event-driven behavior while preserving the
current offline-first local runtime.

### Memory Layer

The memory layer stores structured operational and analytical memory.

It includes:

- analysis session memory;
- query history;
- pattern memory;
- future experience memory;
- confidence evolution state.

### Knowledge Layer

The knowledge layer maintains explicit analytical structure.

It covers:

- Knowledge Graph nodes and edges;
- graph lineage;
- deterministic graph queries;
- mapping from runtime context to graph structure;
- graph quality and future governance.

### Reasoning Layer

The reasoning layer is where deterministic analytical thinking happens.

It should orchestrate:

- planning logic;
- comparison logic;
- reusable pattern extraction;
- next analytical step generation;
- evidence alignment between memory and knowledge.

### Inference Layer

The inference layer is explicitly **optional**.

It may include:

- natural language explanation;
- executive summary polishing;
- narrative report enhancement;
- optional advanced conversational assistance.

It must not become the only source of critical analytical decisions.

### Decision Layer

The decision layer transforms evidence into action.

It is responsible for:

- recommendation prioritization;
- confidence-sensitive next actions;
- risk-aware suggestion selection;
- future decision support contracts.

### Learning Layer

The learning layer accumulates reliable experience over time.

It should support:

- feedback-based updates;
- promotion and demotion of strategies;
- reuse scoring;
- future experience engine behavior.

### Domain Pack Layer

The Domain Pack layer injects controlled domain specialization.

It provides:

- KPIs;
- business vocabulary;
- analytical rules;
- report conventions;
- strategy hints;
- domain-specific policies.

### UI / CLI / API / SDK Layer

This is where Veraxis becomes a platform rather than a single interface.

The same kernel should eventually serve:

- dashboard UI;
- CLI workflows;
- API invocation;
- SDK consumption;
- future automation and integration surfaces.

## How the Kernel Will Orchestrate the Platform

The future kernel should orchestrate the system in this order:

```text
Request
  |
  v
Kernel receives execution intent
  |
  v
Kernel resolves required capabilities
  |
  v
Kernel loads memory and knowledge context
  |
  v
Kernel invokes reasoning contracts
  |
  v
Kernel obtains decision outputs
  |
  v
Kernel routes to experience / interface surfaces
```

This means the kernel becomes responsible for selecting platform primitives
rather than simply running a hard-coded pipeline of concrete agents.

## What Must Remain Deterministic

The following must remain deterministic and offline-first:

- dataset profiling;
- analytical planning;
- statistical computation;
- anomaly detection;
- root cause evidence generation;
- knowledge graph persistence and query;
- reasoning over prior analyses;
- recommendation prioritization for critical analytical actions;
- memory updates and confidence progression.

## What May Use LLMs as an Optional Layer

The following may use LLMs, but only as optional support:

- narrative explanation;
- executive summary style improvement;
- report wording refinement;
- advanced conversational assistance;
- optional interface-level language transformation.

These concerns belong to the inference or experience boundary, not to the core
decision path.

## Architectural Transition Strategy

The repository should not jump directly from the current Coordinator to a fully
abstract kernel without staged foundations.

The transition path should be:

1. document the kernel target architecture;
2. define capability contracts;
3. isolate concrete engines behind abstractions;
4. introduce event contracts;
5. move orchestration responsibilities into kernel-friendly interfaces;
6. progressively reduce workflow-level coupling;
7. expose kernel-driven execution to multiple surfaces.

## Status

This document defines the **target architecture**.

It does not claim that the kernel runtime is already implemented in the current
repository.

## V2.1.2 Kernel Runtime Foundation

V2.1.2 introduces the first runtime base of the Veraxis Kernel as an
**experimental, parallel foundation**.

This release does **not** replace the current `Coordinator` pipeline.

It adds a minimal kernel runtime that exists alongside the current execution
model so the architecture can evolve safely without destabilizing production
behavior.

The runtime foundation currently includes:

- a `VeraxisKernel` orchestration object;
- a deterministic `Capability` contract with structured requests and responses;
- a `CapabilityRegistry` for controlled capability registration;
- a minimal in-memory `EventBus` for lifecycle signals;
- an in-memory `KernelMemory` with no disk persistence;
- custom kernel errors for missing, duplicate, and failed capability execution;
- a built-in `HealthCheckCapability` for deterministic runtime inspection.

This runtime layer is intentionally non-invasive:

- the main pipeline remains Coordinator-based;
- existing agents are unchanged;
- dashboard behavior is unchanged;
- no external dependencies are introduced;
- no OpenAI dependency is added to the kernel runtime;
- no kernel memory is persisted to disk in this release.

The goal of V2.1.2 is not feature expansion.

The goal is to establish a safe execution contract that future capabilities,
memory adapters, reasoning modules, and decision flows can target without
forcing an immediate migration of the current product.
