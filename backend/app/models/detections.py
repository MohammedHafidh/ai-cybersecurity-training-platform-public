from typing import Literal

from pydantic import BaseModel, Field

from app.models.events import Label, Scenario
from app.models.ml import MLDetection


class RuleEvidence(BaseModel):
    feature: str
    observed: int = Field(ge=0)
    operator: Literal[">="] = ">="
    threshold: int = Field(ge=1)


class RuleDetection(BaseModel):
    """A rule prediction. Ground truth is deliberately not stored here."""

    detection_id: str
    run_id: str
    detector_type: Literal["rule_based"] = "rule_based"
    predicted_label: Label
    predicted_scenario: Scenario
    triggered_rule: str | None = None
    evidence: list[RuleEvidence]


class DetectorComparison(BaseModel):
    """Side-by-side detector outputs; neither output is treated as ground truth."""

    comparison_id: str
    run_id: str
    rule_detection: RuleDetection
    ml_detection: MLDetection
    agreement: bool
    outcome: Literal[
        "consensus_benign", "consensus_malicious", "detector_disagreement"
    ]
    review_recommended: bool

