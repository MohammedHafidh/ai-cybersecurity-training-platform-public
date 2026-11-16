from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.events import Label, SourceType


ModelName = Literal["logistic_regression", "decision_tree", "random_forest"]


class ModelMetrics(BaseModel):
    model_name: ModelName
    accuracy: float = Field(ge=0, le=1)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    false_positive_rate: float = Field(ge=0, le=1)
    confusion_matrix: list[list[int]]


class MLPrediction(BaseModel):
    model_name: ModelName
    run_id: str
    predicted_label: Label
    malicious_probability: float = Field(ge=0, le=1)
    split: Literal["validation"] = "validation"


class ModelTrainingReport(BaseModel):
    training_sample_count: int = Field(ge=1)
    validation_sample_count: int = Field(ge=1)
    random_state: int
    stratified: bool
    feature_columns: list[str]
    train_run_ids: list[str]
    validation_run_ids: list[str]
    candidates: list[ModelMetrics]
    selected_model: None = None
    selection_note: str


class EvaluationPrediction(BaseModel):
    model_name: ModelName
    run_id: str
    fold: int = Field(ge=1)
    predicted_label: Label
    malicious_probability: float = Field(ge=0, le=1)
    split: Literal["cross_validation"] = "cross_validation"


class SourceMetrics(ModelMetrics):
    source_type: SourceType
    sample_count: int = Field(ge=1)


class ModelEvaluation(BaseModel):
    model_name: ModelName
    overall: ModelMetrics
    by_source: list[SourceMetrics]


class ModelSelectionReport(BaseModel):
    sample_count: int = Field(ge=1)
    fold_count: int = Field(ge=2)
    random_state: int
    stratification: str
    selection_criteria: list[str]
    candidates: list[ModelEvaluation]
    selected_model: ModelName
    selection_reason: str
    limitations: list[str]


class HoldoutPrediction(BaseModel):
    model_name: ModelName
    run_id: str
    predicted_label: Label
    malicious_probability: float = Field(ge=0, le=1)
    split: Literal["final_holdout"] = "final_holdout"


class HoldoutEvaluationReport(BaseModel):
    development_sample_count: int = Field(ge=1)
    holdout_sample_count: int = Field(ge=1)
    holdout_group: str
    development_run_ids: list[str]
    holdout_run_ids: list[str]
    selection: ModelSelectionReport
    final_test: ModelEvaluation
    limitations: list[str]


class MLInferenceRequest(BaseModel):
    """Observable model inputs only; trusted labels are intentionally excluded."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=200)
    source_type: SourceType
    event_count: int = Field(ge=1, le=1_000_000)
    auth_attempt_count: int = Field(ge=0, le=1_000_000)
    failed_login_count: int = Field(ge=0, le=1_000_000)
    successful_login_count: int = Field(ge=0, le=1_000_000)
    unique_username_count: int = Field(ge=0, le=1_000_000)
    web_request_count: int = Field(ge=0, le=1_000_000)
    max_request_length: int = Field(ge=0, le=10_000_000)
    suspicious_token_count: int = Field(ge=0, le=1_000_000)
    connection_count: int = Field(ge=0, le=1_000_000)
    unique_destination_port_count: int = Field(ge=0, le=65_535)


class MLDetection(BaseModel):
    """An ML prediction with provenance, never a ground-truth record."""

    detection_id: str
    run_id: str
    detector_type: Literal["machine_learning"] = "machine_learning"
    model_name: ModelName
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    predicted_label: Label
    malicious_probability: float = Field(ge=0, le=1)
    decision_threshold: float = Field(ge=0, le=1)

