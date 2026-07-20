"""Tenant-isolated REST API and asynchronous analysis jobs."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any
from pathlib import Path

import pandas as pd
from flask import Flask, g, jsonify, request

from coordinator import Coordinator
from services.platform.auth import AuthService, Identity
from services.platform.persistence import PlatformRepository


def create_app(
    repository: PlatformRepository | None = None,
    auth_service: AuthService | None = None,
    coordinator_factory=Coordinator,
) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("API_MAX_REQUEST_BYTES", str(10 * 1024 * 1024)))
    repo = repository or PlatformRepository()
    auth = auth_service or AuthService()
    executor = ThreadPoolExecutor(max_workers=max(1, int(os.getenv("ANALYSIS_WORKERS", "2"))))
    counters = {"submitted": 0, "completed": 0, "failed": 0}
    counter_lock = threading.Lock()

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store" if request.path.startswith("/api/") else "no-cache"
        return response

    def error(message: str, status: int):
        return jsonify({"error": message, "status": status}), status

    def authenticate() -> Identity | None:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        try:
            return auth.verify_token(header.removeprefix("Bearer ").strip())
        except ValueError:
            return None

    def require_identity(roles: set[str] | None = None):
        identity = authenticate()
        if identity is None:
            return None, error("Authentication required", 401)
        if roles and identity.role not in roles:
            return None, error("Insufficient role", 403)
        g.identity = identity
        return identity, None

    @app.post("/api/v1/auth/register")
    def register():
        if os.getenv("ALLOW_SELF_REGISTRATION", "true").lower() not in {"1", "true", "yes"}:
            return error("Self registration disabled", 403)
        body = request.get_json(silent=True) or {}
        if not str(body.get("organization") or "").strip() or "@" not in str(body.get("email") or ""):
            return error("organization and valid email are required", 400)
        try:
            password_hash = auth.hash_password(str(body.get("password") or ""))
            created = repo.create_tenant_with_admin(
                str(body.get("organization") or "").strip(),
                str(body.get("email") or "").strip(),
                password_hash,
            )
        except Exception as exc:
            return error(str(exc), 400)
        identity = Identity(
            created["user_id"], created["tenant_id"],
            str(body["email"]).strip().lower(), created["role"],
        )
        return jsonify({"access_token": auth.issue_token(identity), "identity": asdict(identity)}), 201

    @app.post("/api/v1/auth/login")
    def login():
        body = request.get_json(silent=True) or {}
        user = repo.get_user_by_email(str(body.get("tenant_id") or ""), str(body.get("email") or ""))
        if not user or not auth.verify_password(str(body.get("password") or ""), user["password_hash"]):
            return error("Invalid credentials", 401)
        identity = Identity(user["id"], user["tenant_id"], user["email"], user["role"])
        return jsonify({"access_token": auth.issue_token(identity), "identity": asdict(identity)})

    @app.post("/api/v1/users")
    def create_user():
        identity, failure = require_identity({"admin"})
        if failure:
            return failure
        body = request.get_json(silent=True) or {}
        try:
            user_id = repo.create_user(
                identity.tenant_id,
                str(body.get("email") or ""),
                auth.hash_password(str(body.get("password") or "")),
                str(body.get("role") or "viewer"),
            )
        except Exception as exc:
            return error(str(exc), 400)
        return jsonify({"id": user_id, "tenant_id": identity.tenant_id}), 201

    @app.post("/api/v1/analyses")
    def submit_analysis():
        identity, failure = require_identity({"admin", "analyst"})
        if failure:
            return failure
        body = request.get_json(silent=True) or {}
        description = str(body.get("description") or "").strip()
        records = body.get("records")
        if not description or not isinstance(records, list) or not records:
            return error("description and non-empty records are required", 400)
        max_records = max(1, int(os.getenv("API_MAX_RECORDS", "100000")))
        if len(records) > max_records:
            return error(f"records exceeds configured limit {max_records}", 413)
        job_id = repo.create_analysis(identity.tenant_id, identity.user_id, body)
        with counter_lock:
            counters["submitted"] += 1
        executor.submit(run_analysis, identity, job_id, body)
        return jsonify({"id": job_id, "status": "queued"}), 202

    def run_analysis(identity: Identity, job_id: str, body: dict[str, Any]):
        repo.update_analysis(identity.tenant_id, job_id, status="processing")
        try:
            frame = pd.DataFrame(body["records"])
            tenant_root = Path(os.getenv("TENANT_DATA_ROOT", "data/tenants")) / identity.tenant_id
            context = coordinator_factory().run(
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
            )
            repo.update_analysis(
                identity.tenant_id, job_id, status="completed", result=_serialize_context(context)
            )
            with counter_lock:
                counters["completed"] += 1
        except Exception as exc:
            repo.update_analysis(identity.tenant_id, job_id, status="failed", error=str(exc))
            with counter_lock:
                counters["failed"] += 1

    @app.get("/api/v1/analyses")
    def list_analyses():
        identity, failure = require_identity()
        if failure:
            return failure
        return jsonify({"items": repo.list_analyses(identity.tenant_id, request.args.get("limit", 50))})

    @app.get("/api/v1/analyses/<analysis_id>")
    def get_analysis(analysis_id: str):
        identity, failure = require_identity()
        if failure:
            return failure
        item = repo.get_analysis(identity.tenant_id, analysis_id)
        return jsonify(item) if item else error("Analysis not found", 404)

    @app.get("/health/live")
    def live():
        return jsonify({"status": "alive"})

    @app.get("/health/ready")
    def ready():
        try:
            return jsonify(repo.readiness())
        except Exception as exc:
            return error(str(exc), 503)

    @app.get("/metrics")
    def metrics():
        lines = [f"skills_agent_analyses_{name}_total {value}" for name, value in counters.items()]
        return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

    @app.get("/api/v1/openapi.json")
    def openapi():
        return jsonify({
            "openapi": "3.0.3",
            "info": {"title": "Skills Agent API", "version": "1.0.0"},
            "paths": {
                "/api/v1/auth/register": {"post": {"summary": "Create tenant and admin"}},
                "/api/v1/auth/login": {"post": {"summary": "Issue access token"}},
                "/api/v1/users": {"post": {"summary": "Create tenant user"}},
                "/api/v1/analyses": {
                    "post": {"summary": "Submit analysis job"},
                    "get": {"summary": "List tenant analyses"},
                },
                "/api/v1/analyses/{analysis_id}": {"get": {"summary": "Get tenant analysis"}},
            },
        })

    app.extensions["platform_repository"] = repo
    app.extensions["platform_executor"] = executor
    return app


def _serialize_context(context) -> dict[str, Any]:
    """Expose analytical results without persisting uploaded raw rows."""
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


app = create_app()
