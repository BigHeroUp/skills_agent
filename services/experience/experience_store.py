"""Local JSON store for deterministic analytical experiences."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .experience_models import AnalyticalExperience


class ExperienceStore:
    """Simple local JSON persistence for analytical experiences."""

    DEFAULT_PATH = Path("data") / "experience" / "experience_store.json"

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else self.DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._experiences: dict[str, AnalyticalExperience] = {}

    def load(self) -> list[AnalyticalExperience]:
        self._experiences = {}
        if not self.path.exists():
            return self.list_experiences()

        try:
            with self.path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return self.list_experiences()

        experiences = payload.get("experiences", []) if isinstance(payload, dict) else []
        for item in experiences or []:
            if isinstance(item, dict):
                experience = AnalyticalExperience.from_dict(item)
                self.upsert_experience(experience)
        return self.list_experiences()

    def save(self) -> list[AnalyticalExperience]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "experiences": [experience.to_dict() for experience in self.list_experiences()],
        }
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self._json_safe(payload), file, ensure_ascii=False, indent=2, sort_keys=True)
        return self.list_experiences()

    def upsert_experience(self, experience: AnalyticalExperience) -> None:
        if not experience.id:
            return
        sanitized = AnalyticalExperience.from_dict(experience.to_dict())
        duplicate_id = self._find_duplicate_id(sanitized)
        if duplicate_id and duplicate_id != sanitized.id:
            self._experiences.pop(duplicate_id, None)
        self._experiences[sanitized.id] = sanitized

    def list_experiences(self) -> list[AnalyticalExperience]:
        return [self._experiences[key] for key in sorted(self._experiences)]

    def get_experience(self, id: str) -> AnalyticalExperience | None:
        return self._experiences.get(id)

    def clear(self) -> None:
        self._experiences = {}
        if self.path.exists():
            self.path.unlink()

    def _find_duplicate_id(self, candidate: AnalyticalExperience) -> str | None:
        candidate_signature = self._signature(candidate)
        for experience_id, experience in self._experiences.items():
            if experience_id == candidate.id:
                continue
            if self._signature(experience) == candidate_signature:
                return experience_id
        return None

    def _signature(self, experience: AnalyticalExperience) -> tuple[str, tuple[str, ...]]:
        if experience.metrics and not experience.anomalies and not experience.root_causes:
            return ("metric", tuple(sorted(item.lower() for item in experience.metrics)))
        if experience.anomalies:
            return ("anomaly", tuple(sorted(item.lower() for item in experience.anomalies)))
        if experience.root_causes:
            return ("root_cause", tuple(sorted(item.lower() for item in experience.root_causes)))
        return ("id", (experience.id.lower(),))

    def find_by_metric(self, metric: str) -> list[AnalyticalExperience]:
        expected = str(metric or "").strip().lower()
        return [
            experience
            for experience in self.list_experiences()
            if expected and expected in {item.lower() for item in experience.metrics}
        ]

    def find_by_anomaly(self, anomaly: str) -> list[AnalyticalExperience]:
        expected = str(anomaly or "").strip().lower()
        return [
            experience
            for experience in self.list_experiences()
            if expected and expected in {item.lower() for item in experience.anomalies}
        ]

    def find_by_root_cause(self, root_cause: str) -> list[AnalyticalExperience]:
        expected = str(root_cause or "").strip().lower()
        return [
            experience
            for experience in self.list_experiences()
            if expected and expected in {item.lower() for item in experience.root_causes}
        ]

    def find_by_tag(self, tag: str) -> list[AnalyticalExperience]:
        expected = str(tag or "").strip().lower()
        return [
            experience
            for experience in self.list_experiences()
            if expected and expected in {item.lower() for item in experience.tags}
        ]

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
