import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from app.ml.training import FEATURE_COLUMNS
from app.models.features import RunFeatures
from app.models.ml import MLDetection, MLInferenceRequest, ModelName


DECISION_THRESHOLD = 0.5


@dataclass(frozen=True)
class SelectedModel:
    model: object
    model_name: ModelName
    model_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_selected_model(model_path: Path, metadata_path: Path) -> SelectedModel:
    """Verify provenance before deserializing the trusted local model artifact."""
    if not model_path.is_file() or not metadata_path.is_file():
        raise ValueError("selected model artifact and metadata are required")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("selected model metadata is invalid") from exc

    required = {"model_name", "model_sha256", "feature_columns"}
    if not required.issubset(metadata):
        raise ValueError("selected model metadata is incomplete")
    if metadata["feature_columns"] != FEATURE_COLUMNS:
        raise ValueError("selected model feature contract does not match the application")
    actual_sha256 = _sha256(model_path)
    if metadata["model_sha256"] != actual_sha256:
        raise ValueError("selected model checksum does not match metadata")

    model = joblib.load(model_path)
    if not hasattr(model, "predict") or not hasattr(model, "predict_proba"):
        raise ValueError("selected model does not support required inference operations")
    if metadata["model_name"] not in {
        "logistic_regression",
        "decision_tree",
        "random_forest",
    }:
        raise ValueError("selected model name is unsupported")
    return SelectedModel(
        model=model,
        model_name=metadata["model_name"],
        model_sha256=actual_sha256,
    )


def predict_run(bundle: SelectedModel, request: MLInferenceRequest) -> MLDetection:
    record = request.model_dump(exclude={"run_id"})
    frame = pd.DataFrame([record], columns=FEATURE_COLUMNS)
    probabilities = bundle.model.predict_proba(frame)[0]
    malicious_index = list(bundle.model.classes_).index("malicious")
    malicious_probability = float(probabilities[malicious_index])
    predicted_label = (
        "malicious" if malicious_probability >= DECISION_THRESHOLD else "benign"
    )
    identity = (
        f"{request.run_id}\0{bundle.model_name}\0{bundle.model_sha256}".encode("utf-8")
    )
    return MLDetection(
        detection_id="ml-det-" + hashlib.sha256(identity).hexdigest()[:24],
        run_id=request.run_id,
        model_name=bundle.model_name,
        model_sha256=bundle.model_sha256,
        predicted_label=predicted_label,
        malicious_probability=malicious_probability,
        decision_threshold=DECISION_THRESHOLD,
    )


def inference_request_from_features(row: RunFeatures) -> MLInferenceRequest:
    """Cross the explicit boundary from labeled dataset row to unlabeled inputs."""
    values = row.model_dump(include=set(FEATURE_COLUMNS))
    return MLInferenceRequest(run_id=row.run_id, **values)
