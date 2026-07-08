# Veraxis Development Guide

## Purpose

This guide defines the architectural and delivery rules for Veraxis as it moves
toward a Kernel-Oriented, capability-oriented platform.

It is a development governance document.

## Architecture before Features

No major feature should be added if the architectural boundary it depends on is
still undefined.

Veraxis should evolve by stabilizing:

- boundaries;
- abstractions;
- contracts;
- quality gates;
- deterministic execution behavior.

## Every New Feature Requires an ADR

Any feature that changes one of the following requires a new ADR:

- execution flow;
- memory model;
- orchestration contracts;
- capability contracts;
- domain pack lifecycle;
- LLM usage boundary;
- persistence model;
- API surface.

Small bug fixes do not require ADRs.

Architectural behavior changes do.

## How to Add a Capability

1. Define the capability purpose.
2. Define input and output contracts.
3. Define whether it is deterministic or optional-inference-assisted.
4. Identify required memory and knowledge dependencies.
5. Add validation and failure behavior.
6. Add tests.
7. Document the capability boundary.

A capability must be reusable outside a single workflow.

## How to Add an Agent

1. Define the agent role clearly.
2. Make the agent depend on abstractions, not concrete engines.
3. Limit agent responsibility to role execution, not platform orchestration.
4. Ensure failure isolation.
5. Add tests for success and non-blocking failure behavior.
6. Document how it fits current architecture and target kernel architecture.

Agents must not become hidden coordinators.

## How to Add a Domain Pack

1. Define domain scope and intended use cases.
2. Add pack metadata and versioning.
3. Provide KPIs, terminology, patterns, and strategy rules.
4. Validate JSON-safe structure.
5. Test pack detection and pack export behavior.
6. Document privacy and domain assumptions.

Domain Packs extend the platform without changing the core runtime principles.

## How to Add a New Memory

1. Define memory type and retention purpose.
2. Define what is stored and what is explicitly forbidden.
3. Ensure no raw data persistence unless a policy explicitly allows it.
4. Define update logic and confidence logic if applicable.
5. Add export and serialization guarantees.
6. Add tests for empty state, update, and replay behavior.

## How to Add a New CLI Script

1. Confirm there is a clear operator use case.
2. Keep the script thin.
3. Put business logic in services, not in the script body.
4. Use explicit arguments and readable output.
5. Add usage help and failure messages.
6. Add tests when behavior is non-trivial.
7. Document the script in README or relevant docs.

## Definition of Done

Work is done only when:

- architecture impact is understood;
- documentation is updated;
- tests pass;
- failure behavior is explicit;
- privacy implications are reviewed;
- deterministic boundaries are preserved;
- the milestone leaves the project releasable.

## Quality Gates

At minimum, new work must be evaluated for:

- deterministic correctness;
- serialization safety;
- explainability;
- privacy compliance;
- regression risk;
- fallback behavior without LLM;
- Validation Lab relevance when applicable.

## Testing Policy

- start with narrow tests close to the change;
- expand to regression tests when behavior crosses boundaries;
- prefer deterministic tests over prompt-shape tests;
- add failure-path coverage for non-blocking components;
- run `python3 -m pytest -q` before finalizing.

## Privacy Policy: No Raw Data Persistence

Veraxis must not persist raw dataframe rows into memory layers, graph layers, or
architectural persistence components unless an explicit future policy changes
that rule.

Allowed examples:

- row count;
- column count;
- column names;
- dtypes;
- semantic roles;
- compact synthetic metadata.

Forbidden examples:

- raw row snapshots;
- bulk column values;
- unbounded payload dumps;
- secrets.

## Offline-First Policy

The core platform must remain functional without OpenAI.

This includes:

- planning;
- statistics;
- anomaly detection;
- root cause analysis;
- knowledge graph query;
- knowledge reasoning;
- memory updates;
- critical recommendations.

LLMs are optional.

## Git Workflow

- branch from `main`;
- use focused feature branches;
- do not mix architecture documentation with unrelated runtime changes;
- run tests before commit;
- push feature branches without force push;
- do not rebase or reset destructively unless explicitly requested.

## Naming Conventions

- repository and runtime names remain `skills_agent` until an explicit rename;
- `Veraxis` can be used as working product name in documentation;
- architectural documents should distinguish **current architecture** from
  **target architecture**;
- use clear, explicit identifiers for capability and memory concepts.

## Codex Prompt Workflow

When using Codex or similar agents:

1. define the objective clearly;
2. state architectural boundaries;
3. specify whether runtime code changes are allowed;
4. require deterministic validation where relevant;
5. require final reporting of modified files, tests, and outcomes;
6. treat documentation, ADRs, and quality gates as first-class deliverables.

## Kernel-Oriented Transition Rule

Until the kernel exists, contributors should avoid deepening direct coupling
between agents and concrete services more than necessary.

Every significant change should make future extraction into:

- capability contracts;
- memory abstractions;
- kernel orchestration contracts;
- event contracts

easier, not harder.
