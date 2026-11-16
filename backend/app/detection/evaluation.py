"""Public read-only view of the frozen Day 32 report."""
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

router = APIRouter()
ARTIFACT = Path(__file__).resolve().parents[3] / "data/processed/day32/evaluation.json"


class Metrics(BaseModel):
    sample_count: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    label_order: tuple[Literal["benign"], Literal["malicious"]]
    confusion_matrix: tuple[tuple[int, int], tuple[int, int]]


class Breakdown(BaseModel):
    overall: Metrics
    auth: Metrics
    web: Metrics
    network: Metrics


class DetectorMetrics(BaseModel):
    rule: Breakdown
    ml: Breakdown


class EvaluationSummary(BaseModel):
    model_version: str
    rule_version: str
    run_aggregation: str
    metrics: DetectorMetrics


@router.get("/evaluation/summary", response_model=EvaluationSummary, tags=["evaluation"])
def evaluation_summary() -> EvaluationSummary:
    """Return the recorded held-out metrics from the official Day 32 artifact."""
    try:
        return EvaluationSummary.model_validate_json(ARTIFACT.read_bytes())
    except (OSError, ValidationError) as exc:
        raise HTTPException(status_code=503, detail="frozen evaluation summary unavailable") from exc
