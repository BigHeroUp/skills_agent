import sqlite3

import pytest

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
    assert repository.readiness()["schema_version"] == 5

    restored = PlatformRepository(f"sqlite:///{tmp_path / 'restored.db'}")
    restored.restore(tmp_path / "backup.db")
    assert restored.get_analysis(first["tenant_id"], analysis_id)["request"]["record_count"] == 1


def test_feedback_retention_and_delete_remain_tenant_scoped(tmp_path):
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'lifecycle.db'}")
    first = repository.create_tenant_with_admin("First", "admin@first.test", "hash")
    second = repository.create_tenant_with_admin("Second", "admin@second.test", "hash")
    analysis_id = repository.create_analysis(first["tenant_id"], first["user_id"], {
        "description": "Synthetic analysis", "records": [{"value": 1}],
    })
    repository.update_analysis(first["tenant_id"], analysis_id, status="completed", result={"ok": True})

    feedback = repository.record_analysis_feedback(
        first["tenant_id"], analysis_id, first["user_id"],
        rating=4, outcome="correct", notes="Useful result",
    )
    assert feedback["rating"] == 4
    assert repository.feedback_summary(first["tenant_id"])["outcomes"] == {"correct": 1}
    assert repository.feedback_summary(second["tenant_id"])["total"] == 0
    assert repository.delete_analysis(second["tenant_id"], analysis_id) is False
    assert repository.get_analysis(first["tenant_id"], analysis_id) is not None

    with repository.connect() as connection:
        connection.execute("UPDATE analyses SET created_at=? WHERE id=?", ("2020-01-01T00:00:00+00:00", analysis_id))
    assert len(repository.retention_candidates("2021-01-01T00:00:00+00:00")) == 1
    assert repository.purge_analyses_before("2021-01-01T00:00:00+00:00") == 1
    assert repository.get_analysis(first["tenant_id"], analysis_id) is None


def test_verified_feedback_requires_independent_review_and_resets_on_edit(tmp_path):
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'verified-feedback.db'}")
    tenant = repository.create_tenant_with_admin("Beta", "admin@beta.test", "hash")
    tester_id = repository.create_user(tenant["tenant_id"], "tester@beta.test", "hash", "analyst")
    analysis_id = repository.create_analysis(tenant["tenant_id"], tester_id, {
        "description": "Check totals", "records": [{"value": 10}], "_beta_session_id": "hidden",
    })
    repository.update_analysis(tenant["tenant_id"], analysis_id, status="completed", result={"ok": True})
    assert "_beta_session_id" not in repository.get_analysis(tenant["tenant_id"], analysis_id)["request"]

    feedback = repository.record_analysis_feedback(
        tenant["tenant_id"], analysis_id, tester_id,
        rating=3, outcome="partial", feedback_source="external",
        reason_code="calculation_error", expected_result="Expected total: 10",
        notes="The total is incomplete", analysis_version="0.27.0-test",
    )
    assert feedback["verification_status"] == "pending"
    assert repository.feedback_summary(tenant["tenant_id"])["verified_external_total"] == 0
    with pytest.raises(ValueError, match="cannot verify their own"):
        repository.review_analysis_feedback(
            tenant["tenant_id"], feedback["id"], tester_id,
            verification_status="verified",
        )

    reviewed = repository.review_analysis_feedback(
        tenant["tenant_id"], feedback["id"], tenant["user_id"],
        verification_status="verified", reviewer_notes="Reproduced",
        issue_reference="REV-021",
    )
    assert reviewed["verified_by"] == tenant["user_id"]
    summary = repository.feedback_summary(tenant["tenant_id"])
    assert summary["verified_external_total"] == 1
    assert summary["verified_external_partial"] == 1
    assert summary["distinct_external_testers"] == 1
    assert repository.list_analysis_feedback(tenant["tenant_id"])[0]["user_email"] == "tester@beta.test"

    edited = repository.record_analysis_feedback(
        tenant["tenant_id"], analysis_id, tester_id,
        rating=5, outcome="correct", feedback_source="external",
        notes="Correct after clarification", analysis_version="0.27.0-test",
    )
    assert edited["verification_status"] == "pending"
    assert edited["verified_by"] is None
    assert edited["issue_reference"] == ""
    assert repository.feedback_summary(tenant["tenant_id"])["verified_external_total"] == 0


def test_incorrect_feedback_requires_reproducible_diagnostics(tmp_path):
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'feedback-diagnostics.db'}")
    tenant = repository.create_tenant_with_admin("Diagnostics", "admin@example.test", "hash")
    analysis_id = repository.create_analysis(tenant["tenant_id"], tenant["user_id"], {
        "description": "Check the total", "records": [{"value": 2}],
    })

    with pytest.raises(ValueError, match="diagnostic reason"):
        repository.record_analysis_feedback(
            tenant["tenant_id"], analysis_id, tenant["user_id"],
            rating=2, outcome="incorrect",
        )
    with pytest.raises(ValueError, match="expected result"):
        repository.record_analysis_feedback(
            tenant["tenant_id"], analysis_id, tenant["user_id"],
            rating=2, outcome="incorrect", reason_code="calculation_error",
        )


def test_beta_funnel_is_deduplicated_aggregate_and_tenant_scoped(tmp_path):
    repository = PlatformRepository(f"sqlite:///{tmp_path / 'funnel.db'}")
    first = repository.create_tenant_with_admin("First", "first@beta.test", "hash")
    second = repository.create_tenant_with_admin("Second", "second@beta.test", "hash")
    analysis_id = repository.create_analysis(first["tenant_id"], first["user_id"], {
        "description": "Analyze", "records": [{"value": 1}],
    })
    repository.update_analysis(first["tenant_id"], analysis_id, status="completed", result={"ok": True})

    assert repository.record_beta_funnel_event(
        first["tenant_id"], first["user_id"], "session-1", "portal_accessed"
    ) is True
    assert repository.record_beta_funnel_event(
        first["tenant_id"], first["user_id"], "session-1", "analysis_started", analysis_id
    ) is True
    assert repository.record_beta_funnel_event(
        first["tenant_id"], first["user_id"], "session-1", "analysis_started", analysis_id
    ) is False
    assert repository.record_beta_analysis_completed(
        first["tenant_id"], first["user_id"], analysis_id
    ) is True
    repository.record_beta_funnel_event(
        first["tenant_id"], first["user_id"], "session-1", "result_viewed", analysis_id
    )
    repository.record_beta_funnel_event(
        first["tenant_id"], first["user_id"], "session-1", "feedback_submitted", analysis_id
    )

    summary = repository.beta_funnel_summary(first["tenant_id"])
    assert summary["stages"]["analysis_started"]["sessions"] == 1
    assert summary["conversion"]["started_to_completed"] == 1.0
    assert summary["conversion"]["result_viewed_to_feedback"] == 1.0
    assert repository.beta_funnel_summary(second["tenant_id"])["stages"]["portal_accessed"]["events"] == 0

    assert repository.delete_analysis(first["tenant_id"], analysis_id) is True
    after_delete = repository.beta_funnel_summary(first["tenant_id"])
    assert after_delete["stages"]["analysis_started"]["events"] == 0
    assert after_delete["stages"]["portal_accessed"]["events"] == 1


def test_schema_v4_feedback_migrates_without_becoming_verified_external(tmp_path):
    database = tmp_path / "legacy-v4.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
            CREATE TABLE tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE users (
                id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL,
                password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(tenant_id, email)
            );
            CREATE TABLE analyses (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                tenant_id TEXT NOT NULL, created_by TEXT NOT NULL, description TEXT NOT NULL,
                source_type TEXT NOT NULL, status TEXT NOT NULL, request_json TEXT NOT NULL,
                result_json TEXT, error TEXT, progress INTEGER NOT NULL DEFAULT 0,
                cancel_requested INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE analysis_feedback (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                tenant_id TEXT NOT NULL, analysis_id TEXT NOT NULL, user_id TEXT NOT NULL,
                rating INTEGER NOT NULL, outcome TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(tenant_id, analysis_id, user_id)
            );
            INSERT INTO schema_migrations VALUES (4, '2026-07-29T00:00:00+00:00');
            INSERT INTO tenants VALUES ('t1', 'Legacy', '2026-07-29T00:00:00+00:00');
            INSERT INTO users VALUES ('u1', 't1', 'legacy@test.example', 'hash', 'admin', '2026-07-29T00:00:00+00:00');
            INSERT INTO analyses(id,tenant_id,created_by,description,source_type,status,request_json,result_json,error,created_at,updated_at)
                VALUES ('a1','t1','u1','Legacy analysis','csv','completed','{}','{}',NULL,'2026-07-29T00:00:00+00:00','2026-07-29T00:00:00+00:00');
            INSERT INTO analysis_feedback(id,tenant_id,analysis_id,user_id,rating,outcome,notes,created_at,updated_at)
                VALUES ('f1','t1','a1','u1',5,'correct','legacy','2026-07-29T00:00:00+00:00','2026-07-29T00:00:00+00:00');
        """)

    repository = PlatformRepository(f"sqlite:///{database}")
    migrated = repository.get_analysis_feedback("t1", "a1", "u1")
    assert repository.readiness()["schema_version"] == 5
    assert migrated["feedback_source"] == "unclassified"
    assert migrated["verification_status"] == "pending"
    assert repository.feedback_summary("t1")["verified_external_total"] == 0
