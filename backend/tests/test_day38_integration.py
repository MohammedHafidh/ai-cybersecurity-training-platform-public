"""Exercise the backend with one fresh, benign loopback connection."""
import hashlib

from fastapi.testclient import TestClient

from app.main import app
from loopback_capture import capture_loopback
from test_ingestion_api import database


def test_fresh_benign_connection_through_persistent_detection_history(database, tmp_path):
    run, event, log, raw_hash = capture_loopback(tmp_path)
    run_id = run.run_id
    with TestClient(app) as client:
        ingested = client.post("/ingestion/runs", json={
            "source_type": "network",
            "run": run.model_dump(mode="json"),
            "events": [event.model_dump(mode="json")],
        })
        assert ingested.status_code == 201, ingested.text
        processed = client.post(f"/runs/{run_id}/process")
        assert processed.status_code == 200, processed.text
        result = processed.json()["result"]
        observation, = result["observations"]
        assert result["ground_truth"] == {"scenario": "benign", "expected_label": "benign"}
        assert observation["observed_features"]["connection_count"] == 1
        assert observation["observed_features"]["unique_destination_port_count"] == 1
        assert observation["rule"]["predicted_label"] == "benign"
        assert observation["rule"]["evidence"]["observed"] == 1
        assert observation["ml"]["model_version"] == "capstone-ml-v1"
        ids = processed.json()["detection_ids"]
        assert len(set(ids)) == 2

    with TestClient(app) as client:
        detectors = set()
        for detection_id in ids:
            fetched = client.get(f"/detections/{detection_id}")
            assert fetched.status_code == 200, fetched.text
            record = fetched.json()
            detector = record["detector"]
            detectors.add(detector)
            assert record["run_id"] == run_id
            assert record["event_id"] == event.event_id
            assert record["evidence"]["event_ids"] == [event.event_id]
            assert record["evidence"]["raw_source_files"] == run.log_sources
            assert record["predicted_label"] == observation[detector]["predicted_label"]
        assert detectors == {"rule", "ml"}
    assert hashlib.sha256(log.read_bytes()).digest() == raw_hash
