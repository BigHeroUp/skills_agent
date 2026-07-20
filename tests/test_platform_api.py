import time

from platform_api.app import create_app
from services.platform.auth import AuthService
from services.platform.persistence import PlatformRepository
from utils.context import AgentContext


class FakeCoordinator:
    def run(self, description, metadata):
        return AgentContext(
            user_input=description,
            final_report="Completed report",
            anomaly_detection_results={"anomaly_count": 1},
            product_intelligence={"status": "completed"},
        )


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
