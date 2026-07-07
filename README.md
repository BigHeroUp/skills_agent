# 🚀 Skills Agent

<div align="center">

### **An Autonomous AI Platform that Thinks Like a Senior Data Analyst**

Transform raw datasets into professional, explainable analyses through autonomous reasoning, statistical intelligence and modular domain knowledge.

---

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange?style=for-the-badge)
![Architecture](https://img.shields.io/badge/Architecture-Hub%20%26%20Spoke-blue?style=for-the-badge)

</div>

---

# 📖 Overview

Most AI assistants answer questions.

**Skills Agent is designed to reason before answering.**

Instead of simply describing data, Skills Agent builds an analytical strategy, selects the most appropriate statistical techniques, detects anomalies, learns from previous analyses and produces explainable reports similar to those created by an experienced **Senior Data Analyst**.

The long-term vision is to create an autonomous analytical platform capable of progressively reducing its dependency on external Large Language Models while maintaining professional-grade analytical capabilities.

---

# 🎯 Vision

The goal is not to build another chatbot.

The goal is to build an **AI Data Analyst** capable of reasoning through data like an experienced professional.

Skills Agent should autonomously:

- Understand the user's analytical objective.
- Inspect and interpret datasets.
- Build an analytical strategy.
- Select the most appropriate statistical techniques.
- Detect patterns and anomalies.
- Learn from previous analyses.
- Produce explainable reports.
- Continuously improve through accumulated knowledge.

Ultimately, the platform aims to become a reusable analytical engine adaptable to different business domains without changing its core architecture.

---

# ❓ Why Skills Agent?

| Traditional AI Assistant | Skills Agent |
|--------------------------|--------------|
| Answers prompts | Builds analytical strategies |
| Describes data | Reasons about data |
| Generic knowledge | Modular domain knowledge |
| One-shot responses | Iterative analysis |
| Hidden reasoning | Fully explainable reasoning |
| Prompt dependent | Learning engine |
| Generic statistics | Autonomous statistical selection |

---

# ✨ Main Features

## 🧠 Autonomous Analytical Reasoning

The platform determines **how** data should be analyzed before executing any statistical computation.

---

## 📊 Advanced Statistical Engine

Supports advanced statistical techniques including:

- Descriptive statistics
- Percentiles
- Trend analysis
- Dispersion analysis
- Correlation analysis
- Threshold comparison
- Frequency analysis
- Missing data analysis

---

## 🚨 Anomaly Detection

Automatically detects:

- Outliers
- Time-series spikes
- Performance degradation
- Threshold violations
- Distribution changes
- Baseline deviations

---

## 🔎 Root Cause Analysis

Groups anomalies, patterns, trends and statistical evidence to propose explainable possible root causes without relying on external AI services.

The engine distinguishes:

- Evidence
- Hypotheses
- Alternative explanations
- Recommended actions
- Confidence and severity

---

## 📚 Learning Engine

Every analysis contributes to improving future analytical decisions.

The platform continuously refines:

- Pattern confidence
- Strategy recommendations
- Analytical priorities

---

## 🧩 Domain Intelligence Packs

The analytical engine remains completely generic.

Domain expertise is loaded dynamically through reusable **Domain Intelligence Packs** containing:

- KPIs
- Pattern libraries
- Business terminology
- Report templates
- Decision rules
- Analytical strategies

---

## 📄 Explainable Reports

Every conclusion is designed to be fully explainable.

Instead of saying:

> "An anomaly was detected."

The platform explains:

- Why it was detected
- Which algorithms were used
- Which evidence was considered
- Confidence level
- Recommended actions

---

## Validation Lab

Skills Agent uses a Validation Lab to evaluate the system against real and synthetic evidence instead of relying only on implementation milestones.

The lab tracks:

- analytical correctness;
- report quality;
- dashboard UX;
- LLM Gateway robustness;
- domain pack maturity.

See:

- [Validation Lab README](validation_lab/README.md)
- [Quality Gates](validation_lab/quality_gates.md)

---

## Knowledge Graph Layer

Skills Agent includes a first internal Knowledge Graph Layer designed to make
analysis and code relationships explicit without introducing heavy external
dependencies.

The layer indexes:

- Python files, classes, functions and imports through a static `ast` indexer;
- analysis runs, datasets, dataframe columns, insights, anomalies, root causes
  and generated reports through the pipeline context;
- domain pack usage when a domain pack is detected.

The graph is persisted as local JSON in:

```text
data/knowledge_graph/knowledge_graph.json
```

To index the repository code:

```bash
python scripts/index_knowledge_graph.py
```

The JSON structure stores explicit `nodes` and `edges`, with stable ids,
properties and relationship names such as `CONTAINS`, `IMPORTS`,
`USES_DATASET`, `HAS_COLUMN`, `DETECTED_ANOMALY` and
`PROPOSED_ROOT_CAUSE`. This makes it Graphify-ready: the same snapshot can be
loaded later into graph databases, visualization tools or semantic graph
pipelines without changing the core analytical pipeline.

No raw dataframe rows are stored. The analysis mapper only persists metadata
such as shape, column names, dtypes and compact synthetic summaries.

## Querying the Knowledge Graph

The local graph can be queried deterministically without OpenAI through the
Knowledge Graph Query Layer.

Example commands:

```bash
python scripts/query_knowledge_graph.py "quali funzioni generano grafici?"
python scripts/query_knowledge_graph.py "quali analisi hanno anomalie su response_time?"
```

The query layer supports:

- node filters by type, label and properties;
- edge filters by relationship, source and target;
- neighbor lookup for incoming, outgoing or bidirectional relationships;
- code search over Python files, classes, functions and imports;
- analysis search over runs, datasets, columns, insights, anomalies, root causes
  and reports;
- first rule-based answers in Italian for questions about functions, classes,
  files, imports, analyses, anomalies, root causes, columns, `response_time`,
  charts, Excel, Oracle and reports.

If `data/knowledge_graph/knowledge_graph.json` does not exist yet, the CLI
returns a clear message and asks to run the indexing script first.

## Knowledge Graph in Dash Chat

The Dash follow-up chat can route Knowledge Graph questions to the deterministic
query engine before using conversational fallbacks.

Supported examples:

```text
quali funzioni generano grafici?
quali classi usano Oracle?
quali anomalie sono presenti nel grafo?
quali colonne compaiono nelle analisi precedenti?
```

The chat response includes the deterministic answer, confidence score,
execution type and up to 10 matching graph nodes with compact properties. If
the local JSON graph has not been generated yet, the chat returns a readable
message instead of failing.

## Knowledge Graph Explorer

The dashboard includes a first visual Knowledge Graph Explorer built with
Plotly and Dash, without Neo4j, NetworkX or extra frontend dependencies.

The MVP shows the lineage of the latest saved analysis run:

```text
analysis_run -> dataset
analysis_run -> dataframe_column
analysis_run -> insight
analysis_run -> anomaly
analysis_run -> root_cause
analysis_run -> report
```

The explorer appears after an analysis completes and can be refreshed with the
`Aggiorna grafo` button. Clicking a node opens a compact detail panel with
label, type, id and the first relevant properties.

If `data/knowledge_graph/knowledge_graph.json` does not exist, or if no
`analysis_run` is available yet, the explorer shows a readable empty-state
message instead of failing.

MVP limits:

- only the `latest_analysis_lineage` view is rendered;
- nodes are capped at 80 for readability;
- layout is deterministic by node type, not force-directed;
- graph editing and full-code graph exploration are intentionally deferred.

---

# 🏗 Architecture

The project follows a modular **Hub & Spoke Architecture**.

```text
                    User Request
                          │
                          ▼
                 Coordinator Agent
                          │
                          ▼
               Data Processor Agent
                          │
                          ▼
          Analytical Reasoning Layer
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
 Statistical      Pattern Knowledge    Learning
    Engine             Engine          Engine
          │
          ▼
  Anomaly Detection Engine
          │
          ▼
 Root Cause Analysis Engine
          │
          ▼
 Senior Data Analyst Engine
          │
          ▼
 Explainability Engine
          │
          ▼
   Professional Report
          │
          ▼
 Domain Intelligence Packs
```

Each component is independent, making the platform scalable and easy to extend.

---

# 🔄 Analytical Workflow

Every analysis follows the same reasoning pipeline.

```text
User Request

        │

        ▼

Dataset Inspection

        │

        ▼

Analytical Strategy Generation

        │

        ▼

Pattern Recognition

        │

        ▼

Statistical Analysis

        │

        ▼

Anomaly Detection

        │

        ▼

Root Cause Analysis

        │

        ▼

Learning

        │

        ▼

Explainability

        │

        ▼

Professional Report
```

---

# 🧩 Domain Intelligence Packs

One of the key architectural principles of Skills Agent is the complete separation between **analytical logic** and **domain knowledge**.

The Core Engine remains entirely domain-independent.

Domain-specific expertise is encapsulated inside reusable **Domain Intelligence Packs**.

Each pack can provide:

- KPI definitions
- Domain terminology
- Pattern libraries
- Analytical strategies
- Business rules
- Clarification questions
- Report templates
- Recommendations

Adding support for a new domain should require **no changes to the Core Engine**.

Only a new Domain Intelligence Pack.

---

# 🛣 Roadmap

## ✅ Core Platform

- Learning Engine
- Analytical Reasoning Layer
- Advanced Statistical Engine
- Anomaly Detection Engine
- Domain Intelligence Packs Architecture
- Root Cause Analysis Engine

---

## 🚧 In Progress

- Explainability Engine
- Predictive Analytics
- Automated Visualization Engine
- Local Knowledge Base
- Multi-domain Intelligence Packs
- Autonomous Insight Generation

---

# 💡 Design Principles

Skills Agent is built around five core principles.

### Modular Architecture

Every engine is independent and reusable.

---

### Explainability

Every conclusion should be understandable and traceable.

---

### Deterministic Analysis

Statistical results should always be reproducible.

---

### Continuous Learning

Past analyses improve future analytical decisions.

---

### Domain Independence

The engine stays generic.

Knowledge becomes modular.

---

# Philosophy

> **The engine stays generic.**

> **Knowledge becomes modular.**

> **Intelligence becomes reusable.**

Skills Agent separates analytical capabilities from domain expertise, enabling the creation of a reusable AI analytical platform that can evolve through modular knowledge without continuously changing its core architecture.
