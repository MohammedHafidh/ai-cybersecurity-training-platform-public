"""Normalize recorded network evidence or synthetic connection log records."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from auth_browser_capture import normalize, private_capture


def synthetic_capture():
    run_id = f"day51-network-{uuid4().hex}"
    timestamps = [f"2026-01-01T12:00:0{second}Z" for second in (1, 3, 5)]
    with TemporaryDirectory() as directory:
        root = Path(directory)
        log = root / "network.jsonl"
        log.write_text("".join(json.dumps({
            "event_type": "tcp_connection", "timestamp": timestamp, "run_id": run_id,
            "source_ip": "192.0.2.51", "destination_port": port, "protocol": "tcp",
        }) + "\n" for timestamp, port in zip(timestamps, (8080, 8081, 8081), strict=True)), encoding="utf-8")
        metadata = root / "metadata.json"
        metadata.write_text(json.dumps({
            "run_id": run_id, "scenario": "reconnaissance", "expected_label": "malicious",
            "start_time": timestamps[0], "end_time": timestamps[-1], "source": "fixture-client",
            "target": "fixture-target", "tool_or_method": "synthetic raw connection records",
            "log_sources": [log.name],
        }), encoding="utf-8")
        return normalize(log, metadata, "network")


if __name__ == "__main__":
    print(json.dumps(private_capture("network") if os.getenv("CAPSTONE_NETWORK_LOG") else synthetic_capture()))
