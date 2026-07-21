import io
import re
import time
from pathlib import Path

import pytest

from platform_api.app import create_app
from platform_api.jobs import ensure_usable_analysis
from services.platform.auth import AuthService
from services.platform.persistence import PlatformRepository
from services.experience.experience_models import AnalyticalExperience
from services.experience.experience_store import ExperienceStore
from services.knowledge_graph.models import KnowledgeEdge, KnowledgeGraphSnapshot, KnowledgeNode
from services.knowledge_graph.store import KnowledgeGraphStore
from utils.context import AgentContext


class FakeCoordinator:
    def run(self, description, metadata):
        return AgentContext(
            user_input=description,
            final_report="Completed report",
            anomaly_detection_results={"anomaly_count": 1},
            product_intelligence={"status": "completed"},
        )


def test_unusable_zero_row_report_is_not_publishable():
    context = AgentContext(
        user_input="Conta i contratti",
        errors=["[DataProcessor] Colonna non disponibile per l'analisi: None"],
        final_report="Report su 0 record",
        dataframe_enriched_metadata={},
    )

    with pytest.raises(RuntimeError, match="analisi è stata interrotta"):
        ensure_usable_analysis(context, input_row_count=100)


def _register(client, organization, email):
    response = client.post("/api/v1/auth/register", json={
        "organization": organization,
        "email": email,
        "password": "very-secure-password",
    })
    assert response.status_code == 201
    return response.get_json()


def test_authenticated_async_analysis_and_tenant_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'api.db'}")
    app = create_app(repository, AuthService("s" * 32), coordinator_factory=FakeCoordinator)
    client = app.test_client()
    first = _register(client, "First", "admin@first.test")
    second = _register(client, "Second", "admin@second.test")

    response = client.post(
        "/api/v1/analyses",
        json={"description": "Analyze revenue", "records": [{"revenue": 10}]},
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )
    assert response.status_code == 202
    analysis_id = response.get_json()["id"]
    for _ in range(50):
        item = repository.get_analysis(first["identity"]["tenant_id"], analysis_id)
        if item["status"] == "completed":
            break
        time.sleep(0.01)

    own = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )
    foreign = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )

    assert own.status_code == 200
    assert own.get_json()["result"]["final_report"] == "Completed report"
    assert foreign.status_code == 404
    assert client.get("/health/ready").status_code == 200
    assert b"skills_agent_analyses_completed_total 1" in client.get("/metrics").data


def test_viewer_cannot_submit_analysis(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'roles.db'}")
    auth = AuthService("s" * 32)
    app = create_app(repository, auth, coordinator_factory=FakeCoordinator)
    client = app.test_client()
    admin = _register(client, "First", "admin@first.test")
    response = client.post(
        "/api/v1/users",
        json={"email": "viewer@first.test", "password": "viewer-password-1", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert response.status_code == 201
    login = client.post("/api/v1/auth/login", json={
        "tenant_id": admin["identity"]["tenant_id"],
        "email": "viewer@first.test",
        "password": "viewer-password-1",
    }).get_json()

    forbidden = client.post(
        "/api/v1/analyses",
        json={"description": "No", "records": [{"x": 1}]},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert forbidden.status_code == 403


def test_api_limits_payload_and_adds_security_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    monkeypatch.setenv("API_MAX_RECORDS", "1")
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'limits.db'}")
    app = create_app(repository, AuthService("s" * 32), coordinator_factory=FakeCoordinator)
    client = app.test_client()
    admin = _register(client, "First", "admin@first.test")

    response = client.post(
        "/api/v1/analyses",
        json={"description": "Too many", "records": [{"x": 1}, {"x": 2}]},
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )

    assert response.status_code == 413
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/api/v1/openapi.json").get_json()["openapi"] == "3.0.3"


def test_portal_register_excel_analysis_and_logout(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'portal.db'}")
    app = create_app(repository, AuthService("p" * 32), coordinator_factory=FakeCoordinator)
    client = app.test_client()

    page = client.get("/portal")
    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    registered = client.post("/portal/register", data={
        "csrf_token": csrf,
        "organization": "Portal Corp",
        "email": "admin@portal.test",
        "password": "portal-password-1",
    }, follow_redirects=True)
    assert b"Organizzazione registrata correttamente" in registered.data
    assert b"Nuova analisi" in registered.data
    tenant_id = re.search(rb'<p><code>([^<]+)</code></p>', registered.data).group(1).decode()

    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', registered.data).group(1).decode()
    workbook_path = Path(__file__).parents[1] / "outputs" / "milestone19" / "skills_agent_sales_demo.xlsx"
    with workbook_path.open("rb") as workbook:
        submitted = client.post("/portal/analyses", data={
            "csrf_token": csrf,
            "description": "Analyze regional revenue anomalies",
            "dataset": (io.BytesIO(workbook.read()), "sales-demo.xlsx"),
        }, content_type="multipart/form-data", follow_redirects=True)
    assert b"avviata correttamente" in submitted.data

    analysis_id = repository.list_analyses(tenant_id, 1)[0]["id"]
    for _ in range(50):
        if repository.get_analysis(tenant_id, analysis_id)["status"] == "completed":
            break
        time.sleep(0.01)
    result_page = client.get(f"/portal/analyses/{analysis_id}")
    assert result_page.status_code == 200
    assert b"Report dell'analisi" in result_page.data
    assert b"Completed report" in result_page.data
    assert client.get(f"/portal/analyses/{analysis_id}/download").status_code == 200

    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', submitted.data).group(1).decode()
    logged_out = client.post("/portal/logout", data={"csrf_token": csrf}, follow_redirects=True)
    assert b"Registra un'organizzazione" in logged_out.data

    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', logged_out.data).group(1).decode()
    logged_in = client.post("/portal/login", data={
        "csrf_token": csrf,
        "tenant_id": tenant_id,
        "email": "admin@portal.test",
        "password": "portal-password-1",
    }, follow_redirects=True)
    assert b"Accesso completato" in logged_in.data
    assert b"Storico analisi" in logged_in.data


def test_portal_cookie_secure_flag_can_be_disabled_for_local_http(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'cookie.db'}")
    app = create_app(repository, AuthService("c" * 32), coordinator_factory=FakeCoordinator)

    response = app.test_client().get("/portal")
    cookie = response.headers["Set-Cookie"]

    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" not in cookie


def test_root_redirects_to_the_only_public_product_entrypoint(tmp_path):
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'entry.db'}")
    app = create_app(repository, AuthService("e" * 32), coordinator_factory=FakeCoordinator)

    response = app.test_client().get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/portal"


def test_tenant_knowledge_workspace_is_visible_queryable_and_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    monkeypatch.setenv("TENANT_DATA_ROOT", str(tmp_path / "tenants"))
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'knowledge.db'}")
    auth = AuthService("k" * 32)
    app = create_app(repository, auth, coordinator_factory=FakeCoordinator)
    client = app.test_client()
    first = _register(client, "Knowledge Corp", "admin@knowledge.test")
    second = _register(client, "Empty Corp", "admin@empty.test")
    tenant_root = tmp_path / "tenants" / first["identity"]["tenant_id"]
    KnowledgeGraphStore(tenant_root / "knowledge_graph.json").save(KnowledgeGraphSnapshot(
        nodes=[
            KnowledgeNode("run:1", "analysis_run", "Revenue analysis", {"created_at": "2026-07-21T09:00:00Z"}),
            KnowledgeNode("anomaly:1", "anomaly", "Revenue spike", {"severity": "high"}),
        ],
        edges=[KnowledgeEdge("run:1", "anomaly:1", "DETECTED_ANOMALY")],
    ))
    experience = ExperienceStore(tenant_root / "experience.json")
    experience.upsert_experience(AnalyticalExperience(
        "experience:1", "Recurring revenue spike", "Pattern detected in regional revenue",
        anomalies=["Revenue spike"], confidence=0.91, evidence_count=2,
    ))
    experience.save()

    headers = {"Authorization": f"Bearer {first['access_token']}"}
    payload = client.get("/api/v1/knowledge", headers=headers).get_json()
    assert payload["summary"]["nodes"] == 2
    assert payload["summary"]["edges"] == 1
    assert payload["summary"]["experiences"] == 1
    assert payload["quality"]["can_consume"] is True
    assert client.get(
        "/api/v1/knowledge", headers={"Authorization": f"Bearer {second['access_token']}"}
    ).get_json()["summary"]["nodes"] == 0

    query = client.post(
        "/api/v1/knowledge/query", json={"question": "Mostra le anomalie"}, headers=headers,
    )
    assert query.status_code == 200
    assert query.get_json()["execution_type"] == "deterministic_kg_query"

    with client.session_transaction() as portal_session:
        portal_session["access_token"] = first["access_token"]
    page = client.get("/portal/knowledge")
    assert page.status_code == 200
    assert b"Spazio di intelligenza della conoscenza" in page.data
    assert b'/portal/static/knowledge-workspace.js' in page.data
    assert client.get("/portal/static/knowledge-workspace.js").status_code == 200
    assert client.get("/portal/api/knowledge/export").headers["Content-Disposition"].endswith(
        "knowledge-intelligence.json"
    )


def test_knowledge_portal_requires_login(tmp_path):
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'protected.db'}")
    app = create_app(repository, AuthService("z" * 32), coordinator_factory=FakeCoordinator)
    client = app.test_client()

    assert client.get("/portal/knowledge").status_code == 302
    assert client.get("/portal/api/knowledge").status_code == 401


class FakeQueuedJob:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeQueue:
    def __init__(self):
        self.enqueued = []
        self.jobs = {}

    def enqueue(self, function, *args, **kwargs):
        job = FakeQueuedJob()
        self.enqueued.append((function, args, kwargs))
        self.jobs[kwargs["job_id"]] = job
        return job

    def fetch_job(self, job_id):
        return self.jobs.get(job_id)


def test_redis_queue_submission_and_cancel_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'queue.db'}")
    queue = FakeQueue()
    app = create_app(repository, AuthService("q" * 32), coordinator_factory=FakeCoordinator, job_queue=queue)
    client = app.test_client()
    admin = _register(client, "Queue Corp", "admin@queue.test")
    headers = {"Authorization": f"Bearer {admin['access_token']}"}

    created = client.post("/api/v1/analyses", json={
        "description": "Analyze queued data", "records": [{"x": 1}]
    }, headers=headers)
    analysis_id = created.get_json()["id"]
    cancelled = client.post(f"/api/v1/analyses/{analysis_id}/cancel", headers=headers)

    assert created.get_json()["queue"] == "redis_rq"
    assert len(queue.enqueued) == 1
    assert cancelled.status_code == 202
    assert queue.jobs[analysis_id].cancelled is True
