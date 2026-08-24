from validation_lab.beta_readiness import BetaReadinessEvaluator


def _ready_evidence():
    return {
        "validation_cases": {"total": 36, "domains": 4},
        "feedback": {
            "total": 20,
            "correct": 17,
            "partial": 2,
            "incorrect": 1,
            "verified_external_total": 20,
            "verified_external_correct": 17,
            "distinct_external_testers": 5,
        },
        "load_test": {"concurrency": 5, "requests": 20, "error_rate": 0.0, "p95_ms": 1200},
        "operations": {
            "backup_restore_passed": True,
            "retention_delete_passed": True,
            "monitoring_passed": True,
        },
        "safety": {
            "tenant_isolation_passed": True,
            "unsupported_requests_passed": True,
            "open_critical_bugs": 0,
        },
    }


def test_private_beta_gates_pass_only_with_complete_evidence():
    result = BetaReadinessEvaluator().evaluate(_ready_evidence())

    assert result["status"] == "ready"
    assert result["passed"] == result["total"] == 10


def test_missing_evidence_never_becomes_implicit_success():
    result = BetaReadinessEvaluator().evaluate({})

    assert result["status"] == "not_ready"
    assert "validation_cases" in result["failed_gates"]
    assert "tenant_isolation" in result["failed_gates"]


def test_accuracy_gate_requires_volume_and_quality():
    evidence = _ready_evidence()
    evidence["feedback"].update({
        "verified_external_total": 5,
        "verified_external_correct": 5,
        "distinct_external_testers": 3,
    })

    result = BetaReadinessEvaluator().evaluate(evidence)

    assert "validated_accuracy" in result["failed_gates"]


def test_unverified_or_single_tester_feedback_cannot_open_beta():
    unverified = _ready_evidence()
    unverified["feedback"] = {"total": 20, "correct": 20}
    assert "validated_accuracy" in BetaReadinessEvaluator().evaluate(unverified)["failed_gates"]

    concentrated = _ready_evidence()
    concentrated["feedback"]["distinct_external_testers"] = 2
    result = BetaReadinessEvaluator().evaluate(concentrated)
    assert "validated_accuracy" in result["failed_gates"]
    gate = next(item for item in result["gates"] if item["id"] == "validated_accuracy")
    assert gate["observed"]["distinct_external_testers"] == 2
