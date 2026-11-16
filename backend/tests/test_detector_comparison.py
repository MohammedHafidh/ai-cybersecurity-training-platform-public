import numpy as np
from fastapi.testclient import TestClient

from app.detection.comparison import compare_detectors
from app.main import app
from app.ml.evaluation import evaluate_and_select, train_selected_model
from app.ml.inference import (
    SelectedModel,
    inference_request_from_features,
    load_selected_model,
)
from test_ml_training import balanced_rows


client = TestClient(app)


class AlwaysBenignModel:
    classes_ = np.array(["benign", "malicious"])

    def predict_proba(self, frame):
        return np.array([[0.9, 0.1] for _ in range(len(frame))])


def real_bundle(tmp_path):
    rows = balanced_rows()
    report, _ = evaluate_and_select(rows)
    model_path = train_selected_model(rows, report, tmp_path)
    metadata_path = tmp_path / "selected-model-metadata.json"
    return rows, model_path, metadata_path, load_selected_model(model_path, metadata_path)


def test_comparison_preserves_both_independent_detections(tmp_path):
    rows, _, _, bundle = real_bundle(tmp_path)
    request = inference_request_from_features(rows[0])
    comparison = compare_detectors(bundle, request)
    assert comparison.run_id == request.run_id
    assert comparison.rule_detection.detector_type == "rule_based"
    assert comparison.ml_detection.detector_type == "machine_learning"
    assert comparison.agreement
    assert comparison.outcome in {"consensus_benign", "consensus_malicious"}
    assert not comparison.review_recommended


def test_disagreement_is_explicit_and_recommends_review():
    malicious = next(
        row
        for row in balanced_rows()
        if row.source_type == "auth" and row.attack_label == "malicious"
    )
    request = inference_request_from_features(malicious)
    bundle = SelectedModel(
        model=AlwaysBenignModel(),
        model_name="logistic_regression",
        model_sha256="0" * 64,
    )
    comparison = compare_detectors(bundle, request)
    assert comparison.rule_detection.predicted_label == "malicious"
    assert comparison.ml_detection.predicted_label == "benign"
    assert not comparison.agreement
    assert comparison.outcome == "detector_disagreement"
    assert comparison.review_recommended


def test_comparison_is_independent_of_ground_truth(tmp_path):
    rows, _, _, bundle = real_bundle(tmp_path)
    row = rows[0]
    relabeled = row.model_copy(update={"attack_label": "malicious", "scenario": "brute_force"})
    first = compare_detectors(bundle, inference_request_from_features(row))
    second = compare_detectors(bundle, inference_request_from_features(relabeled))
    assert first == second


def test_comparison_output_contains_no_ground_truth(tmp_path):
    rows, _, _, bundle = real_bundle(tmp_path)
    comparison = compare_detectors(bundle, inference_request_from_features(rows[0]))
    record = comparison.model_dump()
    assert "attack_label" not in str(record)
    assert "ground_truth" not in str(record)


def test_comparison_api_returns_both_results(tmp_path, monkeypatch):
    rows, model_path, metadata_path, _ = real_bundle(tmp_path)
    monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
    monkeypatch.setenv("ML_MODEL_METADATA_PATH", str(metadata_path))
    payload = inference_request_from_features(rows[0]).model_dump()
    response = client.post("/detections/compare", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["rule_detection"]["detector_type"] == "rule_based"
    assert result["ml_detection"]["detector_type"] == "machine_learning"
