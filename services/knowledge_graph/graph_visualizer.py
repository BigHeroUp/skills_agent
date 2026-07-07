"""Visualizzazione Plotly del Knowledge Graph locale."""

from __future__ import annotations

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
