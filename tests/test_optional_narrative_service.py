import json

import pytest

from services.narrative import (
    NarrativePolicy,
    NarrativePurpose,
    NarrativeRequest,
    OptionalNarrativeService,
)


class FakeGateway:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return dict(self.response)


def _request(**kwargs):
    return NarrativeRequest(
        purpose=kwargs.pop("purpose", NarrativePurpose.EXECUTIVE_SUMMARY),
        deterministic_text=kwargs.pop("deterministic_text", "Metric up 10%; confidence 0.8."),
        facts=kwargs.pop("facts", {"metric": "revenue", "change_pct": 10}),
        **kwargs,
    )


def test_layer_is_disabled_by_default_and_preserves_deterministic_content():
    gateway = FakeGateway({"status": "completed", "content": "LLM text"})

    result = OptionalNarrativeService(gateway=gateway).render(_request())

    assert result.status == "disabled"
    assert result.content == result.deterministic_text
    assert result.used_llm is False
    assert gateway.calls == []


def test_enabled_layer_uses_gateway_without_losing_authoritative_source():
    gateway = FakeGateway({
        "status": "completed",
        "content": "Ricavi in aumento del 10%, con confidence 0,8.",
        "model": "test-model",
        "error": None,
    })
    service = OptionalNarrativeService(
        gateway=gateway,
        policy=NarrativePolicy(enabled=True),
    )

    result = service.render(_request())

    assert result.status == "completed"
    assert result.used_llm is True
    assert result.model == "test-model"
    assert result.deterministic_text == "Metric up 10%; confidence 0.8."
    assert result.provenance["authoritative_source"] == "deterministic_text"
    assert "Do not add facts" in gateway.calls[0][0][1]["content"]
    assert json.dumps(result.to_dict(), allow_nan=False)


def test_gateway_failure_returns_exact_deterministic_fallback():
    gateway = FakeGateway({
        "status": "fallback",
        "content": "Metric up 10%; confidence 0.8.",
        "model": "test-model",
        "error": "offline",
    })
    service = OptionalNarrativeService(gateway, NarrativePolicy(enabled=True))

    result = service.render(_request())

    assert result.status == "fallback"
    assert result.content == "Metric up 10%; confidence 0.8."
    assert result.used_llm is False
    assert result.error == "offline"


def test_critical_use_is_blocked_without_calling_gateway():
    gateway = FakeGateway({"status": "completed", "content": "Choose action A"})
    service = OptionalNarrativeService(gateway, NarrativePolicy(enabled=True))

    result = service.render(_request(critical=True))

    assert result.status == "blocked_critical_use"
    assert result.used_llm is False
    assert gateway.calls == []


def test_raw_data_keys_are_rejected_before_any_gateway_call():
    gateway = FakeGateway({"status": "completed", "content": "text"})
    service = OptionalNarrativeService(gateway, NarrativePolicy(enabled=True))

    with pytest.raises(ValueError, match="forbidden narrative fact key"):
        service.render(_request(facts={"analysis": {"raw_rows": [["secret"]]}}))
    assert gateway.calls == []


def test_input_limit_falls_back_without_calling_gateway():
    gateway = FakeGateway({"status": "completed", "content": "text"})
    service = OptionalNarrativeService(
        gateway,
        NarrativePolicy(enabled=True, max_input_characters=50),
    )

    result = service.render(_request(deterministic_text="x" * 100))

    assert result.status == "input_too_large"
    assert result.content == "x" * 100
    assert gateway.calls == []
