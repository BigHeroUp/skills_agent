"""Optional LLM narrative facade with deterministic fallback and provenance."""

from __future__ import annotations

import json

from services.llm_gateway import LLMGateway, get_llm_gateway
from services.knowledge_graph.domain.issues import json_safe

from .contracts import NarrativeRequest, NarrativeResult
from .policy import DEFAULT_NARRATIVE_POLICY, NarrativePolicy


class OptionalNarrativeService:
    def __init__(
        self,
        gateway: LLMGateway | None = None,
        policy: NarrativePolicy = DEFAULT_NARRATIVE_POLICY,
    ):
        self.gateway = gateway
        self.policy = policy

    def render(self, request: NarrativeRequest) -> NarrativeResult:
        self.policy.validate_facts(request.facts)
        if request.critical:
            return self._deterministic(
                request,
                status="blocked_critical_use",
                error="The optional narrative layer cannot perform critical decisions.",
            )
        if not self.policy.enabled:
            return self._deterministic(request, status="disabled")

        facts_json = json.dumps(json_safe(request.facts), ensure_ascii=False, sort_keys=True)
        prompt = (
            f"Purpose: {request.purpose.value}\n"
            f"Audience: {request.audience}\n"
            f"Language: {request.language}\n"
            "Rewrite only the supplied deterministic content. Do not add facts, "
            "numbers, causes, recommendations, or decisions. Preserve uncertainty "
            "and evidence references.\n\n"
            f"Deterministic content:\n{request.deterministic_text}\n\n"
            f"Approved facts:\n{facts_json}"
        )
        if len(prompt) > self.policy.max_input_characters:
            return self._deterministic(
                request,
                status="input_too_large",
                error="Narrative input exceeds the configured character limit.",
            )
        gateway = self.gateway or get_llm_gateway()
        response = gateway.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a non-critical narrative formatter. The supplied "
                        "deterministic content is authoritative. Never introduce new facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            task_name=f"narrative.{request.purpose.value}",
            fallback=request.deterministic_text,
        )
        completed = response.get("status") == "completed" and bool(
            str(response.get("content") or "").strip()
        )
        return NarrativeResult(
            status="completed" if completed else "fallback",
            content=(
                str(response.get("content")).strip()
                if completed
                else request.deterministic_text
            ),
            deterministic_text=request.deterministic_text,
            purpose=request.purpose,
            used_llm=completed,
            model=str(response.get("model")) if completed and response.get("model") else None,
            error=response.get("error"),
            provenance=self._provenance(request),
        )

    def _deterministic(self, request, status, error=None):
        return NarrativeResult(
            status=status,
            content=request.deterministic_text,
            deterministic_text=request.deterministic_text,
            purpose=request.purpose,
            used_llm=False,
            model=None,
            error=error,
            provenance=self._provenance(request),
        )

    def _provenance(self, request):
        return {
            "authoritative_source": "deterministic_text",
            "critical": request.critical,
            "policy_id": self.policy.policy_id,
            "policy_version": self.policy.version,
        }
