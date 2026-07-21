"""Durable RQ job entrypoint for Coordinator analyses."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

from coordinator import Coordinator
from services.platform.auth import Identity
from services.platform.persistence import PlatformRepository


def execute_analysis_job(
    identity_payload: dict[str, str],
    job_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    repository = PlatformRepository()
    identity = Identity(**identity_payload)
    if repository.is_cancel_requested(identity.tenant_id, job_id):
        repository.update_analysis(identity.tenant_id, job_id, status="cancelled")
        return {"status": "cancelled"}
    repository.update_progress(identity.tenant_id, job_id, 5)
    try:
        frame = pd.DataFrame(body["records"])
        tenant_root = Path(os.getenv("TENANT_DATA_ROOT", "data/tenants")) / identity.tenant_id

        def progress(agent_name: str, value: int):
            if repository.is_cancel_requested(identity.tenant_id, job_id):
                raise AnalysisCancelled("Analysis cancelled by user")
            repository.update_progress(identity.tenant_id, job_id, max(5, value))

        context = Coordinator().run(
            str(body["description"]),
            metadata={
                "source_type": str(body.get("source_type") or "csv"),
                "file_path": str(body.get("dataset_name") or "api-records"),
                "dataframe": frame,
                "tenant_id": identity.tenant_id,
                "created_by": identity.user_id,
                "knowledge_graph_path": str(tenant_root / "knowledge_graph.json"),
                "experience_path": str(tenant_root / "experience.json"),
                "query_history_path": str(tenant_root / "query_history.db"),
                "analysis_history_path": str(tenant_root / "analysis_history.db"),
                "enable_narrative": bool(body.get("enable_narrative", False)),
            },
            progress_callback=progress,
        )
        repository.update_analysis(
            identity.tenant_id,
            job_id,
            status="completed",
            result=serialize_context(context),
        )
        repository.update_progress(identity.tenant_id, job_id, 100, "completed")
        return {"status": "completed", "analysis_id": job_id}
    except AnalysisCancelled:
        repository.update_analysis(identity.tenant_id, job_id, status="cancelled")
        return {"status": "cancelled"}
    except Exception as exc:
        repository.update_analysis(identity.tenant_id, job_id, status="failed", error=str(exc))
        raise


def serialize_context(context) -> dict[str, Any]:
    return {
        "is_valid": bool(context.is_valid),
        "errors": list(context.errors),
        "validation_results": context.validation_results,
        "insights": context.insights,
        "anomaly_detection_results": context.anomaly_detection_results,
        "root_cause_results": context.root_cause_results,
        "recommended_analytical_steps": context.recommended_analytical_steps,
        "product_intelligence": context.product_intelligence,
        "final_report": context.final_report,
        "created_at": context.created_at.isoformat(),
    }


class AnalysisCancelled(RuntimeError):
    pass
