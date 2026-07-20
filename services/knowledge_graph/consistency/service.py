"""Knowledge consistency evaluation over structurally accepted graph records."""

from __future__ import annotations

from services.knowledge_graph.validation import GraphValidationResult

from .contracts import (
    ConsistencyContext,
    ConsistencyReport,
    ConsistencyRule,
    ConsistencyStatus,
    DomainPackConsistencyRules,
)
from .rules import CORE_CONSISTENCY_RULES


def evaluate_consistency(
    validation: GraphValidationResult,
    *,
    core_rules: tuple[ConsistencyRule, ...] = CORE_CONSISTENCY_RULES,
    domain_pack_rules: tuple[DomainPackConsistencyRules, ...] = (),
) -> ConsistencyReport:
    if not validation.can_consume:
        return ConsistencyReport(
            status=ConsistencyStatus.NOT_EVALUATED,
            fingerprint=validation.fingerprint,
            issues=(),
            evaluated_rule_ids=(),
            can_inform_experience=False,
            can_inform_recommendations=False,
        )

    rules = list(core_rules)
    for extension in sorted(domain_pack_rules, key=lambda item: item.pack_id):
        rules.extend(extension.rules)
    rule_ids = [rule.rule_id for rule in rules]
    if len(set(rule_ids)) != len(rule_ids):
        raise ValueError("consistency rule ids must be globally unique")
    context = ConsistencyContext(validation.accepted_nodes, validation.accepted_edges)
    issues = tuple(issue for rule in rules for issue in rule.evaluate(context))
    errors = sum(issue.severity.value == "error" for issue in issues)
    if errors:
        status = ConsistencyStatus.INCONSISTENT
    elif issues:
        status = ConsistencyStatus.DEGRADED
    else:
        status = ConsistencyStatus.CONSISTENT
    return ConsistencyReport(
        status=status,
        fingerprint=validation.fingerprint,
        issues=issues,
        evaluated_rule_ids=tuple(rule_ids),
        can_inform_experience=errors == 0,
        can_inform_recommendations=errors == 0,
    )
