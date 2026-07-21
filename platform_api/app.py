"""Tenant-isolated REST API and asynchronous analysis jobs."""

from __future__ import annotations

import os
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any
from pathlib import Path

import pandas as pd
from flask import Flask, Response, g, jsonify, redirect, render_template, request, session, url_for

from coordinator import Coordinator
from services.platform.auth import AuthService, Identity
from services.platform.persistence import PlatformRepository
from platform_api.jobs import execute_analysis_job, serialize_context
from platform_api.knowledge import answer_workspace_question, build_workspace_payload, tenant_paths
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_app(
    repository: PlatformRepository | None = None,
    auth_service: AuthService | None = None,
    coordinator_factory=Coordinator,
    job_queue=None,
) -> Flask:
    # Keep portal assets under /portal so the production gateway routes them
    # to this service instead of the Dash application mounted at `/`.
    app = Flask(__name__, static_url_path="/portal/static")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("API_MAX_REQUEST_BYTES", str(10 * 1024 * 1024)))
    repo = repository or PlatformRepository()
    auth = auth_service or AuthService()
    app.secret_key = auth.secret
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_env_bool(
            "SESSION_COOKIE_SECURE",
            os.getenv("PLATFORM_ENV", "development").lower() == "production",
        ),
    )
    executor = ThreadPoolExecutor(max_workers=max(1, int(os.getenv("ANALYSIS_WORKERS", "2"))))
    counters = {"submitted": 0, "completed": 0, "failed": 0}
    counter_lock = threading.Lock()
    redis_url = os.getenv("REDIS_URL", "").strip()
    if job_queue is None and redis_url:
        from redis import Redis
        from rq import Queue
        job_queue = Queue("analyses", connection=Redis.from_url(redis_url), default_timeout=1800)

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

    def portal_identity() -> Identity | None:
        token = session.get("access_token")
        if not token:
            return None
        try:
            return auth.verify_token(token)
        except ValueError:
            session.clear()
            return None

    def csrf_token() -> str:
        return session.setdefault("csrf_token", secrets.token_urlsafe(24))

    def valid_csrf() -> bool:
        body = request.get_json(silent=True) if request.is_json else {}
        supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or (body or {}).get("csrf_token")
        return secrets.compare_digest(str(session.get("csrf_token") or ""), str(supplied or ""))

    def workspace_paths(identity: Identity):
        return tenant_paths(os.getenv("TENANT_DATA_ROOT", "data/tenants"), identity.tenant_id)

    def latest_product_intelligence(identity: Identity) -> dict[str, Any]:
        for item in repo.list_analyses(identity.tenant_id, 20):
            if item.get("status") != "completed":
                continue
            detail = repo.get_analysis(identity.tenant_id, item["id"])
            intelligence = ((detail or {}).get("result") or {}).get("product_intelligence")
            if isinstance(intelligence, dict) and intelligence:
                return {"analysis_id": item["id"], "updated_at": item.get("updated_at"), **intelligence}
        return {}

    def workspace_payload(identity: Identity):
        paths = workspace_paths(identity)
        return build_workspace_payload(
            paths["graph"], paths["experience"], repo.list_analyses(identity.tenant_id, 50),
            node_type=request.args.get("type", ""), search=request.args.get("q", ""),
            limit=request.args.get("limit", 250),
            latest_intelligence=latest_product_intelligence(identity),
        )

    def enqueue_analysis(identity: Identity, body: dict[str, Any]) -> tuple[str, str]:
        job_id = repo.create_analysis(identity.tenant_id, identity.user_id, body)
        with counter_lock:
            counters["submitted"] += 1
        if job_queue is not None:
            from rq import Retry
            job_queue.enqueue(
                execute_analysis_job,
                asdict(identity),
                job_id,
                body,
                job_id=job_id,
                description=f"analysis:{job_id}",
                retry=Retry(max=2, interval=[10, 30]),
                result_ttl=86400,
                failure_ttl=604800,
            )
            return job_id, "redis_rq"
        executor.submit(run_analysis, identity, job_id, body)
        return job_id, "local_fallback"

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
        job_id, queue_backend = enqueue_analysis(identity, body)
        return jsonify({"id": job_id, "status": "queued", "queue": queue_backend}), 202

    @app.get("/portal")
    def portal():
        identity = portal_identity()
        analyses = repo.list_analyses(identity.tenant_id, 50) if identity else []
        return render_template(
            "portal.html",
            identity=identity,
            analyses=analyses,
            csrf_token=csrf_token(),
            message=session.pop("message", ""),
            self_registration=os.getenv("ALLOW_SELF_REGISTRATION", "true").lower() in {"1", "true", "yes"},
        )

    @app.get("/portal/knowledge")
    def portal_knowledge():
        identity = portal_identity()
        if identity is None:
            session["message"] = "Login required to open Knowledge Intelligence."
            return redirect(url_for("portal"))
        return render_template("knowledge_workspace.html", identity=identity, csrf_token=csrf_token())

    @app.get("/portal/api/knowledge")
    def portal_knowledge_data():
        identity = portal_identity()
        if identity is None:
            return error("Authentication required", 401)
        return jsonify(workspace_payload(identity))

    @app.post("/portal/api/knowledge/query")
    def portal_knowledge_query():
        identity = portal_identity()
        if identity is None:
            return error("Authentication required", 401)
        if not valid_csrf():
            return error("Invalid CSRF token", 400)
        question = str((request.get_json(silent=True) or {}).get("question") or "").strip()
        if not question:
            return error("question is required", 400)
        return jsonify(answer_workspace_question(workspace_paths(identity)["graph"], question))

    @app.get("/portal/api/knowledge/nodes/<path:node_id>")
    def portal_knowledge_node(node_id: str):
        identity = portal_identity()
        if identity is None:
            return error("Authentication required", 401)
        engine = KnowledgeGraphQueryEngine(path=workspace_paths(identity)["graph"])
        node = next((item for item in engine.find_nodes(limit=1000) if item["id"] == node_id), None)
        if node is None:
            return error("Knowledge node not found", 404)
        return jsonify({"node": node, "neighbors": engine.get_neighbors(node_id, limit=100)})

    @app.get("/portal/api/knowledge/export")
    def portal_knowledge_export():
        identity = portal_identity()
        if identity is None:
            return error("Authentication required", 401)
        return Response(
            __import__("json").dumps(workspace_payload(identity), ensure_ascii=False, indent=2, default=str),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=knowledge-intelligence.json"},
        )

    @app.post("/portal/register")
    def portal_register():
        if not valid_csrf():
            return "Invalid CSRF token", 400
        if os.getenv("ALLOW_SELF_REGISTRATION", "true").lower() not in {"1", "true", "yes"}:
            return "Self registration disabled", 403
        try:
            organization = request.form.get("organization", "").strip()
            email = request.form.get("email", "").strip().lower()
            if not organization or "@" not in email:
                raise ValueError("Organization and valid email are required")
            created = repo.create_tenant_with_admin(
                organization,
                email,
                auth.hash_password(request.form.get("password", "")),
            )
            identity = Identity(created["user_id"], created["tenant_id"], email, "admin")
            session["access_token"] = auth.issue_token(identity)
            session["message"] = "Organization registered successfully."
        except Exception as exc:
            session["message"] = str(exc)
        return redirect(url_for("portal"))

    @app.post("/portal/analyses/<analysis_id>/cancel")
    def portal_cancel_analysis(analysis_id: str):
        identity = portal_identity()
        if identity is None:
            return redirect(url_for("portal"))
        if identity.role not in {"admin", "analyst"}:
            return "Insufficient role", 403
        if not valid_csrf():
            return "Invalid CSRF token", 400
        if not repo.request_cancel(identity.tenant_id, analysis_id):
            session["message"] = "Analysis not found or no longer cancellable."
            return redirect(url_for("portal"))
        if job_queue is not None:
            try:
                job = job_queue.fetch_job(analysis_id)
                if job is not None:
                    job.cancel()
                    repo.update_analysis(identity.tenant_id, analysis_id, status="cancelled")
            except Exception:
                pass
        session["message"] = f"Cancellation requested for analysis {analysis_id[:8]}."
        return redirect(url_for("portal"))

    @app.post("/portal/login")
    def portal_login():
        if not valid_csrf():
            return "Invalid CSRF token", 400
        user = repo.get_user_by_email(request.form.get("tenant_id", ""), request.form.get("email", ""))
        if not user or not auth.verify_password(request.form.get("password", ""), user["password_hash"]):
            session["message"] = "Invalid credentials."
        else:
            identity = Identity(user["id"], user["tenant_id"], user["email"], user["role"])
            session["access_token"] = auth.issue_token(identity)
            session["message"] = "Login completed."
        return redirect(url_for("portal"))

    @app.post("/portal/logout")
    def portal_logout():
        if not valid_csrf():
            return "Invalid CSRF token", 400
        session.clear()
        return redirect(url_for("portal"))

    @app.post("/portal/analyses")
    def portal_submit_analysis():
        identity = portal_identity()
        if identity is None:
            return redirect(url_for("portal"))
        if identity.role not in {"admin", "analyst"}:
            return "Insufficient role", 403
        if not valid_csrf():
            return "Invalid CSRF token", 400
        uploaded = request.files.get("dataset")
        description = request.form.get("description", "").strip()
        if not uploaded or not description:
            session["message"] = "Description and dataset are required."
            return redirect(url_for("portal"))
        filename = uploaded.filename or "dataset"
        try:
            if filename.lower().endswith(".csv"):
                frame = pd.read_csv(uploaded.stream)
                source_type = "csv"
            elif filename.lower().endswith((".xlsx", ".xls")):
                frame = pd.read_excel(uploaded.stream)
                source_type = "excel"
            else:
                raise ValueError("Only CSV and Excel files are supported")
            max_records = max(1, int(os.getenv("API_MAX_RECORDS", "100000")))
            if len(frame) > max_records:
                raise ValueError(f"Dataset exceeds configured limit {max_records}")
            job_id, backend = enqueue_analysis(identity, {
                "description": description,
                "records": frame.where(pd.notna(frame), None).to_dict(orient="records"),
                "source_type": source_type,
                "dataset_name": filename,
                "enable_narrative": request.form.get("enable_narrative") == "on",
            })
            session["message"] = f"Analysis {job_id[:8]} queued through {backend}."
        except Exception as exc:
            session["message"] = str(exc)
        return redirect(url_for("portal"))

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
                identity.tenant_id, job_id, status="completed", result=serialize_context(context)
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

    @app.get("/api/v1/knowledge")
    def get_knowledge_workspace():
        identity, failure = require_identity()
        if failure:
            return failure
        return jsonify(workspace_payload(identity))

    @app.post("/api/v1/knowledge/query")
    def query_knowledge_workspace():
        identity, failure = require_identity()
        if failure:
            return failure
        question = str((request.get_json(silent=True) or {}).get("question") or "").strip()
        if not question:
            return error("question is required", 400)
        return jsonify(answer_workspace_question(workspace_paths(identity)["graph"], question))

    @app.post("/api/v1/analyses/<analysis_id>/cancel")
    def cancel_analysis(analysis_id: str):
        identity, failure = require_identity({"admin", "analyst"})
        if failure:
            return failure
        if not repo.request_cancel(identity.tenant_id, analysis_id):
            return error("Analysis not found or no longer cancellable", 409)
        if job_queue is not None:
            try:
                job = job_queue.fetch_job(analysis_id)
                if job is not None:
                    job.cancel()
                    repo.update_analysis(identity.tenant_id, analysis_id, status="cancelled")
            except Exception:
                pass
        return jsonify({"id": analysis_id, "status": "cancelling"}), 202

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
                "/api/v1/analyses/{analysis_id}/cancel": {"post": {"summary": "Cancel analysis"}},
                "/api/v1/knowledge": {"get": {"summary": "Get tenant Knowledge Intelligence workspace"}},
                "/api/v1/knowledge/query": {"post": {"summary": "Query the tenant Knowledge Graph"}},
            },
        })

    app.extensions["platform_repository"] = repo
    app.extensions["platform_executor"] = executor
    return app


app = create_app()
