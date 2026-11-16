"""Rebuild the quality/provenance outputs from retained immutable raw bytes."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ingestion.corpus import audit_corpus


def main():
    archive = ROOT / "data/raw-corpus-v0.1/raw-corpus-v0.1.tar.gz"
    expected = "e35bfe2e7d5d4bc2638ed31dc0d830db57e35a0def8578277586d334d9b096b9"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError("frozen archive checksum mismatch")
    with tempfile.TemporaryDirectory() as directory:
        with tarfile.open(archive) as source:
            source.extractall(directory, filter="data")
        base = Path(directory) / "raw-corpus-v0.1"
        events, ledger, report, snapshot = audit_corpus(base / "manifest.json")
        for name, actual in (("provenance-manifest.json", snapshot), ("exclusion-ledger.json", ledger), ("corpus-quality-report.json", report)):
            if json.loads((base / "freeze" / name).read_text()) != actual:
                raise ValueError(f"frozen {name} differs from rebuilt output")
        frozen = [json.loads(line) for line in (base / "freeze/normalized-events.jsonl").read_text().splitlines()]
        if frozen != [event.model_dump(mode="json") for event in events]:
            raise ValueError("normalized output differs from frozen evidence")
        print(f"raw corpus v0.1 verified: {len(snapshot['runs'])} runs, {len(events)} observations")


if __name__ == "__main__":
    main()
