from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import threading
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.training import lab
from app.training.content import SCENARIOS
from app.training.storage import Exercise
from app.training.evidence import projection
from app.ingestion.pipeline import load_run_metadata, normalize_log
from app.ingestion.service import RunIngestionRequest, store_run
from app.detection.routes import process_known_run

CANCELS = {}
LOCK = threading.Lock()


def sample_capture(exercise, scenario, stage):
    """Explicit harmless sample; never used as a live fallback."""
    folder = lab.data_root() / "samples" / exercise
    folder.mkdir(parents=True, exist_ok=False)
    start = lab.utc()
    run_id = "sample-" + exercise
    source = SCENARIOS[scenario]["source"]
    if source == "auth":
        lines = [
            f"{start.isoformat()} fixture sshd[{100+i}]: Failed password for student from 192.0.2.1 port 41000 ssh2"
            for i in range(3)
        ]
    elif source == "web":
        lines = [
            json.dumps(
                dict(
                    event_type="http_request",
                    timestamp=start.isoformat(),
                    source_ip="192.0.2.1",
                    method="GET",
                    path="/users",
                    id_input="select a category",
                    status_code=400,
                    run_id=run_id,
                )
            )
        ]
    else:
        lines = [
            json.dumps(
                dict(
                    event_type="tcp_connection",
                    timestamp=start.isoformat(),
                    source_ip="192.0.2.1",
                    destination_port=p,
                    protocol="tcp",
                    run_id=run_id,
                )
            )
            for p in (8080, 9090)
        ]
    (folder / "capture.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    metadata = dict(
        run_id=run_id,
        scenario="benign",
        expected_label="benign",
        start_time=start.isoformat(),
        end_time=(start + timedelta(seconds=1)).isoformat(),
        source="synthetic learner",
        target="synthetic target",
        tool_or_method="Harmless synthetic demonstration; not an executed attack",
        log_sources=["capture.log"],
    )
    (folder / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    stage("capturing")
    return folder, metadata


def perform(engine, exercise_id, scenario, mode, cancel):
    current = "preparing"

    def stage(name):
        nonlocal current
        if cancel.is_set():
            raise InterruptedError("Exercise cancelled")
        current = name
        with Session(engine) as session, session.begin():
            row = session.get(Exercise, exercise_id)
            row.stage = name
            row.history = [*row.history, {"stage": name, "at": lab.utc().isoformat()}]

    try:
        if mode == "live":
            folder, metadata = lab.capture(exercise_id, scenario, stage, cancel)
        else:
            folder, metadata = sample_capture(exercise_id, scenario, stage)
        stage("normalizing")
        run = load_run_metadata(folder / "metadata.json")
        events = normalize_log(
            folder / "capture.log", run, SCENARIOS[scenario]["source"], source_root=folder
        )
        if not events:
            raise ValueError("No usable event records were captured")
        hashes = {
            p.name: lab.digest(p)
            for p in folder.iterdir()
            if p.name in ("capture.log", "metadata.json", "nmap-scan.txt", "nmap-scan.xml")
        }
        data = RunIngestionRequest.model_validate(
            dict(
                source_type=SCENARIOS[scenario]["source"],
                run=run.model_dump(),
                events=[e.model_dump() for e in events],
            )
        )
        with Session(engine) as session:
            store_run(session, data)
            result = process_known_run(run.run_id, session, progress=stage)
        if hashes != {name: lab.digest(folder / name) for name in hashes}:
            raise ValueError("Original evidence changed during processing")
        safe = projection(events)
        # Do not return raw detector evidence containing addresses; expose typed teaching fields.
        safe.update(
            run_id=run.run_id,
            expected_label=run.expected_label,
            ground_truth_reason=run.tool_or_method,
            hashes=hashes,
            observations=[
                dict(
                    event_ids=o.event_ids,
                    features=o.observed_features,
                    rule=dict(
                        label=o.rule.predicted_label,
                        version=o.rule.rule_version,
                        threshold=o.rule.evidence.get("threshold"),
                        observed=o.rule.evidence.get("observed"),
                        feature=o.rule.evidence.get("feature"),
                    ),
                    ml=dict(
                        label=o.ml.predicted_label,
                        version=o.ml.model_version,
                        probability=o.ml.malicious_probability,
                    ),
                )
                for o in result.result.observations
            ],
            detection_ids=result.detection_ids,
        )
        stage("ready")
        with Session(engine) as session, session.begin():
            row = session.get(Exercise, exercise_id)
            row.status = "ready"
            row.active_slot = None
            row.run_id = run.run_id
            row.result = safe
    except Exception as exc:
        # Diagnostic details stay private and are never reflected into HTTP responses.
        diagnostics = lab.data_root() / "diagnostics"
        diagnostics.mkdir(parents=True, exist_ok=True)
        (diagnostics / (exercise_id + ".txt")).write_text(
            f"{current}: {type(exc).__name__}: {exc}", encoding="utf-8"
        )
        with Session(engine) as session, session.begin():
            row = session.get(Exercise, exercise_id)
            row.status = "cancelled" if isinstance(exc, InterruptedError) else "failed"
            row.active_slot = None
            row.error = f"Exercise {row.status} during {current}. No demonstration was substituted. Check readiness or ask the operator to review diagnostics."
    finally:
        with LOCK:
            CANCELS.pop(exercise_id, None)


def launch(engine, row):
    cancel = threading.Event()
    with LOCK:
        CANCELS[row.id] = cancel
    threading.Thread(
        target=perform,
        args=(engine, row.id, row.scenario, row.mode, cancel),
        daemon=True,
        name="training-" + row.id,
    ).start()


def recover(engine):
    """Called only after the platform acquires its exclusive PostgreSQL instance lock."""
    with Session(engine) as session, session.begin():
        for row in session.scalars(select(Exercise).where(Exercise.active_slot == 1)):
            if row.mode == "live":
                lab.cleanup(row.id)
            row.active_slot = None
            row.status = "failed"
            row.error = "The previous platform session was interrupted. Its owned lab resources were cleaned up; no replay was substituted. Start a new exercise when ready."
