"""Normalize existing auth evidence for browser integration tests."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.ingestion.pipeline import load_run_metadata, normalize_log


def normalize(log, metadata):
    run = load_run_metadata(metadata)
    declared, = run.log_sources
    root = log.resolve().parents[len(declared.split("/")) - 1]
    events = normalize_log(log, run, "auth", source_root=root)
    if run.scenario != "brute_force" or run.expected_label != "malicious" or not events:
        raise ValueError("expected a labeled brute-force capture with normalized events")
    return {"source_type": "auth", "run": run.model_dump(mode="json"),
            "events": [event.model_dump(mode="json") for event in events]}


def evidence_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_capture():
    log = Path(os.environ["CAPSTONE_AUTH_LOG"])
    metadata = Path(os.environ["CAPSTONE_AUTH_METADATA"])
    expected = (os.environ["CAPSTONE_AUTH_LOG_SHA256"].lower(),
                os.environ["CAPSTONE_AUTH_METADATA_SHA256"].lower())
    if (evidence_hash(log), evidence_hash(metadata)) != expected:
        raise ValueError("private evidence hashes differ from the approved manifest")
    result = normalize(log, metadata)
    if (evidence_hash(log), evidence_hash(metadata)) != expected:
        raise ValueError("private evidence changed during normalization")
    return result


def synthetic_capture():
    run_id = f"day49-auth-{uuid4().hex}"
    start = "2026-01-01T12:00:00Z"
    end = "2026-01-01T12:00:02Z"
    with TemporaryDirectory() as directory:
        root = Path(directory)
        log = root / "fixture.log"
        log.write_text("".join(
            f"fixture-target | 2026-01-01T12:00:0{i}Z fixture-target sshd[{i+101}]: "
            "Failed password for fixture from 192.0.2.49 port 41001 ssh2\n"
            for i in range(3)
        ), encoding="utf-8")
        metadata = root / "metadata.json"
        metadata.write_text(json.dumps({
            "run_id": run_id, "scenario": "brute_force", "expected_label": "malicious",
            "start_time": start, "end_time": end, "source": "fixture-client", "target": "fixture-target",
            "tool_or_method": "synthetic raw log regression", "log_sources": [log.name],
        }), encoding="utf-8")
        return normalize(log, metadata)


if __name__ == "__main__":
    print(json.dumps(private_capture() if os.getenv("CAPSTONE_AUTH_LOG") else synthetic_capture()))
