import hashlib
import json
from pathlib import Path
import sys
from verify_day27 import compare

ROOT = Path(__file__).resolve().parents[1]


def verify(output):
    for name in ("comparison", "improvement", "selection", "predictions", "security_review"):
        compare(json.loads((ROOT / f"data/processed/day30/{name}.json").read_text()),
                json.loads((output / f"{name}.json").read_text()))
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["model_sha256"] == hashlib.sha256((output / "selected-pipeline.joblib").read_bytes()).hexdigest()
    reference = json.loads((ROOT / "data/processed/day30/manifest.json").read_text())
    compare(reference["source_sha256"], manifest["source_sha256"])
    compare(reference["dataset_sha256"], manifest["dataset_sha256"])
    assert (ROOT / "data/processed/day30/comparison.md").read_text() == (output / "comparison.md").read_text()
    print("Day 30 comparison, bounded experiment, selection and model hash verified")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
