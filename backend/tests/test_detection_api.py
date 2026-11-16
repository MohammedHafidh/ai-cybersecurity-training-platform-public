from fastapi.testclient import TestClient

from app.detection import routes
from app.detection.service import DetectionServiceError
from app.main import app
from test_ingestion_api import database, sample


def test_ingest_process_list_and_read(database):
    with TestClient(app) as client:
        body = sample("network", "day36-network")
        first = body["events"][0]
        body["events"].append(dict(first, event_id="day36-second", destination_port=8081))
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/health/database").status_code == 200
        assert client.post("/ingestion/runs", json=body).status_code == 201
        response = client.post("/runs/day36-network/process")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["result"]["ground_truth"]["expected_label"] == "malicious"
        observation, = payload["result"]["observations"]
        assert observation["rule"]["triggered"] is True
        assert observation["ml"]["model_version"] == "capstone-ml-v1"
        ids = payload["detection_ids"]
        assert len(set(ids)) == 2
        assert client.post("/runs/day36-network/process").json()["detection_ids"] == ids

        events = client.get("/events?limit=1").json()
        assert len(events) == 1
        assert events[0]["timestamp"].endswith("Z")
        assert events[0]["raw_source_file"] == "fixture.log"
        listed = [d for d in client.get("/detections").json() if d["run_id"] == "day36-network"]
        assert {d["detection_id"] for d in listed} == set(ids)
        assert {d["detector"] for d in listed} == {"rule", "ml"}
        for summary in listed:
            detail = client.get(f"/detections/{summary['detection_id']}").json()
            assert detail["event_id"] is None
            assert set(detail["evidence"]["event_ids"]) == {first["event_id"], "day36-second"}
            assert "expected_label" not in detail["evidence"]
            if detail["detector"] == "rule":
                assert detail["evidence"]["rule"]["observed"] == 2
            else:
                assert 0 <= detail["evidence"]["malicious_probability"] <= 1


def test_error_responses_and_openapi(database, monkeypatch):
    with TestClient(app) as client:
        assert client.post("/runs/no-such-run/process").status_code == 404
        assert client.get("/detections/no-such-detection").status_code == 404
        assert client.get("/events?limit=101").status_code == 422
        assert client.get("/detections?limit=0").status_code == 422
        body = sample(key="day36-invalid-evidence")
        body["events"][0]["outcome"] = "unknown"
        assert client.post("/ingestion/runs", json=body).status_code == 201
        assert client.post("/runs/day36-invalid-evidence/process").status_code == 422
        assert all(row["run_id"] != "day36-invalid-evidence" for row in client.get("/detections").json())
        paths = client.get("/openapi.json").json()["paths"]
        assert {"/health", "/health/database", "/ingestion/runs", "/runs/{run_id}/process",
                "/events", "/detections", "/detections/{detection_id}"} <= paths.keys()
        assert client.get("/docs").status_code == 200
    monkeypatch.delenv("DATABASE_URL")
    with TestClient(app) as client:
        assert client.get("/events").status_code == 503


def test_processing_reports_unavailable_model(database, monkeypatch):
    def unavailable():
        raise DetectionServiceError("frozen ML bundle unavailable or invalid")

    monkeypatch.setattr(routes, "detection_service", unavailable)
    with TestClient(app) as client:
        assert client.post("/ingestion/runs", json=sample(key="day36-model-error")).status_code == 201
        assert client.post("/runs/day36-model-error/process").status_code == 503
        assert all(row["run_id"] != "day36-model-error" for row in client.get("/detections").json())
