from config import DEFAULT_OPENAI_MODEL, get_openai_model


def test_openai_model_uses_modern_default(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    assert DEFAULT_OPENAI_MODEL == "gpt-5.5"
    assert get_openai_model() == "gpt-5.5"


def test_openai_model_can_be_overridden(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom-model")

    assert get_openai_model() == "custom-model"
