from typing import Literal

from pydantic import BaseModel, Field


class ReadinessCheck(BaseModel):
    check_id: str
    status: Literal["pass", "fail"]
    observed: str
    required: str
    message: str


class DatasetReadinessReport(BaseModel):
    """Deterministic evidence for whether ML training is defensible."""

    ready_for_training: bool
    sample_count: int = Field(ge=0)
    label_counts: dict[str, int]
    scenario_counts: dict[str, int]
    source_label_counts: dict[str, dict[str, int]]
    checks: list[ReadinessCheck]
    blockers: list[str]

