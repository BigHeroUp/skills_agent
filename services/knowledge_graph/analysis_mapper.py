"""Mapping difensivo da AgentContext a Knowledge Graph."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from services.knowledge_graph.models import KnowledgeEdge, KnowledgeGraphSnapshot, KnowledgeNode
from utils.context import AgentContext


def map_analysis_context(context: AgentContext) -> KnowledgeGraphSnapshot:
    """Crea nodi e relazioni sintetiche per l'analisi corrente."""
    nodes: list[KnowledgeNode] = []
    edges: list[KnowledgeEdge] = []

    run_id = _analysis_run_id(context)
    created_at = getattr(context, "created_at", None)
    dataframe = (getattr(context, "raw_data", {}) or {}).get("dataframe")
    shape = getattr(dataframe, "shape", None)
    analysis_node = KnowledgeNode(
        id=run_id,
        type="analysis_run",
        label=_truncate(getattr(context, "user_input", "") or "Analisi", 120),
        properties={
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
            "user_input": _truncate(getattr(context, "user_input", "") or "", 500),
            "source_type": _safe_metadata(context).get("source_type"),
            "row_count": int(shape[0]) if shape else None,
            "column_count": int(shape[1]) if shape else None,
            "primary_metric": getattr(context, "primary_metric", None),
            "time_axis": getattr(context, "time_axis", None),
            "confidence_score": getattr(context, "confidence_score", 0.0),
            "plan_source": getattr(context, "plan_source", None),
            "autonomous_mode": bool(getattr(context, "autonomous_mode", False)),
            "is_valid": bool(getattr(context, "is_valid", True)),
            "error_count": len(getattr(context, "errors", []) or []),
        },
    )
    nodes.append(analysis_node)

    dataset_id = _map_dataset(context, run_id, nodes, edges)
    _map_insights(context, run_id, nodes, edges)
    _map_anomalies(context, run_id, dataset_id, nodes, edges)
    _map_root_causes(context, run_id, nodes, edges)
    _map_report(context, run_id, nodes, edges)
    _map_domain_pack(context, run_id, nodes, edges)

    return KnowledgeGraphSnapshot(nodes=nodes, edges=edges)


def _map_dataset(
    context: AgentContext,
    run_id: str,
    nodes: list[KnowledgeNode],
    edges: list[KnowledgeEdge],
) -> str | None:
    dataframe = (getattr(context, "raw_data", {}) or {}).get("dataframe")
    metadata = _safe_metadata(context)
    dataset_id = f"dataset:{run_id}"
    shape = getattr(dataframe, "shape", None)
    columns = [str(column) for column in getattr(dataframe, "columns", [])]
    dtypes = {
        str(column): str(dtype)
        for column, dtype in getattr(dataframe, "dtypes", {}).items()
    } if hasattr(getattr(dataframe, "dtypes", None), "items") else {}

    nodes.append(KnowledgeNode(
        id=dataset_id,
        type="dataset",
        label=str(metadata.get("filename") or metadata.get("source_type") or "dataset"),
        properties={
            "source_type": metadata.get("source_type"),
            "row_count": int(shape[0]) if shape else None,
            "column_count": int(shape[1]) if shape else len(columns) or None,
            "columns": columns,
        },
    ))
    edges.append(KnowledgeEdge(run_id, dataset_id, "ANALYZED_DATASET"))
    edges.append(KnowledgeEdge(run_id, dataset_id, "USES_DATASET"))

    for column in columns:
        column_id = f"dataframe_column:{run_id}:{_stable_slug(column)}"
        nodes.append(KnowledgeNode(
            id=column_id,
            type="dataframe_column",
            label=column,
            properties=_column_properties(context, dataframe, column, dtypes.get(column)),
        ))
        edges.append(KnowledgeEdge(run_id, column_id, "HAS_COLUMN"))
        edges.append(KnowledgeEdge(dataset_id, column_id, "HAS_COLUMN"))
    return dataset_id


def _map_insights(
    context: AgentContext,
    run_id: str,
    nodes: list[KnowledgeNode],
    edges: list[KnowledgeEdge],
) -> None:
    insights = getattr(context, "insights", {}) or {}
    if not isinstance(insights, dict):
        return
    for index, (key, value) in enumerate(insights.items()):
        if key in {"processed_data", "local_analysis"}:
            continue
        summary = _summarize_value(value)
        if summary is None:
            continue
        insight_id = f"insight:{run_id}:{_stable_slug(key)}:{index}"
        nodes.append(KnowledgeNode(
            id=insight_id,
            type="insight",
            label=str(key),
            properties={"summary": summary},
        ))
        edges.append(KnowledgeEdge(run_id, insight_id, "PRODUCED_INSIGHT"))
        edges.append(KnowledgeEdge(run_id, insight_id, "GENERATED_INSIGHT"))


def _map_anomalies(
    context: AgentContext,
    run_id: str,
    dataset_id: str | None,
    nodes: list[KnowledgeNode],
    edges: list[KnowledgeEdge],
) -> None:
    anomaly_results = getattr(context, "anomaly_detection_results", {}) or {}
    anomalies = anomaly_results.get("anomalies", []) if isinstance(anomaly_results, dict) else []
    for index, anomaly in enumerate(anomalies or []):
        if not isinstance(anomaly, dict):
            continue
        anomaly_id = f"anomaly:{anomaly.get('anomaly_id') or _stable_hash(anomaly)}"
        nodes.append(KnowledgeNode(
            id=anomaly_id,
            type="anomaly",
            label=str(anomaly.get("anomaly_type") or anomaly.get("type") or f"anomaly_{index + 1}"),
            properties=_pick(anomaly, [
                "anomaly_type",
                "severity",
                "confidence_score",
                "affected_column",
                "affected_period",
                "method",
            ]),
        ))
        edges.append(KnowledgeEdge(run_id, anomaly_id, "DETECTED_ANOMALY"))
        if dataset_id:
            edges.append(KnowledgeEdge(anomaly_id, dataset_id, "OBSERVED_IN_DATASET"))


def _map_root_causes(
    context: AgentContext,
    run_id: str,
    nodes: list[KnowledgeNode],
    edges: list[KnowledgeEdge],
) -> None:
    root_cause_results = getattr(context, "root_cause_results", {}) or {}
    causes = root_cause_results.get("possible_causes", []) if isinstance(root_cause_results, dict) else []
    for index, cause in enumerate(causes or []):
        if not isinstance(cause, dict):
            continue
        cause_id = f"root_cause:{cause.get('cause_id') or _stable_hash(cause)}"
        nodes.append(KnowledgeNode(
            id=cause_id,
            type="root_cause",
            label=str(cause.get("title") or f"root_cause_{index + 1}"),
            properties={
                **_pick(cause, ["severity", "confidence_score", "method"]),
                "affected_metrics": list(cause.get("affected_metrics") or [])[:10],
            },
        ))
        edges.append(KnowledgeEdge(run_id, cause_id, "IDENTIFIED_ROOT_CAUSE"))
        edges.append(KnowledgeEdge(run_id, cause_id, "PROPOSED_ROOT_CAUSE"))
        for anomaly_id in cause.get("related_anomalies", []) or []:
            edges.append(KnowledgeEdge(cause_id, f"anomaly:{anomaly_id}", "EXPLAINS_ANOMALY"))


def _map_report(
    context: AgentContext,
    run_id: str,
    nodes: list[KnowledgeNode],
    edges: list[KnowledgeEdge],
) -> None:
    report = getattr(context, "final_report", "") or ""
    if not report:
        return
    report_id = f"report:{run_id}"
    nodes.append(KnowledgeNode(
        id=report_id,
        type="report",
        label="final_report",
        properties={
            "length_chars": len(report),
            "line_count": len(report.splitlines()),
            "sha1": _stable_hash(report),
        },
    ))
    edges.append(KnowledgeEdge(run_id, report_id, "GENERATED_REPORT"))


def _map_domain_pack(
    context: AgentContext,
    run_id: str,
    nodes: list[KnowledgeNode],
    edges: list[KnowledgeEdge],
) -> None:
    domain_pack = getattr(context, "domain_pack_context", {}) or {}
    if not isinstance(domain_pack, dict) or not domain_pack.get("pack_id"):
        return
    pack_id = f"domain_pack:{domain_pack.get('pack_id')}"
    nodes.append(KnowledgeNode(
        id=pack_id,
        type="domain_pack",
        label=str(domain_pack.get("pack_id")),
        properties=_pick(domain_pack, ["status", "pack_id"]),
    ))
    edges.append(KnowledgeEdge(run_id, pack_id, "USED_DOMAIN_PACK"))


def _column_properties(
    context: AgentContext,
    dataframe: Any,
    column: str,
    dtype: str | None,
) -> dict[str, Any]:
    semantic_columns = getattr(context, "semantic_columns", {}) or {}
    semantic_role = _semantic_role_for_column(semantic_columns, column)
    properties = {
        "name": column,
        "dtype": dtype,
        "semantic_role": semantic_role,
        "is_primary_metric": column == getattr(context, "primary_metric", None),
        "is_time_axis": column == getattr(context, "time_axis", None),
    }
    if hasattr(dataframe, "columns") and column in dataframe.columns:
        series = dataframe[column]
        row_count = len(series)
        null_count = int(series.isna().sum())
        properties.update({
            "null_count": null_count,
            "null_percentage": round(null_count / row_count * 100, 4) if row_count else 0.0,
            "cardinality": int(series.nunique(dropna=True)),
        })
    return properties


def _semantic_role_for_column(semantic_columns: dict[str, Any], column: str) -> str | None:
    if not isinstance(semantic_columns, dict):
        return None
    direct = semantic_columns.get(column)
    if isinstance(direct, str):
        return direct
    if isinstance(direct, dict):
        return direct.get("semantic_role") or direct.get("role") or direct.get("type")
    for role, values in semantic_columns.items():
        if isinstance(values, list) and column in values:
            return str(role)
        if isinstance(values, dict):
            columns = values.get("columns") or values.get("matches") or []
            if isinstance(columns, list) and column in columns:
                return str(role)
    return None


def _analysis_run_id(context: AgentContext) -> str:
    payload = "|".join([
        str(getattr(context, "created_at", "")),
        str(getattr(context, "user_input", "")),
        str(_safe_metadata(context).get("source_type", "")),
    ])
    return f"analysis_run:{_stable_hash(payload)}"


def _safe_metadata(context: AgentContext) -> dict[str, Any]:
    metadata = getattr(context, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        return {}
    blocked = {"password", "token", "api_key", "secret", "connection_string", "dsn"}
    return {
        str(key): value
        for key, value in metadata.items()
        if str(key).lower() not in blocked and _is_scalar(value)
    }


def _pick(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {
        key: _json_safe(payload.get(key))
        for key in keys
        if key in payload
    }


def _summarize_value(value: Any) -> Any:
    if _is_scalar(value):
        return _truncate(str(value), 500)
    if isinstance(value, list):
        scalar_items = [_truncate(str(item), 240) for item in value if _is_scalar(item)]
        return scalar_items[:5] if scalar_items else {"item_count": len(value)}
    if isinstance(value, dict):
        scalar_items = {
            str(key): _truncate(str(item), 240)
            for key, item in value.items()
            if _is_scalar(item)
        }
        return dict(list(scalar_items.items())[:10]) if scalar_items else {"key_count": len(value)}
    return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if _is_scalar(value):
        return value
    return str(value)


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _stable_slug(value: Any) -> str:
    text = str(value).strip().lower()
    slug = "".join(char if char.isalnum() else "_" for char in text).strip("_")
    return slug[:80] or _stable_hash(value)[:12]


def _stable_hash(value: Any) -> str:
    return hashlib.sha1(str(value).encode("utf-8", errors="replace")).hexdigest()[:16]


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."
