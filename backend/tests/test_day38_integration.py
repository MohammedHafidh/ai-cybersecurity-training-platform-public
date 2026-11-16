"""Exercise the backend with one fresh, benign loopback connection."""
from datetime import datetime, timezone
import hashlib
import json
import socket
from uuid import uuid4

from fastapi.testclient import TestClient

from app.ingestion.pipeline import load_run_metadata, normalize_log
from app.main import app
from test_ingestion_api import database


def test_fresh_benign_connection_through_persistent_detection_history(database, tmp_path):
    run_id = f"day38-benign-{uuid4().hex}"
    log = tmp_path / "loopback.log"
    metadata = tmp_path / "run.json"

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(3)
        host, port = listener.getsockname()
        start = datetime.now(timezone.utc)
        with socket.create_connection((host, port), timeout=3) as sender:
            connection, peer = listener.accept()
            with connection:
                observed_at = datetime.now(timezone.utc)
                assert sender.getsockname() == peer
        end = datetime.now(timezone.utc)

    log.write_text(json.dumps({
        "event_type": "tcp_connection",
        "timestamp": observed_at.isoformat(),
        "source_ip": peer[0],
        "destination_port": port,
        "protocol": "tcp",
        "run_id": run_id,
    }) + "\n", encoding="utf-8")
    metadata.write_text(json.dumps({
        "run_id": run_id,
        "scenario": "benign",
        "expected_label": "benign",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "source": "loopback-client",
        "target": "loopback-listener",
        "tool_or_method": "single ordinary TCP connection",
        "log_sources": [log.name],
    }), encoding="utf-8")
    raw_hash = hashlib.sha256(log.read_bytes()).digest()
    run = load_run_metadata(metadata)
    event, = normalize_log(log, run, "network")
    assert event.destination_port == port
    assert event.source_ip == peer[0]

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
            assert record["evidence"]["raw_source_files"] == [log.name]
            assert record["predicted_label"] == observation[detector]["predicted_label"]
        assert detectors == {"rule", "ml"}
    assert hashlib.sha256(log.read_bytes()).digest() == raw_hash
