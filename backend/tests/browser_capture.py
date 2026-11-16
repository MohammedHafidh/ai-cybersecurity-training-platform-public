"""Print a normalized ingestion request for a fresh benign loopback capture."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from loopback_capture import capture_loopback


if __name__ == "__main__":
    with TemporaryDirectory(prefix="browser-smoke-") as directory:
        run, event, log, raw_hash = capture_loopback(Path(directory))
        assert hashlib.sha256(log.read_bytes()).digest() == raw_hash
        print(json.dumps({
            "source_type": "network",
            "run": run.model_dump(mode="json"),
            "events": [event.model_dump(mode="json")],
        }))
