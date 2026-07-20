from services.decision import (
    DecisionEvidence,
    DecisionIntelligenceEngine,
    DecisionOption,
    DecisionSource,
    EvidenceKind,
)
from services.knowledge_graph.consistency import ConsistencyReport, ConsistencyStatus
from services.recommendation import ActionRisk


def _evidence(identifier, score=0.9):
    return DecisionEvidence(
        evidence_id=identifier,
        kind=EvidenceKind.METRIC,
        strength=score,
        reliability=score,
        confidence=score,
        summary=f"Evidence {identifier}",
    )


def _option(identifier, source, evidence_ids, confidence=0.8, risk=ActionRisk.LOW):
    return DecisionOption(
        option_id=identifier,
        action=f"Action {identifier}",
        source=source,
        base_confidence=confidence,
        evidence_ids=tuple(evidence_ids),
        risk=risk,
    )


def test_arbitrates_across_all_decision_sources_deterministically():
    evidence = (_evidence("metric:1"),)
    options = (
        _option("strategy", DecisionSource.STRATEGY, ("metric:1",)),
        _option("anomaly", DecisionSource.ANOMALY, ("metric:1",)),
        _option("root", DecisionSource.ROOT_CAUSE, ("metric:1",)),
        _option("recommendation", DecisionSource.RECOMMENDATION, ("metric:1",)),
    )

    first = DecisionIntelligenceEngine().decide(options, evidence)
    second = DecisionIntelligenceEngine().decide(tuple(reversed(options)), evidence)

    assert first.status == "selected"
    assert first.selected.option_id == "recommendation"
    assert [item.option_id for item in first.ranked_options] == [
        item.option_id for item in second.ranked_options
    ]
    assert first.selected.evidence_ids == ("metric:1",)
    assert first.to_dict()["policy_id"] == "veraxis.decision.v1"


def test_missing_evidence_reduces_completeness_and_is_explained():
    complete = _option("complete", DecisionSource.STRATEGY, ("metric:1",))
    partial = _option("partial", DecisionSource.RECOMMENDATION, ("metric:1", "missing"))

    result = DecisionIntelligenceEngine().decide((partial, complete), (_evidence("metric:1"),))

    assert result.selected.option_id == "complete"
    partial_rank = next(item for item in result.ranked_options if item.option_id == "partial")
    assert partial_rank.missing_evidence_ids == ("missing",)
    assert partial_rank.score < result.selected.score


def test_unsupported_or_low_scoring_options_cause_abstention():
    options = (
        _option("unsupported", DecisionSource.STRATEGY, ("missing",)),
        _option(
            "too-risky",
            DecisionSource.ANOMALY,
            ("weak",),
            confidence=0.2,
            risk=ActionRisk.CRITICAL,
        ),
    )

    result = DecisionIntelligenceEngine().decide(options, (_evidence("weak", 0.2),))

    assert result.status == "abstained"
    assert result.selected is None
    assert set(result.rejected_option_ids) == {"unsupported", "too-risky"}


def test_consistency_gate_blocks_arbitration():
    report = ConsistencyReport(
        status=ConsistencyStatus.INCONSISTENT,
        fingerprint=None,
        issues=(),
        evaluated_rule_ids=(),
        can_inform_experience=False,
        can_inform_recommendations=False,
    )
    option = _option("blocked", DecisionSource.RECOMMENDATION, ("metric:1",))

    result = DecisionIntelligenceEngine().decide(
        (option,),
        (_evidence("metric:1"),),
        consistency_report=report,
    )

    assert result.status == "blocked_by_consistency"
    assert result.selected is None
    assert result.rejected_option_ids == ("blocked",)
