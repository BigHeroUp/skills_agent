"""Safety policy for optional narrative generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class NarrativePolicy:
    policy_id: str = "veraxis.narrative.optional.v1"
    version: str = "1.0.0"
    enabled: bool = False
    max_input_characters: int = 12_000
    forbidden_fact_keys: frozenset[str] = frozenset({
        "dataframe",
        "raw_data",
        "raw_rows",
        "rows",
        "records",
    })

    def validate_facts(self, facts: Mapping[str, Any]) -> None:
        def visit(value: Any, path: str = "facts") -> None:
            if isinstance(value, Mapping):
                for key, item in value.items():
                    clean = str(key).lower()
                    if clean in self.forbidden_fact_keys:
                        raise ValueError(f"forbidden narrative fact key: {path}.{key}")
                    visit(item, f"{path}.{key}")
            elif isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    visit(item, f"{path}[{index}]")

        visit(facts)


DEFAULT_NARRATIVE_POLICY = NarrativePolicy()
