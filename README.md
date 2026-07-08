# Veraxis

## Offline-first Analytical Intelligence Platform

**A deterministic Senior Data Analyst that learns from previous analyses without depending on LLMs.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-215%20passed-2E8B57?style=for-the-badge)
![Offline First](https://img.shields.io/badge/Offline-First-1F4E79?style=for-the-badge)
![Deterministic Reasoning](https://img.shields.io/badge/Deterministic-Reasoning-4B5563?style=for-the-badge)
![Knowledge Graph](https://img.shields.io/badge/Knowledge-Graph-8B5CF6?style=for-the-badge)

Veraxis is the working product identity for the platform currently hosted in the
`skills_agent` repository. It is designed as an enterprise-grade Analytical
Intelligence system that turns raw datasets into repeatable analysis, explainable
evidence, reusable analytical memory, and professional reporting.

## Product Positioning

Veraxis is not positioned as a generic assistant. It is an Analytical
Intelligence Platform built to transform raw operational datasets into:

- statistical analysis;
- explainable insights;
- anomaly detection;
- root cause analysis;
- professional reports;
- analytical memory;
- experience-based recommendations.

Its central thesis is simple: analytical decisions should come from
deterministic reasoning, explicit statistical methods, and accumulated
experience, not from opaque generative text alone.

## Why This Is Not a Simple Chatbot

| Capability | Traditional BI | Generic AI Chatbot | Veraxis |
| --- | --- | --- | --- |
| Primary interaction model | Dashboard and static queries | Conversational prompting | Analytical workflow plus deterministic reasoning |
| Statistical reasoning core | Usually delegated to analyst tooling | Usually absent or implicit | Built into the platform |
| Knowledge Graph | Rarely central | Usually none | Native local analytical memory layer |
| Analytical memory | Limited dashboards/history | Weak session memory | Persistent reusable analysis memory |
| Offline-first operation | Partial | Rare | Core architectural principle |
| LLM dependency | None | High | Optional and non-critical |
| Critical analytical decisions | Human/manual | Often prompt-driven | Deterministic and auditable |
| Root cause and anomaly evidence | External workflow | Often narrative only | Evidence-based pipeline output |

## Architecture V2

Veraxis V2 formalizes the platform into six macro-layers.

### The Six Layers

- **Core Platform**: orchestration, ingestion, shared context, runtime control, UI hooks.
- **Knowledge Platform**: Knowledge Graph, query layer, lineage, comparison, graph indexing.
- **Intelligence Platform**: planning, statistics, anomaly detection, root cause analysis, reasoning.
- **Decision Platform**: next analytical steps, prioritization, confidence-driven actions.
- **Learning Platform**: analytical memory, pattern reuse, confidence evolution, feedback learning.
- **Experience Platform**: reports, dashboard interactions, chat surfaces, narrative enrichment.

### Readable Layer Diagram

```text
+-------------------------------------------------------------+
| Experience Platform                                         |
| Reports, Dash UI, follow-up chat, optional narrative layer  |
+-------------------------------------------------------------+
| Learning Platform                                           |
| Analytical memory, pattern learning, confidence evolution   |
+-------------------------------------------------------------+
| Decision Platform                                           |
| Recommendation logic, prioritization, next-step selection   |
+-------------------------------------------------------------+
| Intelligence Platform                                       |
| Planning, statistics, anomaly, root cause, reasoning        |
+-------------------------------------------------------------+
| Knowledge Platform                                          |
| Knowledge Graph, lineage, query engine, comparator, indexer |
+-------------------------------------------------------------+
| Core Platform                                               |
| Pipeline, context, ingestion, validation, processing        |
+-------------------------------------------------------------+
```

Detailed architecture documentation is available in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Implemented Capabilities

The repository already includes the following platform capabilities.

### Core Execution

- Hub & Spoke multi-agent pipeline;
- data source management;
- CSV support;
- Excel support;
- Oracle read-only support;
- data validation;
- data processing;
- dashboard-driven execution flow.

### Analytical Intelligence

- Analytical Planning Engine;
- deterministic statistical analysis;
- anomaly detection;
- root cause analysis;
- Senior Data Analyst Engine;
- report generation;
- analytical strategy and reasoning layers.

### Knowledge and Memory

- Knowledge Graph persisted as local JSON;
- Python code indexer;
- deterministic Knowledge Graph Query Engine;
- Dash chat integration with the Knowledge Graph;
- analytical memory and pattern reuse;
- analysis comparator;
- Knowledge Reasoning Engine;
- local learning engine and pattern knowledge foundation.

### Tooling and Quality

- CLI utilities for indexing, querying, comparing and reviewing analysis memory;
- Validation Lab with test cases, quality gates, review templates and benchmarks.

## Offline-first Philosophy

Veraxis is built around an offline-first analytical core.

### What Works Without OpenAI

- Knowledge Graph persistence and querying;
- deterministic reasoning over previous analyses;
- Analytical Planning Engine;
- statistical analysis;
- anomaly detection;
- root cause analysis;
- report facts and core analytical conclusions;
- analytical memory and comparison flows.

### What LLMs Are Allowed To Do

LLMs are optional and can be used only as a narrative or explanation layer for:

- natural-language explanations;
- narrative report polishing;
- executive summaries;
- language reformulation;
- advanced chat assistance.

### Hard Rule

Critical analytical decisions must be deterministic. An LLM must not be the
sole source of truth for:

- KPI selection;
- anomaly declaration;
- root cause evidence;
- confidence ranking;
- analytical recommendations.

See the formal policy in [docs/OFFLINE_FIRST.md](docs/OFFLINE_FIRST.md).

## Knowledge Graph

The Knowledge Graph makes code and analytical history explicit without requiring
an external graph database.

### What It Indexes

- Python files, classes, functions and imports;
- analysis runs;
- datasets;
- dataframe columns;
- insights;
- anomalies;
- root causes;
- reports;
- domain pack usage.

### What It Stores

The local graph stores:

- stable node ids;
- edge relationships;
- dataset shape;
- column names;
- dtypes;
- compact analytical metadata;
- synthetic properties required for comparison and reasoning.

### What It Does Not Store

For privacy and reproducibility reasons, it does **not** store:

- raw dataframe rows;
- bulk column values;
- large raw payload dumps;
- operational secrets.

### Storage Location

```text
data/knowledge_graph/knowledge_graph.json
```

### Query and Inspection Commands

```bash
python3 scripts/index_knowledge_graph.py
python3 scripts/query_knowledge_graph.py "quali funzioni generano grafici?"
python3 scripts/show_latest_analyses.py --limit 10
python3 scripts/compare_latest_analyses.py
```

## Knowledge Reasoning Engine

The Knowledge Reasoning Engine turns the Knowledge Graph from a queryable memory
store into a deterministic reasoning layer for analytical reuse.

### Current Scope

- dataset profile extraction from `AgentContext`;
- similar analysis detection;
- reusable pattern extraction;
- analytical recommendation generation;
- deterministic scoring and ranking;
- no OpenAI dependency.

### How It Works

The engine builds a compact synthetic profile using:

- column names;
- dtypes;
- row and column counts;
- primary metric;
- time axis;
- source type;
- semantic roles;
- compact keywords.

It then compares this profile with stored analysis runs to:

- find similar analyses;
- extract recurring metrics, anomalies, root causes and strategies;
- recommend next analytical steps.

### CLI Operator Contract

The deterministic reasoning engine is already available through the Python
service layer and pipeline integration. The thin operator-facing CLI wrapper is
not yet present in the repository; the intended command shape is:

```bash
python3 scripts/reason_about_dataset.py --columns response_time created_at status channel --primary-metric response_time --time-axis created_at --source-type csv --row-count 100000
```

This command shape documents the V2 product contract without renaming runtime
packages or inventing a released script.

## Quick Start

```bash
git clone https://github.com/BigHeroUp/skills_agent.git
cd skills_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest -q
python3 main.py
```

Windows activation:

```powershell
.venv\Scripts\activate
```

## Project Status

- V2 Architecture Foundation: completed
- Milestone 6 Knowledge Reasoning Engine: completed
- Current test suite: 215 passed
- Next planned milestone: Knowledge Graph Governance & Quality or Analytical
  Experience Engine; the roadmap may be refined as governance and product
  priorities evolve

## Documentation Map

- [Vision](docs/VISION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Architectural Decisions](docs/DECISIONS.md)
- [Milestones](docs/MILESTONES.md)
- [Offline-First Strategy](docs/OFFLINE_FIRST.md)
- [V2 Product Model](docs/V2_PRODUCT_MODEL.md)
- [Validation Lab](validation_lab/README.md)

## Roadmap Snapshot

- Analytical Experience Engine
- Knowledge Graph Governance & Quality
- Recommendation Engine
- Decision Intelligence Layer
- Domain Intelligence Packs
- Optional LLM Narrative Layer

## Development Philosophy

- Every milestone must leave the project releasable
- Offline-first
- Deterministic before generative
- Explainability
- No raw data persistence
- Test-first hardening
- Architecture before features

## Repository Naming Note

Veraxis is currently the working product name. The repository is still named
`skills_agent` until branding due diligence is completed.
