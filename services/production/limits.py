"""Environment-backed limits for one integrated product flow execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from config import (
    get_product_flow_lock_timeout_seconds,
    get_product_flow_max_candidates,
    get_product_flow_max_experience_runs,
    get_product_flow_max_graph_bytes,
    get_product_flow_stage_timeout_seconds,
)


@dataclass(frozen=True)
class ProductFlowLimits:
    stage_timeout_seconds: int
    lock_timeout_seconds: int
    max_graph_bytes: int
    max_candidates: int
    max_experience_runs: int

    @classmethod
    def from_environment(cls) -> "ProductFlowLimits":
        return cls(
            stage_timeout_seconds=get_product_flow_stage_timeout_seconds(),
            lock_timeout_seconds=get_product_flow_lock_timeout_seconds(),
            max_graph_bytes=get_product_flow_max_graph_bytes(),
            max_candidates=get_product_flow_max_candidates(),
            max_experience_runs=get_product_flow_max_experience_runs(),
        )

    def to_dict(self) -> dict[str, int]:
        return asdict(self)
