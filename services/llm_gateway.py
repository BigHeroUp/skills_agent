"""Gateway centralizzato per chiamate LLM opzionali."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from openai import OpenAI

from config import (
    get_openai_api_key,
    get_openai_max_calls_per_analysis,
    get_openai_model,
    is_openai_cache_enabled,
)
from utils.logging_config import get_logger


logger = get_logger("llm_gateway")


class LLMGateway:
    """Centralizza OpenAI, fallback locale, cache e budget chiamate."""

    def __init__(
        self,
        client: Any | None = None,
        model: str | None = None,
        api_key: str | None = None,
        max_calls: int | None = None,
        cache_enabled: bool | None = None,
    ):
        self.model = model or get_openai_model()
        self.api_key = api_key if api_key is not None else get_openai_api_key()
        self.client = client if client is not None else (OpenAI(api_key=self.api_key) if self.api_key else None)
        self.max_calls = get_openai_max_calls_per_analysis() if max_calls is None else max(0, int(max_calls))
        self.cache_enabled = is_openai_cache_enabled() if cache_enabled is None else bool(cache_enabled)
        self._cache: dict[str, dict[str, Any]] = {}
        self.reset_usage()

    def complete(
        self,
        messages: list[dict],
        task_name: str,
        temperature: float | None = None,
        cache_key: str | None = None,
        fallback: str | dict | None = None,
    ) -> dict:
        """Esegue una completion opzionale restituendo sempre un payload standard."""
        task = task_name or "unknown"
        key = cache_key or self._build_cache_key(messages, task)
        if self.cache_enabled and key in self._cache:
            cached = copy.deepcopy(self._cache[key])
            cached["cached"] = True
            cached["usage"] = self._usage_payload(call_increment=0)
            return cached

        if not self.client:
            return self._fallback_result(task, fallback, "OPENAI_API_KEY non configurata")

        if self._calls_used >= self.max_calls:
            logger.warning("OpenAI call skipped: max calls reached")
            return self._fallback_result(task, fallback, "max calls reached")

        try:
            params = self.build_request_params(messages, temperature=temperature)
            logger.info(
                "OpenAI request params sanitized. task_name=%s model=%s param_keys=%s message_count=%s temperature_included=%s",
                task,
                params.get("model"),
                sorted(key for key in params.keys() if key != "messages"),
                len(params.get("messages", [])),
                "temperature" in params,
            )
            response = self.client.chat.completions.create(**params)
            self._calls_used += 1
            usage = getattr(response, "usage", None)
            content = response.choices[0].message.content if response.choices else ""
            result = {
                "status": "completed",
                "content": content or "",
                "model": self.model,
                "task_name": task,
                "cached": False,
                "error": None,
                "usage": {
                    "calls": self._calls_used,
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                },
            }
            if self.cache_enabled:
                self._cache[key] = copy.deepcopy(result)
            return result
        except Exception as exc:
            error = str(exc)
            if self._is_bad_request_or_unsupported_parameter(exc):
                return self._fallback_result(task, fallback, error)
            return self._fallback_result(task, fallback, error)

    def build_request_params(
        self,
        messages: list[dict],
        temperature: float | None = None,
        **kwargs,
    ) -> dict:
        """Costruisce i parametri OpenAI compatibili con il modello configurato."""
        params = {
            "model": self.model,
            "messages": messages,
        }
        if temperature is not None and self.model_supports_temperature(self.model):
            params["temperature"] = temperature
        params.update(kwargs)
        return params

    def model_supports_temperature(self, model: str) -> bool:
        """GPT-5 non accetta temperature custom; modelli chat legacy sì."""
        normalized = str(model or "").lower()
        if normalized.startswith("gpt-5"):
            return False
        return normalized.startswith(("gpt-4o", "gpt-4", "gpt-3.5"))

    def get_usage_summary(self) -> dict:
        """Ritorna stato budget e cache per la sessione corrente."""
        return {
            "model": self.model,
            "calls_used": self._calls_used,
            "max_calls": self.max_calls,
            "cache_enabled": self.cache_enabled,
            "cache_size": len(self._cache),
        }

    def reset_usage(self) -> None:
        """Resetta il contatore chiamate della singola analisi."""
        self._calls_used = 0

    def _fallback_result(self, task_name: str, fallback: str | dict | None, error: str) -> dict:
        status = "fallback" if fallback is not None else "error"
        content = fallback if isinstance(fallback, str) else json.dumps(fallback, ensure_ascii=False) if fallback is not None else ""
        return {
            "status": status,
            "content": content,
            "model": self.model,
            "task_name": task_name,
            "cached": False,
            "error": error,
            "usage": self._usage_payload(call_increment=0),
        }

    def _usage_payload(self, call_increment: int) -> dict:
        return {
            "calls": self._calls_used + call_increment,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

    def _build_cache_key(self, messages: list[dict], task_name: str) -> str:
        normalized = json.dumps(
            {
                "model": self.model,
                "task_name": task_name,
                "messages": messages,
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _is_bad_request_or_unsupported_parameter(self, exc: Exception) -> bool:
        name = type(exc).__name__.lower()
        message = str(exc).lower()
        return (
            "badrequest" in name
            or "bad request" in message
            or "unsupported" in message
            or "temperature" in message
            or "parameter" in message
        )


_DEFAULT_GATEWAY: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    """Restituisce il gateway condiviso del runtime applicativo."""
    global _DEFAULT_GATEWAY
    if _DEFAULT_GATEWAY is None:
        _DEFAULT_GATEWAY = LLMGateway()
    return _DEFAULT_GATEWAY


def reset_llm_gateway() -> None:
    """Resetta solo il budget chiamate del gateway condiviso."""
    get_llm_gateway().reset_usage()
