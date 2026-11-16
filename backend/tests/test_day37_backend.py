import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.detection import evaluation
from app.main import app
from test_ingestion_api import database, sample

ROOT = Path(__file__).resolve().parents[2]


def test_history_survives_shutdown_and_restart(database):
    with TestClient(app) as client:
        engine = app.state.database_engine
        assert client.post("/ingestion/runs", json=sample(key="day37-history")).status_code == 201
        response = client.post("/runs/day37-history/process")
        assert response.status_code == 200, response.text
        assert app.state.database_engine is engine
        result = response.json()
        assert result["result"]["ground_truth"]["expected_label"] == "malicious"
        assert result["result"]["rule_label"] == "benign"
        ids = result["detection_ids"]
        dispose = patch.object(engine, "dispose", wraps=engine.dispose)
        spy = dispose.start()
    try:
        spy.assert_called_once()
    finally:
        dispose.stop()
    assert app.state.database_engine is None
    with TestClient(app) as client:
        assert app.state.database_engine is not engine
        for key in ids:
            response = client.get(f"/detections/{key}")
            assert response.status_code == 200
            detail = response.json()
            assert detail["run_id"] == "day37-history"
            assert "expected_label" not in detail["evidence"]


def test_evaluation_reads_only_the_frozen_report(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    path = ROOT / "data/processed/day32/evaluation.json"
    with TestClient(app) as client:
        assert client.get("/evaluation/summary").json() == json.loads(path.read_text())
        missing = tmp_path / "missing.json"
        monkeypatch.setattr(evaluation, "ARTIFACT", missing)
        assert client.get("/evaluation/summary").status_code == 503
        missing.write_text("{}")
        assert client.get("/evaluation/summary").status_code == 503


def test_cors_preflight_only_allows_frontend_and_supported_methods():
    client = TestClient(app)
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
               "Access-Control-Request-Headers": "content-type"}
    permitted = client.options("/ingestion/runs", headers=headers)
    assert permitted.status_code == 200
    assert permitted.headers["access-control-allow-origin"] == headers["Origin"]
    assert "access-control-allow-credentials" not in permitted.headers
    foreign = client.options("/ingestion/runs", headers={**headers, "Origin": "https://other.example"})
    assert foreign.status_code == 400
    assert "access-control-allow-origin" not in foreign.headers
    unsupported = client.options("/ingestion/runs", headers={**headers, "Access-Control-Request-Method": "DELETE"})
    assert unsupported.status_code == 400


def test_missing_fields_and_invalid_scenarios_do_not_echo_values():
    client = TestClient(app)
    body = sample()
    marker = "example-private-value"
    body["run"]["scenario"] = marker
    del body["events"][0]["event_id"]
    response = client.post("/ingestion/runs", json=body)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert {tuple(error["loc"]) for error in errors} == {
        ("body", "run", "scenario"), ("body", "events", 0, "event_id"),
    }
    assert marker not in response.text
