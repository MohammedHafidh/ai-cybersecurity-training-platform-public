"""Normalize recorded web evidence or a harmless synthetic log for browser tests."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from auth_browser_capture import normalize, private_capture


def synthetic_capture():
    run_id = f"day50-web-{uuid4().hex}"
    timestamp = "2026-01-01T12:00:00Z"
    with TemporaryDirectory() as directory:
        root = Path(directory)
        log = root / "web.jsonl"
        log.write_text(json.dumps({
            "event_type": "http_request", "timestamp": timestamp, "run_id": run_id,
            "source_ip": "192.0.2.50", "method": "GET", "path": "/fixture",
            "status_code": 400, "raw_query": "id=select+a+category",
        }) + "\n", encoding="utf-8")
        metadata = root / "metadata.json"
        metadata.write_text(json.dumps({
            "run_id": run_id, "scenario": "sql_injection", "expected_label": "malicious",
            "start_time": timestamp, "end_time": timestamp, "source": "fixture-client",
            "target": "fixture-target", "tool_or_method": "synthetic raw log regression",
            "log_sources": [log.name],
        }), encoding="utf-8")
        capture = normalize(log, metadata, "web")
        assert capture["events"][0]["request_data"] == "select a category"
        return capture


if __name__ == "__main__":
    print(json.dumps(private_capture("web") if os.getenv("CAPSTONE_WEB_LOG") else synthetic_capture()))
