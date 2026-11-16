"""Check rebuilt results semantically across supported platforms."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def compare(expected, actual):
    if isinstance(expected, dict):
        assert expected.keys() == actual.keys()
        for key in expected:
            compare(expected[key], actual[key])
    elif isinstance(expected, list):
        assert len(expected) == len(actual)
        for a, b in zip(expected, actual):
            compare(a, b)
    elif isinstance(expected, float):
        np.testing.assert_allclose(actual, expected, rtol=1e-8, atol=1e-8)
    else:
        assert expected == actual, (expected, actual)


if __name__ == "__main__":
    output = Path(sys.argv[1])
    for name in ("config", "metrics", "predictions", "feature_review"):
        compare(json.loads((ROOT / f"data/processed/day27/{name}.json").read_text()),
                json.loads((output / f"{name}.json").read_text()))
    for name, sha in json.loads((output / "checksums.json").read_text()).items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == sha
    print("Day 27 results reproduced; artifact hashes verified")
