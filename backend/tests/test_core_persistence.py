import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.persistence.core import DetectionRecord, EventRecord, RunRecord, setup_core_schema
from app.persistence.database import build_engine, session_factory


def test_core_round_trip_and_foreign_keys(tmp_path, monkeypatch):
    url = os.getenv("CAPSTONE_TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'core.db'}"
    engine = build_engine(url)
    monkeypatch.setenv("DATABASE_URL", url)
    try:
        setup_core_schema(engine)
        setup_core_schema(engine)
        assert TestClient(app).get("/health/database").json() == {"status": "ok"}
        now = datetime.now(timezone.utc)
        sessions = session_factory(engine)
        with sessions.begin() as session:
            for run in ("one", "two"):
                session.add(RunRecord(run_id=run, source_type="auth", scenario="benign",
                    expected_label="benign", start_time=now, end_time=now,
                    source="fixture-client", target="fixture-server"))
            session.flush()
            session.add(EventRecord(event_id="event", run_id="one", source_type="auth",
                timestamp=now, event_type="login", raw_source_file="fixture.log", attributes={"outcome": "success"}))
            session.flush()
            session.add(DetectionRecord(detection_id="valid", run_id="one", event_id="event",
                detector="rule", detector_version="v1", predicted_label="benign", created_at=now, evidence={}))
        with sessions() as session:
            assert session.get(RunRecord, "one").scenario == "benign"
            assert session.get(EventRecord, "event").raw_source_file == "fixture.log"
            assert session.get(DetectionRecord, "valid").detector_version == "v1"
        with pytest.raises(IntegrityError), sessions.begin() as session:
            session.add(DetectionRecord(detection_id="wrong-run", run_id="two", event_id="event",
                detector="rule", detector_version="v1", predicted_label="benign", created_at=now, evidence={}))
    finally:
        engine.dispose()


def test_readiness_requires_installed_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")
    assert TestClient(app).get("/health/database").status_code == 503
