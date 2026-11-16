import os

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.persistence.core import EventRecord, RunRecord, setup_core_schema
from app.persistence.database import build_engine, session_factory


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = os.getenv("CAPSTONE_TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'ingest.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = build_engine(url)
    setup_core_schema(engine)
    try:
        yield session_factory(engine)
    finally:
        engine.dispose()


def sample(source="auth", key="auth-1", event_id=None):
    scenario, kind, fields = {
        "auth": ("brute_force", "ssh_password", {"username": "fixture", "outcome": "failure"}),
        "web": ("sql_injection", "http_request", {"method": "GET", "status_code": 400}),
        "network": ("reconnaissance", "tcp_connection", {"destination_port": 8080, "protocol": "tcp"}),
    }[source]
    start = "2026-11-06T12:00:00Z"
    return {"source_type": source, "run": {
        "run_id": key, "scenario": scenario, "expected_label": "malicious",
        "start_time": start, "end_time": "2026-11-06T12:01:00Z", "source": "fixture-client",
        "target": "fixture-server", "tool_or_method": "synthetic example", "log_sources": ["fixture.log"],
    }, "events": [{
        "event_id": event_id or f"event-{key}", "run_id": key, "timestamp": start,
        "source_type": source, "event_type": kind, "raw_source_file": "fixture.log",
        "attack_label": "malicious", "scenario": scenario, "source_ip": "192.0.2.1", **fields,
    }]}


def test_ingests_all_three_sources_and_rolls_back_event_conflict(database):
    with TestClient(app) as client:
        for source in ("auth", "web", "network"):
            key = f"day34-{source}"
            body = sample(source, key)
            response = client.post("/ingestion/runs", json=body)
            assert response.status_code == 201, response.text
            assert response.json() == {"run_id": key, "event_count": 1}
            with database() as session:
                run = session.get(RunRecord, key)
                event = session.get(EventRecord, f"event-{key}")
                assert (run.source_type, run.scenario, run.expected_label) == (
                    source, body["run"]["scenario"], "malicious"
                )
                assert (event.run_id, event.raw_source_file, event.attributes["source_ip"]) == (
                    key, "fixture.log", "192.0.2.1"
                )
        assert client.post("/ingestion/runs", json=sample(key="day34-auth")).status_code == 409
        response = client.post("/ingestion/runs", json=sample(key="day34-rollback", event_id="event-day34-auth"))
        assert response.status_code == 409
    with database() as session:
        assert session.get(RunRecord, "day34-rollback") is None


@pytest.mark.parametrize(("key", "value", "message"), [
    ("run_id", "different", "does not match"),
    ("attack_label", "benign", "disagrees"),
    ("timestamp", "2026-11-06T12:00:00", "timezone-aware"),
    ("timestamp", "2026-11-06T12:02:00Z", "run window"),
    ("raw_source_file", "../fixture.log", "undeclared"),
    ("username", None, "required for auth"),
])
def test_inconsistent_event_fails_validation_before_storage(key, value, message, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    body = sample()
    body["events"][0][key] = value
    response = TestClient(app).post("/ingestion/runs", json=body)
    assert response.status_code == 422
    assert message in response.json()["detail"][0]["msg"]


def test_incomplete_event_and_unconfigured_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    client = TestClient(app)
    body = sample()
    assert client.post("/ingestion/runs", json=body).status_code == 503
    del body["events"][0]["event_id"]
    response = client.post("/ingestion/runs", json=body)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "events", 0, "event_id"]
