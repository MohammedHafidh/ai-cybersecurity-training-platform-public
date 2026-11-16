"""Inference with the frozen Dataset v1 Logistic Regression pipeline."""
import hashlib
import io
import json
from importlib.metadata import version
from pathlib import Path

import joblib

from app.ml.dataset_v1 import FEATURES, feature_frame

MODEL_VERSION = "capstone-ml-v1"


def load_pipeline(bundle: Path):
    """Load a bundle from a trusted release or repository checkout."""
    metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
    if metadata["version"] != MODEL_VERSION:
        raise ValueError("unsupported model version")
    payload = (bundle / "pipeline.joblib").read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata["model_sha256"]:
        raise ValueError("model checksum mismatch")
    for package, expected in metadata["dependencies"].items():
        if version(package) != expected:
            raise ValueError(f"model requires {package}=={expected}")
    return joblib.load(io.BytesIO(payload))


def predict_observations(pipeline, observations):
    """Classify observable feature records in input order."""
    rows = list(observations)
    if not rows:
        raise ValueError("at least one observation is required")
    for row in rows:
        source = row.get("source_type")
        if source not in FEATURES or set(row) != {"source_type", *FEATURES[source]}:
            raise ValueError("expected exactly the observable fields for the source")
    frame = feature_frame(rows)
    probabilities = pipeline.predict_proba(frame)
    malicious = list(pipeline.classes_).index("malicious")
    return [
        {"model_version": MODEL_VERSION, "predicted_label": label,
         "malicious_probability": float(scores[malicious])}
        for label, scores in zip(pipeline.predict(frame), probabilities, strict=True)
    ]
