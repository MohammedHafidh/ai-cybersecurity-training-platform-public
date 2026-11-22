from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
from uuid import uuid4
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.training import lab, worker
from app.training.storage import Exercise, setup_training
from app.persistence.database import build_engine


def test_single_active_slot_and_interrupted_capture_recovery(tmp_path, monkeypatch):
    engine = build_engine(f'sqlite:///{tmp_path / "jobs.db"}')
    from app.persistence.core import setup_core_schema

    setup_core_schema(engine)
    setup_training(engine)
    key = uuid4().hex
    with Session(engine) as s, s.begin():
        s.add(
            Exercise(
                id=key,
                scenario="brute-force",
                mode="live",
                active_slot=1,
                status="running",
                stage="activity",
                history=[],
                result={},
                error="",
            )
        )
    with pytest.raises(IntegrityError):
        with Session(engine) as s, s.begin():
            s.add(
                Exercise(
                    id=uuid4().hex,
                    scenario="sql-injection",
                    mode="live",
                    active_slot=1,
                    status="running",
                    stage="preparing",
                    history=[],
                    result={},
                    error="",
                )
            )
    calls = []
    monkeypatch.setattr(lab, "cleanup", calls.append)
    worker.recover(engine)
    with Session(engine) as s:
        row = s.get(Exercise, key)
        assert row.status == "failed" and row.active_slot is None
        assert "interrupted" in row.error
    assert calls == [key]
    engine.dispose()


def test_changed_private_bundle_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "lab"
    root.mkdir()
    script = root / "approved.sh"
    script.write_bytes(b"approved")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": {"approved.sh": lab.digest(script)}}))
    (tmp_path / "operator.json").write_text(json.dumps({"lab_root": str(root)}))
    monkeypatch.setattr(lab, "data_root", lambda: tmp_path)
    monkeypatch.setattr(lab, "MANIFEST", manifest)
    lab.verified_bundle()
    script.write_bytes(b"changed")
    with pytest.raises(ValueError):
        lab.verified_bundle()


def test_child_execution_timeout_and_cancel_are_bounded():
    with pytest.raises(TimeoutError):
        lab.command([sys.executable, "-c", "import time;time.sleep(10)"], timeout=0.1)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(InterruptedError):
        lab.command([sys.executable, "-c", "import time;time.sleep(10)"], cancel=cancel)


def test_large_output_is_rejected():
    with pytest.raises(ValueError):
        lab.command([sys.executable, "-c", 'print("x"*2100000)'])
