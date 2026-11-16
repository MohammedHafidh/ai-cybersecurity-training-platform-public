import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.detection.service import DetectionService, DetectionServiceError, RunNotFound
from app.main import app
from app.persistence.core import RunRecord
from test_ingestion_api import database, sample

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "data/releases/capstone-ml-v1"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_observations_match_frozen_rule_and_ml_run_decisions():
    service = DetectionService(BUNDLE)
    rules = {d["row_id"]: d for d in read("data/processed/day26/observation-decisions.json")}
    model_runs = {d["run_id"]: d for d in read("data/processed/day30/predictions.json")}
    tested = set()
    for source in ("auth", "web", "network"):
        path = ROOT / f"data/processed/day20/{source}.jsonl"
        rows = [row for row in map(json.loads, path.read_text().splitlines()) if row["row_id"] in rules]
        result = service.score_observations(source, rows)
        by_run = {}
        for row, output in zip(rows, result, strict=True):
            expected = rules[output.row_id]
            assert output.rule.predicted_label == expected["predicted_label"]
            assert output.rule.evidence == expected["evidence"]
            assert "attack_label" not in output.observed_features
            by_run.setdefault(row["run_id"], []).append(output.ml.predicted_label)
        for run_id, outputs in by_run.items():
            tested.add(run_id)
            assert ("malicious" if "malicious" in outputs else "benign") == model_runs[run_id]["predicted_label"]
    assert tested == model_runs.keys()


def test_detects_from_day34_storage_with_offset_timestamps(database):
    service = DetectionService(BUNDLE)
    client = TestClient(app)
    for source in ("auth", "web", "network"):
        key = f"day35-{source}"
        request = sample(source, key)
        request["run"]["start_time"] = "2026-11-06T15:00:00+03:00"
        request["events"][0]["timestamp"] = "2026-11-06T12:00:05Z"
        assert client.post("/ingestion/runs", json=request).status_code == 201
        with database() as session:
            result = service.detect(session, key)
        observation, = result.observations
        assert result.ground_truth.expected_label == "malicious"
        assert result.rule_label == "benign"
        assert observation.ml.model_version == "capstone-ml-v1"
        assert observation.rule.evidence["event_ids"] == [f"event-{key}"]
        assert observation.raw_source_files == ["fixture.log"]
        if source != "web":
            assert observation.rule.evidence["window_start"] == "2026-11-06T12:00:00+00:00"


def test_missing_run_and_bundle_have_clear_errors(database, tmp_path):
    with pytest.raises(DetectionServiceError, match="bundle unavailable or invalid"):
        DetectionService(tmp_path)
    service = DetectionService(BUNDLE)
    with database() as session, pytest.raises(RunNotFound, match="run not found"):
        service.detect(session, "unknown")


def test_unscorable_stored_run_has_clear_error(database):
    body = sample(key="day35-invalid-stored")
    body["events"][0]["outcome"] = "unknown"
    assert TestClient(app).post("/ingestion/runs", json=body).status_code == 201
    with database() as session, pytest.raises(DetectionServiceError, match="stored run cannot be scored"):
        DetectionService(BUNDLE).detect(session, body["run"]["run_id"])
