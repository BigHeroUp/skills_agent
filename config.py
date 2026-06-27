"""Configurazione applicativa centralizzata."""

import os


DEFAULT_OPENAI_MODEL = "gpt-5.5"
DEFAULT_OPENAI_MAX_CALLS_PER_ANALYSIS = 2


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_openai_model() -> str:
    """Restituisce il modello OpenAI configurato o il default applicativo."""
    return os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL


def get_openai_api_key() -> str:
    """Restituisce la chiave OpenAI configurata, se presente."""
    return os.getenv("OPENAI_API_KEY", "").strip()


def is_openai_enabled() -> bool:
    """OpenAI è disponibile solo se la chiave è presente."""
    return bool(get_openai_api_key())


def get_openai_max_calls_per_analysis() -> int:
    """Limite massimo di chiamate OpenAI per singola analisi."""
    return max(0, _env_int("OPENAI_MAX_CALLS_PER_ANALYSIS", DEFAULT_OPENAI_MAX_CALLS_PER_ANALYSIS))


def is_openai_cache_enabled() -> bool:
    """Indica se la cache in memoria delle chiamate LLM è attiva."""
    return _env_bool("OPENAI_CACHE_ENABLED", True)


OPENAI_API_KEY = get_openai_api_key()
OPENAI_MODEL = get_openai_model()
OPENAI_ENABLED = is_openai_enabled()
OPENAI_MAX_CALLS_PER_ANALYSIS = get_openai_max_calls_per_analysis()
OPENAI_CACHE_ENABLED = is_openai_cache_enabled()
