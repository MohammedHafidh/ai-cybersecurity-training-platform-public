"""Capture and normalize one ordinary TCP connection for integration tests."""
from datetime import datetime, timezone
import hashlib
import json
import socket
from uuid import uuid4

from app.ingestion.pipeline import load_run_metadata, normalize_log


def capture_loopback(tmp_path):
    run_id = f"loopback-benign-{uuid4().hex}"
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
        "log_sources": [f"{tmp_path.name}/{log.name}"],
    }), encoding="utf-8-sig")
    raw_hash = hashlib.sha256(log.read_bytes()).digest()
    run = load_run_metadata(metadata)
    event, = normalize_log(log, run, "network", source_root=tmp_path.parent)
    assert event.destination_port == port
    assert event.source_ip == peer[0]

    return run, event, log, raw_hash
