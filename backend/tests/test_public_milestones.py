"""Check published milestone evidence without relying on private archives."""
import json
from pathlib import Path

from app.detection.auth_baseline import binary_metrics
from app.ml.dataset_v1 import FEATURES
from app.ml.frozen_v1 import load_pipeline, predict_observations

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


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
