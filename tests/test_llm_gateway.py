from types import SimpleNamespace

from services.llm_gateway import LLMGateway


class _FakeCompletions:
    def __init__(self, response_text="ok", error=None):
        self.calls = 0
        self.last_params = None
        self.response_text = response_text
        self.error = error

    def create(self, **params):
        self.calls += 1
        self.last_params = params
        if self.error:
            raise self.error
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.response_text),
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=3,
                completion_tokens=2,
                total_tokens=5,
            ),
        )


class _FakeClient:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)


def test_gpt5_request_params_do_not_include_temperature():
    gateway = LLMGateway(client=_FakeClient(_FakeCompletions()), model="gpt-5.5", api_key="key")

    params = gateway.build_request_params([{"role": "user", "content": "ciao"}], temperature=0.5)

    assert params["model"] == "gpt-5.5"
    assert "temperature" not in params


def test_gpt4o_mini_request_params_include_temperature():
    gateway = LLMGateway(client=_FakeClient(_FakeCompletions()), model="gpt-4o-mini", api_key="key")

    params = gateway.build_request_params([{"role": "user", "content": "ciao"}], temperature=0.5)

    assert params["temperature"] == 0.5


def test_complete_falls_back_without_api_key():
    gateway = LLMGateway(client=None, model="gpt-5.5", api_key="")

    result = gateway.complete(
        [{"role": "user", "content": "ciao"}],
        task_name="test",
        temperature=0.7,
        fallback="fallback locale",
    )

    assert result["status"] == "fallback"
    assert result["content"] == "fallback locale"


def test_complete_falls_back_on_unsupported_parameter_error():
    completions = _FakeCompletions(error=Exception("unsupported parameter: temperature"))
    gateway = LLMGateway(client=_FakeClient(completions), model="gpt-4o-mini", api_key="key")

    result = gateway.complete(
        [{"role": "user", "content": "ciao"}],
        task_name="test",
        temperature=0.7,
        fallback="fallback locale",
    )

    assert result["status"] == "fallback"
    assert result["content"] == "fallback locale"


def test_cache_hit_avoids_second_openai_call():
    completions = _FakeCompletions("prima risposta")
    gateway = LLMGateway(
        client=_FakeClient(completions),
        model="gpt-4o-mini",
        api_key="key",
        cache_enabled=True,
    )
    messages = [{"role": "user", "content": "ciao"}]

    first = gateway.complete(messages, task_name="cache-test", temperature=0.2)
    second = gateway.complete(messages, task_name="cache-test", temperature=0.2)

    assert first["cached"] is False
    assert second["cached"] is True
    assert completions.calls == 1


def test_max_calls_per_analysis_returns_fallback_after_limit():
    completions = _FakeCompletions("ok")
    gateway = LLMGateway(
        client=_FakeClient(completions),
        model="gpt-4o-mini",
        api_key="key",
        max_calls=1,
        cache_enabled=False,
    )

    first = gateway.complete([{"role": "user", "content": "a"}], task_name="one", fallback="fallback")
    second = gateway.complete([{"role": "user", "content": "b"}], task_name="two", fallback="fallback")

    assert first["status"] == "completed"
    assert second["status"] == "fallback"
    assert second["error"] == "max calls reached"
    assert completions.calls == 1
