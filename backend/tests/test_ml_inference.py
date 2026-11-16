import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.evaluation import evaluate_and_select, train_selected_model
from app.ml.inference import (
    inference_request_from_features,
    load_selected_model,
    predict_run,
)
from test_ml_training import balanced_rows


client = TestClient(app)


@pytest.fixture
def selected_model(tmp_path):
    rows = balanced_rows()
    report, _ = evaluate_and_select(rows)
    model_path = train_selected_model(rows, report, tmp_path)
    metadata_path = tmp_path / "selected-model-metadata.json"
    return rows, model_path, metadata_path


def test_verified_model_predicts_without_reading_ground_truth(selected_model):
    rows, model_path, metadata_path = selected_model
    bundle = load_selected_model(model_path, metadata_path)
    row = next(item for item in rows if item.source_type == "web")
    request = inference_request_from_features(row)
    relabeled = row.model_copy(update={"attack_label": "benign", "scenario": "benign"})
    relabeled_request = inference_request_from_features(relabeled)
    assert request == relabeled_request
    assert predict_run(bundle, request) == predict_run(bundle, relabeled_request)


def test_detection_has_model_provenance_but_no_ground_truth(selected_model):
    rows, model_path, metadata_path = selected_model
    bundle = load_selected_model(model_path, metadata_path)
    detection = predict_run(bundle, inference_request_from_features(rows[0]))
    record = detection.model_dump()
    assert detection.detector_type == "machine_learning"
    assert detection.model_name == "logistic_regression"
    assert len(detection.model_sha256) == 64
    assert "attack_label" not in record and "scenario" not in record


def test_loader_rejects_modified_artifact_before_deserialization(selected_model):
    _, model_path, metadata_path = selected_model
    model_path.write_bytes(model_path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        load_selected_model(model_path, metadata_path)


def test_loader_rejects_wrong_feature_contract(selected_model):
    _, model_path, metadata_path = selected_model
    metadata = json.loads(metadata_path.read_text())
    metadata["feature_columns"] = ["unexpected"]
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="feature contract"):
        load_selected_model(model_path, metadata_path)


def test_api_returns_bounded_prediction(selected_model, monkeypatch):
    rows, model_path, metadata_path = selected_model
    monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
    monkeypatch.setenv("ML_MODEL_METADATA_PATH", str(metadata_path))
    payload = inference_request_from_features(rows[0]).model_dump()
    response = client.post("/detections/ml", json=payload)
    assert response.status_code == 200
    assert response.json()["run_id"] == rows[0].run_id
    assert response.json()["detector_type"] == "machine_learning"


def test_api_rejects_ground_truth_fields(selected_model, monkeypatch):
    rows, model_path, metadata_path = selected_model
    monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
    monkeypatch.setenv("ML_MODEL_METADATA_PATH", str(metadata_path))
    payload = inference_request_from_features(rows[0]).model_dump()
    payload["attack_label"] = "malicious"
    payload["scenario"] = "brute_force"
    response = client.post("/detections/ml", json=payload)
    assert response.status_code == 422


def test_api_is_unavailable_without_configured_model(monkeypatch):
    monkeypatch.delenv("ML_MODEL_PATH", raising=False)
    monkeypatch.delenv("ML_MODEL_METADATA_PATH", raising=False)
    payload = inference_request_from_features(balanced_rows()[0]).model_dump()
    response = client.post("/detections/ml", json=payload)
    assert response.status_code == 503
