# VERAXIS

## Offline-first Analytical Intelligence Platform

### Transform data into explainable decisions.

**A deterministic Senior Data Analyst that learns from previous analyses without depending on LLMs.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square)
![Offline First](https://img.shields.io/badge/Offline-First-0F4C81?style=flat-square)
![Deterministic Reasoning](https://img.shields.io/badge/Deterministic-Reasoning-334155?style=flat-square)
![Knowledge Graph](https://img.shields.io/badge/Knowledge-Graph-7C3AED?style=flat-square)
![Multi-Agent](https://img.shields.io/badge/Multi--Agent-Pipeline-065F46?style=flat-square)
![Tests Passing](https://img.shields.io/badge/Tests-215%20passed-15803D?style=flat-square)
![Version](https://img.shields.io/badge/V2-Architecture%20Foundation-111827?style=flat-square)

---

## What Is Veraxis

Veraxis is an Analytical Intelligence Platform.

It is not a chatbot.

It is not a BI dashboard.

It is not a thin framework around prompts.

It is a deterministic system that turns raw datasets into statistical analysis,
explainable insight, anomaly detection, root cause evidence, analytical memory,
experience-aware recommendations, and professional reports.

---

## Product Pillars

| Pillar | Purpose | Current Status | Future Evolution |
| --- | --- | --- | --- |
| Knowledge | Persist analytical structure, lineage, code graph, and analysis memory | Knowledge Graph JSON, Query Engine, Code Indexer, Comparator | Governance, quality controls, schema evolution |
| Reasoning | Reuse previous analyses to suggest better next steps | Deterministic Knowledge Reasoning Engine completed | Deeper experience-weighted reasoning |
| Experience | Convert history into reusable analytical practice | Analytical memory and pattern foundations available | Dedicated Experience Engine |
| Decision | Turn evidence into next analytical actions | Recommendation logic partially present in reasoning flows | Full Decision Intelligence Layer |
| Learning | Improve confidence, pattern reuse, and reliability over time | Learning Engine and pattern knowledge foundation | Outcome-based recommendation learning |

---

## Why Veraxis

| Dimension | Traditional BI | LLM Chatbot | Veraxis |
| --- | --- | --- | --- |
| Knowledge | Static dashboards and reports | Session-local conversation | Persistent analytical knowledge layer |
| Reasoning | Mostly manual analyst work | Mostly generative text | Deterministic analytical reasoning |
| Memory | Limited history | Weak and non-auditable | Analytical memory with reusable patterns |
| Explainability | KPI views, limited rationale | Often narrative without evidence | Evidence-backed and traceable |
| Offline | Partial | Rare | Core design principle |
| Deterministic | Query outputs only | Usually not | Required for critical analysis |
| Recommendations | External analyst interpretation | Prompt-based suggestions | Experience-aware analytical next steps |
| Decision Support | Dashboard-dependent | Narrative-dependent | Structured evidence and reasoning |
| Learning | Mostly organizational, outside tool | Implicit and opaque | Local, explicit, and auditable |

---

## Architecture

```text
+------------------------------------------------------------------+
| Core Platform                                                    |
| Pipeline, ingestion, context, validation, processing, runtime    |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| Knowledge Platform                                               |
| Knowledge Graph, indexing, lineage, query engine, comparison     |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| Intelligence Platform                                            |
| Planning, statistics, anomaly detection, root cause, reasoning   |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| Decision Platform                                                |
| Prioritization, next analytical steps, decision support          |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| Learning Platform                                                |
| Pattern learning, confidence updates, analytical memory reuse    |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
| Experience Platform                                              |
| Reports, dashboard, chat surfaces, optional narrative layer      |
+------------------------------------------------------------------+
```

| Layer | Role |
| --- | --- |
| Core Platform | Runs the product and moves data through the pipeline |
| Knowledge Platform | Makes analytical structure explicit and queryable |
| Intelligence Platform | Computes what the system should analyze and why |
| Decision Platform | Converts evidence into prioritized actions |
| Learning Platform | Accumulates reliability and reusable experience |
| Experience Platform | Presents results as enterprise-grade outputs |

---

## How Veraxis Thinks

```text
Dataset
   |
   v
Planning
   |
   v
Reasoning
   |
   v
Statistics
   |
   v
Knowledge
   |
   v
Experience
   |
   v
Decision
   |
   v
Report
```

Veraxis separates **language** from **analysis**.

The product first decides how to analyze.

Only then does it decide how to explain.

---

## Implemented Modules

| Module | Description | Status |
| --- | --- | --- |
| Coordinator | Hub & Spoke multi-agent orchestration | Implemented |
| Knowledge Graph | Local JSON graph for code and analysis lineage | Implemented |
| Reasoning Engine | Deterministic reuse of previous analytical experience | Implemented |
| Query Engine | Deterministic graph querying and rule-based answers | Implemented |
| Analytical Planning | Strategy and execution planning before statistics | Implemented |
| Dash | Local product UI and operator workflow | Implemented |
| Report Generator | Professional report assembly with local-first fallback | Implemented |
| Experience Memory | Analytical memory, patterns, confidence, session history | Foundation implemented |
| Analysis Comparator | Comparison of recent analysis runs | Implemented |
| Validation Lab | Evidence-driven validation structure and quality gates | Implemented |
| Knowledge Reasoning | Similar analysis detection and recommendation layer | Implemented |

---

## Offline First

Veraxis does **not** require OpenAI to run its analytical core.

### Core Guarantees

- the platform can ingest, process, analyze, compare, and reason locally;
- critical analytical decisions are deterministic;
- Knowledge Graph reasoning is local;
- anomaly and root cause logic are not delegated to a language model.

### LLM Role

LLMs are optional and should be used only as:

- Narrative Layer
- Executive Summary
- Natural Language Explanation

Never as the primary decision engine.

This is a product rule, not a temporary implementation detail.

---

## Knowledge Graph

```text
Dataset
   |
   v
Analysis
   |
   v
Insights
   |
   v
Anomalies
   |
   v
Root Causes
   |
   v
Recommendations
   |
   v
Experience
```

### What It Indexes

- Python files, classes, functions, and imports
- analysis runs
- datasets
- dataframe columns
- insights
- anomalies
- root causes
- reports
- domain pack usage

### What It Stores

- stable node ids
- relationship edges
- dataset shape
- column names
- dtypes
- compact synthetic metadata
- traceable analysis lineage

### What It Does Not Store

- raw dataframe rows
- massive column value dumps
- secrets
- opaque binary memory blobs

### Storage Location

```text
data/knowledge_graph/knowledge_graph.json
```

### Query It

```bash
python3 scripts/index_knowledge_graph.py
python3 scripts/query_knowledge_graph.py "quali funzioni generano grafici?"
python3 scripts/show_latest_analyses.py --limit 10
python3 scripts/compare_latest_analyses.py
```

---

## Experience Engine

Veraxis does not simply store analyses.

It accumulates experience.

### What That Means

- if a metric was repeatedly useful, Veraxis can reuse that signal;
- if anomalies looked similar in previous runs, Veraxis can surface that memory;
- if specific segmentations or strategies proved useful, Veraxis can recommend them again;
- if root cause patterns recur, Veraxis can treat them as reusable analytical evidence.

### Current State

The experience model already has foundations in:

- analytical memory;
- pattern knowledge;
- learning state;
- analysis comparison;
- Knowledge Reasoning Engine.

### Next Step

The dedicated Experience Engine is the next architectural layer that will turn
these foundations into a first-class deterministic learning capability.

---

## CLI

### Index

```bash
python3 scripts/index_knowledge_graph.py
```

### Query

```bash
python3 scripts/query_knowledge_graph.py "quali funzioni generano grafici?"
```

### Compare

```bash
python3 scripts/compare_latest_analyses.py
```

### Latest Analyses

```bash
python3 scripts/show_latest_analyses.py --limit 10
```

### Reasoning

The deterministic reasoning engine is already available through the service
layer and the multi-agent pipeline. The operator-facing CLI contract planned for
this capability is:

```bash
python3 scripts/reason_about_dataset.py --columns response_time created_at status channel --primary-metric response_time --time-axis created_at --source-type csv --row-count 100000
```

This command shape documents the product direction without renaming runtime
packages or claiming a released script that is not yet present in the repository.

---

## Quick Start

### Linux / macOS

```bash
git clone https://github.com/BigHeroUp/skills_agent.git
cd skills_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest -q
python3 main.py
```

### Windows

```powershell
git clone https://github.com/BigHeroUp/skills_agent.git
cd skills_agent
python3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python3 -m pytest -q
python3 main.py
```

---

## Roadmap

- [x] Milestone 1 - Multi-agent platform foundation
- [x] Milestone 2 - Deterministic analysis foundation
- [x] Milestone 3 - Analytical planning and local reasoning foundation
- [x] Milestone 4 - Analytical memory and session progression foundation
- [x] Milestone 5 - Pattern knowledge and learning foundation
- [x] Milestone 6 - Knowledge Reasoning Engine
- [ ] Milestone 7 - Knowledge Graph Governance & Quality
- [ ] Milestone 8 - Experience Engine
- [ ] Milestone 9 - Recommendation Engine
- [ ] Milestone 10 - Decision Intelligence Layer
- [ ] Milestone 11 - Domain Intelligence Packs / Marketplace direction
- [ ] Milestone 12 - Optional LLM Narrative Layer

---

## Documentation

| Document | Description |
| --- | --- |
| [docs/VISION.md](docs/VISION.md) | Product thesis and long-term positioning |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | V2 six-layer architecture |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Planned V2 milestone trajectory |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records |
| [docs/MILESTONES.md](docs/MILESTONES.md) | Milestone-level goals, status, and expected tests |
| [docs/OFFLINE_FIRST.md](docs/OFFLINE_FIRST.md) | Offline-first operating rule |
| [docs/V2_PRODUCT_MODEL.md](docs/V2_PRODUCT_MODEL.md) | Target users, use cases, and product model |
| [validation_lab/README.md](validation_lab/README.md) | Validation Lab operating model |

---

## Development Principles

- **Architecture before Features**
- **Offline First**
- **Deterministic before Generative**
- **No Raw Data Persistence**
- **Explainability**
- **Test First**
- **Enterprise Quality**

---

## Product Status

```text
Core        ██████████
Knowledge   ██████████
Reasoning   █████████░
Experience  ██████░░░░
Decision    ████░░░░░░
Learning    ████░░░░░░
```

---

## Footer

### Working Name Notice

Veraxis is currently the working product name.

### Repository Notice

The repository remains named `skills_agent` until branding due diligence is completed.

### License

No repository license file is currently declared at the root level.

### Contribution

Contributions should preserve the core product principles:

- deterministic analytical decisions;
- offline-first behavior;
- explainable outputs;
- no raw data persistence;
- releasable milestones.
