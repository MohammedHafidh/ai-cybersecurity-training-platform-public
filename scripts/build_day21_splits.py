import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.processing.splits import split_tables, write_splits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    base = ROOT / "data/processed/day20"
    checksums = json.loads((base / "checksums.json").read_text())
    for name, expected in checksums.items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Day 20 input changed: {name}")
    inputs = [base / f"{source}.jsonl" for source in ("auth", "web", "network")]
    tables = {p.stem:[json.loads(line) for line in p.read_text().splitlines()] for p in inputs}
    assignments, report = split_tables(tables)
    write_splits(assignments, report, args.output, inputs)
    print(report["run_counts"])
    print(report["independence_review"]["limitation"])


if __name__ == "__main__":
    main()
