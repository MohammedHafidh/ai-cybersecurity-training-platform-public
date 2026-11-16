import argparse
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from verify_frozen_corpus import main as verify_snapshot
from app.ingestion.corpus import audit_corpus
from app.ingestion.pipeline import load_run_metadata
from app.processing.modeling import build_modeling_tables, write_modeling_outputs
import json


def main():
    parser = argparse.ArgumentParser(description="Build official Day 20 modeling tables from frozen raw corpus v0.1")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify_snapshot()
    with tempfile.TemporaryDirectory() as directory:
        with tarfile.open(ROOT / "data/raw-corpus-v0.1/raw-corpus-v0.1.tar.gz") as archive:
            archive.extractall(directory, filter="data")
        base = Path(directory) / "raw-corpus-v0.1"
        events, _, _, _ = audit_corpus(base / "manifest.json")
        metadata = {}
        for entry in json.loads((base / "manifest.json").read_text())["runs"]:
            run = load_run_metadata(base / entry["metadata"])
            metadata[run.run_id] = run
        tables = build_modeling_tables(events, metadata)
        write_modeling_outputs(tables, args.output)
        print({source: len(rows) for source, rows in tables.items()})


if __name__ == "__main__":
    main()
