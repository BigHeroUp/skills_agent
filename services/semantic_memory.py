"""Memoria semantica basata su embeddings con fallback locale."""

from __future__ import annotations

import math
import os
from difflib import SequenceMatcher
from typing import Iterable


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class SemanticMemory:
    """Genera embeddings opzionali e calcola similarita semantica."""

    def __init__(self, client=None, embedding_model: str | None = None):
        self.embedding_model = embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        self.client = client

    def embed_text(self, text: str) -> list[float] | None:
        """Ritorna un embedding normalizzato o None se non disponibile."""
        if not self.client:
            return None
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text or "",
            )
            vector = response.data[0].embedding
            return self.normalize_vector(vector)
        except Exception:
            return None

    def normalize_vector(self, vector: Iterable[float] | None) -> list[float] | None:
        if vector is None:
            return None
        values = [float(item) for item in vector]
        norm = math.sqrt(sum(item * item for item in values))
        if norm == 0:
            return None
        return [item / norm for item in values]

    def cosine_similarity(self, left: Iterable[float], right: Iterable[float]) -> float:
        left_values = [float(item) for item in left]
        right_values = [float(item) for item in right]
        if len(left_values) != len(right_values) or not left_values:
            return 0.0
        return sum(a * b for a, b in zip(left_values, right_values))

    def text_similarity(self, left: str, right: str) -> float:
        normalized_left = " ".join((left or "").lower().split())
        normalized_right = " ".join((right or "").lower().split())
        return SequenceMatcher(None, normalized_left, normalized_right).ratio()

    def _build_default_client(self):
        return None
