"""Reproduce reviewed results and enforce comparability with Day 27."""
import hashlib
import json
from pathlib import Path
import sys

from verify_day27 import compare

ROOT = Path(__file__).resolve().parents[1]


def verify(output):
    for name in ("config", "metrics", "predictions", "feature_review", "feature_importance", "error_review", "training_behavior"):
        compare(json.loads((ROOT / f"data/processed/day29/{name}.json").read_text()),
                json.loads((output / f"{name}.json").read_text()))
    for name, sha in json.loads((output / "checksums.json").read_text()).items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == sha
    previous = ROOT / "data/processed/day27"
    old_config = json.loads((previous / "config.json").read_text())
    config = json.loads((output / "config.json").read_text())
    for key in ("dataset_sha256", "numeric_features", "categorical_features", "sample_weight",
                "seed", "scaler_fit", "run_aggregation", "train_runs", "validation_runs",
                "absent_source_features", "prohibited_inputs", "final_test_evaluated"):
        compare(old_config[key], config[key])
    old_review = json.loads((previous / "feature_review.json").read_text())
    new_review = json.loads((output / "feature_review.json").read_text())
    for key in new_review:
        compare(old_review[key], new_review[key])
    old = json.loads((previous / "predictions.json").read_text())
    new = json.loads((output / "predictions.json").read_text())
    def membership(rows):
        return [{k: r[k] for k in ("run_id", "row_ids", "split", "source_type")} for r in rows]
    compare(membership(old), membership(new))
    print("Day 29 results and model hashes verified; Day 27 split/preprocessing parity confirmed")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
