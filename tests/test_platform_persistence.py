from services.platform.auth import AuthService, Identity
from services.platform.persistence import PlatformRepository


def test_password_tokens_and_explicit_identity():
    auth = AuthService("x" * 32)
    encoded = auth.hash_password("correct-horse-battery")
    identity = Identity("u1", "t1", "admin@example.test", "admin")

    assert auth.verify_password("correct-horse-battery", encoded)
    assert not auth.verify_password("wrong-password", encoded)
    assert auth.verify_token(auth.issue_token(identity)) == identity


def test_repository_isolates_analyses_by_tenant_and_backs_up(tmp_path):
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'platform.db'}")
    first = repository.create_tenant_with_admin(
        "First", "admin@first.test", AuthService.hash_password("password-first")
    )
    second = repository.create_tenant_with_admin(
        "Second", "admin@second.test", AuthService.hash_password("password-second")
    )
    analysis_id = repository.create_analysis(first["tenant_id"], first["user_id"], {
        "description": "Analyze revenue", "records": [{"revenue": 10}]
    })
    assert repository.get_analysis(first["tenant_id"], analysis_id)["status"] == "queued"
    repository.update_progress(first["tenant_id"], analysis_id, 65)
    assert "records" not in repository.get_analysis(first["tenant_id"], analysis_id)["request"]
    assert repository.get_analysis(first["tenant_id"], analysis_id)["request"]["record_count"] == 1
    assert repository.get_analysis(second["tenant_id"], analysis_id) is None
    assert repository.list_analyses(first["tenant_id"])[0]["progress"] == 65
    assert repository.list_analyses(second["tenant_id"]) == []
    assert repository.backup(tmp_path / "backup.db").exists()
    assert repository.readiness()["schema_version"] == 2
