from services.knowledge_graph.consistency import ConsistencyReport, ConsistencyStatus
from services.recommendation import (
    ActionRisk,
    NextBestActionEngine,
    RecommendationCandidate,
    RecommendationContext,
)


def _candidate(
    identifier,
    confidence,
    evidence,
    urgency=0.0,
    risk=ActionRisk.LOW,
    domain="general",
    contexts=(),
):
    return RecommendationCandidate(
        candidate_id=identifier,
        action=f"Action {identifier}",
        reason=f"Reason {identifier}",
        confidence=confidence,
        evidence_strength=evidence,
        urgency=urgency,
        risk=risk,
        domain=domain,
        contexts=frozenset(contexts),
        evidence_ids=(f"evidence:{identifier}",),
    )


def test_ranking_is_deterministic_explainable_and_risk_adjusted():
    engine = NextBestActionEngine()
    candidates = (
        _candidate("safe", 0.8, 0.8, 0.6),
        _candidate("medium", 0.9, 0.9, 0.8, ActionRisk.MEDIUM),
        _candidate("weak", 0.4, 0.3, 0.1),
    )

    first = engine.recommend(candidates, RecommendationContext())
    second = engine.recommend(tuple(reversed(candidates)), RecommendationContext())

    assert [item.candidate_id for item in first.recommendations] == [
        item.candidate_id for item in second.recommendations
    ]
    assert first.recommendations[0].candidate_id == "medium"
    assert first.recommendations[0].rank == 1
    assert first.recommendations[0].evidence_ids == ("evidence:medium",)
    assert first.to_dict()["policy_id"] == "veraxis.recommendation.v1"


def test_context_domain_confidence_and_risk_are_admission_filters():
    candidates = (
        _candidate("retail", 0.8, 0.8, domain="retail", contexts=("analysis",)),
        _candidate("finance", 0.8, 0.8, domain="finance"),
        _candidate("risky", 0.9, 0.9, risk=ActionRisk.HIGH),
        _candidate("uncertain", 0.2, 0.9),
    )

    result = NextBestActionEngine().recommend(
        candidates,
        RecommendationContext(domain="retail", maximum_risk=ActionRisk.MEDIUM),
    )

    assert [item.candidate_id for item in result.recommendations] == ["retail"]
    assert set(result.rejected_candidate_ids) == {"finance", "risky", "uncertain"}


def test_inconsistent_evidence_blocks_all_recommendations():
    report = ConsistencyReport(
        status=ConsistencyStatus.INCONSISTENT,
        fingerprint=None,
        issues=(),
        evaluated_rule_ids=("core.rule",),
        can_inform_experience=False,
        can_inform_recommendations=False,
    )
    candidate = _candidate("blocked", 0.9, 0.9)

    result = NextBestActionEngine().recommend(
        (candidate,),
        RecommendationContext(),
        consistency_report=report,
    )

    assert result.status == "blocked_by_consistency"
    assert result.recommendations == ()
    assert result.rejected_candidate_ids == ("blocked",)


def test_experience_adapter_preserves_provenance():
    payload = {
        "recommendations": [{
            "step": "Check response time by region",
            "reason": "Repeated anomaly",
            "priority": "high",
            "confidence": 0.82,
            "source_experience_ids": ["experience:1"],
        }],
    }

    candidates = NextBestActionEngine.candidates_from_experience(payload)
    result = NextBestActionEngine().recommend(candidates, RecommendationContext())

    assert candidates[0].source == "experience"
    assert result.recommendations[0].evidence_ids == ("experience:1",)
    assert result.recommendations[0].action == "Check response time by region"
