"""Check published milestone evidence without relying on private archives."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import pytest

from app.detection.auth_baseline import binary_metrics
from app.ml.dataset_v1 import FEATURES, feature_frame, fit_baseline, make_pipeline
from app.ml.frozen_v1 import load_pipeline, predict_observations
from app.ml.gradient_boosting_v1 import fit_gradient_boosting
from app.ml.random_forest_v1 import fit_random_forest
from app.processing.splits import split_tables

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from select_day30 import evaluate


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_public_development_manifest_and_candidate_replay():
    base = ROOT / "data/processed/day20"
    checksums = read("data/processed/day20/checksums.json")
    for name, digest in checksums.items():
        assert hashlib.sha256((base / name).read_bytes()).hexdigest() == digest
    tables = {source: [json.loads(line) for line in (base / f"{source}.jsonl")
        .read_text(encoding="utf-8").splitlines()] for source in FEATURES}
    assignments, report = split_tables(tables)
    assert dict(report, input_sha256={f"{s}.jsonl": checksums[f"{s}.jsonl"] for s in FEATURES}) == read(
        "data/processed/day21/split-report.json"
    )
    by_id = {row["row_id"]: row for rows in tables.values() for row in rows}
    splits = {}
    for split in ("train", "validation", "test"):
        expected = read(f"data/processed/day21/{split}.json")
        assert [row for row in assignments if row["split"] == split] == expected
        if split != "test":
            splits[split] = [by_id[key] for run in expected for key in run["row_ids"]]
    train = splits["train"]
    counts = Counter(row["run_id"] for row in train)
    bounded = make_pipeline().set_params(classifier__C=0.1)
    bounded.fit(feature_frame(train), [row["attack_label"] for row in train],
                classifier__sample_weight=[1 / counts[row["run_id"]] for row in train])
    reference = read("data/processed/day30/comparison.json")
    for name, model in (
        ("logistic_regression", fit_baseline(train)),
        ("random_forest", fit_random_forest(train)),
        ("gradient_boosting", fit_gradient_boosting(train)),
        ("logistic_regression_C_0.1", bounded),
    ):
        metrics, _, _ = evaluate(model, splits)
        assert metrics == reference[name]


def test_public_frozen_model_rejects_metadata_and_corrupted_bytes(tmp_path):
    bundle = ROOT / "data/releases/capstone-ml-v1"
    model = load_pipeline(bundle)
    with pytest.raises(ValueError, match="observable fields"):
        predict_observations(model, [{"source_type": "auth", "attack_label": "benign"}])
    (tmp_path / "metadata.json").write_bytes((bundle / "metadata.json").read_bytes())
    (tmp_path / "pipeline.joblib").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_pipeline(tmp_path)


def test_day30_selection_and_day31_frozen_inference():
    selection = read("data/processed/day30/selection.json")
    candidates = read("data/processed/day30/comparison.json")
    preference = ["logistic_regression", "logistic_regression_C_0.1", "random_forest", "gradient_boosting"]

    def rank(name):
        m = candidates[name]["validation"]["run_metrics"]
        return -m["f1"], -m["recall"], m["false_positive_rate"], preference.index(name)

    assert selection["candidate"] == min(preference, key=rank) == "logistic_regression"
    assert selection["metrics"] == candidates[selection["candidate"]]
    bundle = ROOT / "data/releases/capstone-ml-v1"
    assert read("data/releases/capstone-ml-v1/metadata.json")["candidate"] == selection["candidate"]
    pipeline = load_pipeline(bundle)
    tables = {}
    for source in FEATURES:
        path = ROOT / f"data/processed/day20/{source}.jsonl"
        tables[source] = {row["row_id"]: row for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())}
    reference = read("data/processed/day30/predictions.json")
    for split in ("train", "validation"):
        expected = {r["run_id"]: r["predicted_label"] for r in reference if r["split"] == split}
        decisions, labels = {}, []
        for run in read(f"data/processed/day21/{split}.json"):
            source = run["source_type"]
            rows = [tables[source][key] for key in run["row_ids"]]
            inputs = [{k: r[k] for k in ("source_type", *FEATURES[source])} for r in rows]
            labels.append(run["attack_label"])
            results = predict_observations(pipeline, inputs)
            decisions[run["run_id"]] = "malicious" if any(
                r["predicted_label"] == "malicious" for r in results
            ) else "benign"
        assert decisions == expected
        assert binary_metrics(labels, list(decisions.values())) == selection["metrics"][split]["run_metrics"]


def test_day32_public_summary_is_internally_consistent():
    report = read("data/processed/day32/evaluation.json")
    assert set(report["metrics"]) == {"rule", "ml"}
    for detector in report["metrics"].values():
        assert set(detector) == {"overall", "auth", "web", "network"}
        for group in detector.values():
            (tn, fp), (fn, tp) = group["confusion_matrix"]
            truth = ["benign"] * (tn + fp) + ["malicious"] * (fn + tp)
            predictions = ["benign"] * tn + ["malicious"] * fp + ["benign"] * fn + ["malicious"] * tp
            assert binary_metrics(truth, predictions) == group
        pooled = [[sum(detector[s]["confusion_matrix"][i][j] for s in FEATURES)
                   for j in range(2)] for i in range(2)]
        assert pooled == detector["overall"]["confusion_matrix"]
        assert detector["overall"]["sample_count"] == 12
