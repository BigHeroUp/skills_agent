"""Visualizzazione Plotly del Knowledge Graph locale."""

from __future__ import annotations

from collections import Counter
from math import cos, pi, sin
from typing import Any

import plotly.graph_objects as go

from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine


NODE_COLORS = {
    "analysis_run": "#4C78A8",
    "dataset": "#72B7B2",
    "dataframe_column": "#B279A2",
    "insight": "#54A24B",
    "anomaly": "#E45756",
    "root_cause": "#F58518",
    "report": "#9D9DA1",
}

NODE_LEVELS = {
    "analysis_run": 0,
    "dataset": 1,
    "dataframe_column": 2,
    "insight": 3,
    "anomaly": 4,
    "root_cause": 5,
    "report": 6,
}

MEMORY_LABELS = {
    "analysis_run": "Analisi",
    "dataset": "Dataset",
    "dataframe_column": "Colonne",
    "insight": "Insight",
    "anomaly": "Anomalie",
    "root_cause": "Root cause",
    "report": "Report",
    "python_file": "File Python",
    "python_class": "Classi",
    "python_function": "Funzioni",
    "python_import": "Import",
}

PIPELINE_AGENTS = [
    "DataSourceManager",
    "QuerySuggestion",
    "DataExtractor",
    "DataValidator",
    "DataProcessor",
    "KnowledgeReasoning",
    "Analyst",
    "ReportGenerator",
    "KnowledgeGraph",
    "ProductIntelligence",
]

LINEAGE_BUCKETS = [
    ("dataset", "ANALYZED_DATASET"),
    ("columns", "HAS_COLUMN"),
    ("insights", "PRODUCED_INSIGHT"),
    ("anomalies", "DETECTED_ANOMALY"),
    ("root_causes", "IDENTIFIED_ROOT_CAUSE"),
    ("reports", "GENERATED_REPORT"),
]


class KnowledgeGraphVisualizer:
    """Costruisce figure Plotly per il Knowledge Graph senza dipendenze extra."""

    def __init__(self, query_engine: KnowledgeGraphQueryEngine | None = None):
        self.query_engine = query_engine or KnowledgeGraphQueryEngine()

    def build_latest_analysis_lineage(self, max_nodes: int = 80) -> dict[str, Any]:
        """Visualizza la lineage dell'ultima analysis_run disponibile."""
        latest_runs = self.query_engine.get_latest_analysis_runs(limit=1)
        if not latest_runs:
            message = "Knowledge Graph disponibile, ma non ci sono analysis_run da visualizzare."
            return {
                "figure": self._empty_figure(message),
                "nodes": [],
                "edges": [],
                "message": message,
            }

        run = latest_runs[0]
        lineage = self.query_engine.get_analysis_lineage(run["id"])
        nodes, edges = self._build_lineage_elements(lineage, max_nodes=max_nodes)
        if not nodes:
            message = "Nessun nodo disponibile per la lineage dell'ultima analisi."
            return {
                "figure": self._empty_figure(message),
                "nodes": [],
                "edges": [],
                "message": message,
            }

        message = (
            f"Lineage dell'ultima analisi: {run.get('label', run.get('id'))}. "
            f"Nodi: {len(nodes)}, archi: {len(edges)}."
        )
        return {
            "figure": self._build_figure(nodes, edges, message),
            "nodes": nodes,
            "edges": edges,
            "message": message,
        }

    def build_memory_overview(self) -> dict[str, Any]:
        """Costruisce la vista iniziale della memoria analitica persistente."""
        counts = Counter(node.type for node in self.query_engine.snapshot.nodes)
        total_nodes = sum(counts.values())
        total_edges = len(self.query_engine.snapshot.edges)
        memory_types = [node_type for node_type in MEMORY_LABELS if counts.get(node_type)]

        core = {
            "id": "veraxis:memory",
            "type": "memory_core",
            "label": "VERAXIS\nMEMORY",
            "properties": {
                "nodes": total_nodes,
                "relationships": total_edges,
                "knowledge_areas": len(memory_types),
            },
            "x": 0.0,
            "y": 0.0,
        }
        nodes = [core]
        edges = []
        radius = 2.8
        for index, node_type in enumerate(memory_types):
            angle = (2 * pi * index / max(1, len(memory_types))) + pi / 2
            count = counts[node_type]
            nodes.append({
                "id": f"memory:{node_type}",
                "type": node_type,
                "label": f"{MEMORY_LABELS[node_type]}\n{count}",
                "properties": {"node_type": node_type, "count": count},
                "x": radius * cos(angle),
                "y": radius * sin(angle),
            })
            edges.append({
                "source": core["id"],
                "target": f"memory:{node_type}",
                "relationship": "CONTAINS_MEMORY",
            })

        if not memory_types:
            message = "Memoria Veraxis pronta: nessuna conoscenza persistente disponibile."
        else:
            message = (
                f"Memoria Veraxis attiva · {total_nodes} nodi · "
                f"{total_edges} relazioni · {len(memory_types)} aree di conoscenza."
            )
        return {
            "figure": self._build_memory_figure(nodes, edges, message),
            "nodes": nodes,
            "edges": edges,
            "message": message,
        }

    def build_pipeline_memory(self, processing_status: dict[str, Any] | None = None) -> dict[str, Any]:
        """Visualizza la memoria storica mentre la pipeline analitica si attiva."""
        status = processing_status or {}
        current_agent = str(status.get("current_agent") or "")
        run_status = str(status.get("status") or "processing")
        progress = int(status.get("progress") or 0)
        current_index = PIPELINE_AGENTS.index(current_agent) if current_agent in PIPELINE_AGENTS else -1

        nodes = [{
            "id": "veraxis:active-memory",
            "type": "memory_core",
            "label": f"VERAXIS\n{progress}%",
            "properties": {"status": run_status, "progress": progress},
            "x": 0.0,
            "y": 0.0,
        }]
        edges = []
        radius = 3.4
        for index, agent in enumerate(PIPELINE_AGENTS):
            angle = pi / 2 - (2 * pi * index / len(PIPELINE_AGENTS))
            if run_status == "error" and agent == current_agent:
                agent_status = "error"
            elif run_status == "completed" or (current_index >= 0 and index < current_index):
                agent_status = "completed"
            elif agent == current_agent:
                agent_status = "active"
            else:
                agent_status = "pending"
            nodes.append({
                "id": f"pipeline:{agent}",
                "type": "pipeline_agent",
                "label": agent,
                "properties": {"status": agent_status, "order": index + 1},
                "status": agent_status,
                "x": radius * cos(angle),
                "y": radius * sin(angle),
            })
            edges.append({
                "source": nodes[0]["id"],
                "target": f"pipeline:{agent}",
                "relationship": "ACTIVATES",
            })

        message = f"Memoria analitica in esecuzione · {current_agent or 'avvio'} · {progress}%."
        if run_status == "error":
            message = f"Elaborazione interrotta durante {current_agent or 'la pipeline'}."
        return {
            "figure": self._build_memory_figure(nodes, edges, message, pipeline=True),
            "nodes": nodes,
            "edges": edges,
            "message": message,
        }

    def _build_lineage_elements(
        self,
        lineage: dict[str, Any],
        max_nodes: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        run = lineage.get("analysis_run")
        if not run:
            return [], []

        ordered_nodes = [self._node_payload(run)]
        edge_candidates: list[dict[str, Any]] = []
        run_id = run["id"]

        for bucket, relationship in LINEAGE_BUCKETS:
            for item in lineage.get(bucket, []) or []:
                ordered_nodes.append(self._node_payload(item))
                edge_candidates.append({
                    "source": run_id,
                    "target": item.get("id"),
                    "relationship": relationship,
                })

        nodes = ordered_nodes[: max(1, max_nodes)]
        node_ids = {node["id"] for node in nodes}
        edges = [
            edge for edge in edge_candidates
            if edge["source"] in node_ids and edge["target"] in node_ids
        ]
        positioned_nodes = self._assign_positions(nodes)
        return positioned_nodes, edges

    def _assign_positions(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_type: dict[str, list[dict[str, Any]]] = {}
        for node in nodes:
            by_type.setdefault(node["type"], []).append(node)

        positioned = []
        for node_type, group in by_type.items():
            level = NODE_LEVELS.get(node_type, 7)
            count = len(group)
            for index, node in enumerate(group):
                y = 0 if count == 1 else (count - 1) / 2 - index
                positioned.append({
                    **node,
                    "x": float(level),
                    "y": float(y),
                })
        positioned.sort(key=lambda item: (item["x"], -item["y"], item["label"]))
        return positioned

    def _build_figure(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        title: str,
    ) -> go.Figure:
        node_by_id = {node["id"]: node for node in nodes}
        edge_x: list[float | None] = []
        edge_y: list[float | None] = []
        for edge in edges:
            source = node_by_id.get(edge["source"])
            target = node_by_id.get(edge["target"])
            if not source or not target:
                continue
            edge_x.extend([source["x"], target["x"], None])
            edge_y.extend([source["y"], target["y"], None])

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"width": 1.2, "color": "rgba(180, 190, 205, 0.42)"},
            hoverinfo="skip",
            showlegend=False,
        )
        node_trace = go.Scatter(
            x=[node["x"] for node in nodes],
            y=[node["y"] for node in nodes],
            mode="markers+text",
            marker={
                "size": [self._node_size(node["type"]) for node in nodes],
                "color": [NODE_COLORS.get(node["type"], "#CCCCCC") for node in nodes],
                "line": {"width": 1.6, "color": "rgba(255,255,255,0.72)"},
            },
            text=[self._short_label(node["label"]) for node in nodes],
            textposition="top center",
            textfont={"size": 11, "color": "#F8F9FA"},
            customdata=nodes,
            hovertext=[
                f"<b>{node['label']}</b><br>type={node['type']}<br>id={node['id']}"
                for node in nodes
            ],
            hovertemplate="%{hovertext}<extra></extra>",
            showlegend=False,
        )
        figure = go.Figure(data=[edge_trace, node_trace])
        figure.update_layout(
            template="plotly_dark",
            title={"text": title, "x": 0.02, "xanchor": "left"},
            height=520,
            margin={"l": 20, "r": 20, "t": 70, "b": 20},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis={"visible": False},
            yaxis={"visible": False},
            clickmode="event+select",
        )
        return figure

    def _build_memory_figure(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        title: str,
        pipeline: bool = False,
    ) -> go.Figure:
        """Renderizza una mappa radiale con estetica olografica originale."""
        node_by_id = {node["id"]: node for node in nodes}
        edge_x, edge_y = [], []
        for edge in edges:
            source = node_by_id[edge["source"]]
            target = node_by_id[edge["target"]]
            edge_x.extend([source["x"], target["x"], None])
            edge_y.extend([source["y"], target["y"], None])

        colors = []
        sizes = []
        for node in nodes:
            if node["type"] == "memory_core":
                colors.append("#77E8FF")
                sizes.append(48)
            elif pipeline:
                colors.append({
                    "completed": "#53E6A4",
                    "active": "#67D7FF",
                    "error": "#FF5C7A",
                    "pending": "#33485F",
                }.get(node.get("status"), "#33485F"))
                sizes.append(24 if node.get("status") == "active" else 18)
            else:
                colors.append(NODE_COLORS.get(node["type"], "#7A8EA5"))
                count = int(node.get("properties", {}).get("count", 1))
                sizes.append(min(38, 17 + count ** 0.35))

        figure = go.Figure(data=[
            go.Scatter(
                x=edge_x, y=edge_y, mode="lines", hoverinfo="skip", showlegend=False,
                line={"width": 1.3, "color": "rgba(71, 211, 255, 0.28)"},
            ),
            go.Scatter(
                x=[node["x"] for node in nodes],
                y=[node["y"] for node in nodes],
                mode="markers+text",
                marker={
                    "size": sizes,
                    "color": colors,
                    "line": {"width": 2, "color": "rgba(177, 240, 255, 0.82)"},
                },
                text=[node["label"] for node in nodes],
                textposition="top center",
                textfont={"size": 11, "color": "#DDF8FF"},
                customdata=nodes,
                hovertext=[
                    f"<b>{node['label']}</b><br>{node.get('type', '')}"
                    for node in nodes
                ],
                hovertemplate="%{hovertext}<extra></extra>",
                showlegend=False,
            ),
        ])
        figure.update_layout(
            template="plotly_dark",
            title={"text": title, "x": 0.02, "xanchor": "left"},
            height=580,
            margin={"l": 20, "r": 20, "t": 70, "b": 20},
            plot_bgcolor="#06111F",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis={"visible": False, "range": [-4.4, 4.4]},
            yaxis={"visible": False, "range": [-4.4, 4.4], "scaleanchor": "x"},
            clickmode="event+select",
            hovermode="closest",
        )
        return figure

    def _empty_figure(self, message: str) -> go.Figure:
        return build_empty_knowledge_graph_figure(message)

    def _node_payload(self, node: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(node.get("id", "")),
            "type": str(node.get("type", "")),
            "label": str(node.get("label") or node.get("id", "")),
            "properties": dict(node.get("properties") or {}),
        }

    def _short_label(self, value: str, limit: int = 22) -> str:
        return value if len(value) <= limit else value[: limit - 3] + "..."

    def _node_size(self, node_type: str) -> int:
        return 24 if node_type == "analysis_run" else 18


def format_node_details_payload(node: dict[str, Any] | None, max_properties: int = 10) -> dict[str, Any]:
    """Prepara dettagli compatti per il pannello nodo della dashboard."""
    if not isinstance(node, dict):
        return {
            "label": "Nessun nodo selezionato",
            "type": "",
            "id": "",
            "properties": [],
        }
    properties = node.get("properties") if isinstance(node.get("properties"), dict) else {}
    compact_properties = []
    for key, value in list(properties.items())[:max_properties]:
        rendered = _render_property_value(value)
        compact_properties.append({"key": str(key), "value": rendered})
    return {
        "label": str(node.get("label") or ""),
        "type": str(node.get("type") or ""),
        "id": str(node.get("id") or ""),
        "properties": compact_properties,
    }


def build_empty_knowledge_graph_figure(message: str) -> go.Figure:
    """Crea una figura vuota con messaggio leggibile."""
    figure = go.Figure()
    figure.update_layout(
        template="plotly_dark",
        height=360,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{
            "text": message,
            "xref": "paper",
            "yref": "paper",
            "x": 0.5,
            "y": 0.5,
            "showarrow": False,
            "font": {"size": 14, "color": "#D8DEE9"},
        }],
    )
    return figure


def _render_property_value(value: Any) -> str:
    if isinstance(value, dict):
        rendered = f"dict({len(value)})"
    elif isinstance(value, (list, tuple, set)):
        rendered = ", ".join(str(item) for item in list(value)[:5])
        if len(value) > 5:
            rendered += f" (+{len(value) - 5})"
    else:
        rendered = str(value)
    return rendered if len(rendered) <= 140 else rendered[:137] + "..."
