"""Rebuild the official Day 27 baseline; no model selection or final evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import joblib
import numpy as np
import pandas as pd
import sklearn
import scipy
from app.ml.dataset_v1 import ARCHIVE_SHA, FEATURES, NUMERIC, SEED, feature_frame, fit_baseline, load_development
from app.detection.auth_baseline import binary_metrics


def build(output):
    splits = load_development(ROOT)
    pipeline = fit_baseline(splits["train"])
    output.mkdir(parents=True, exist_ok=False)
    joblib.dump(pipeline, output / "pipeline.joblib")
    restored = joblib.load(output / "pipeline.joblib")
    report, decisions = {}, []
    for split, rows in splits.items():
        frame = feature_frame(rows)
        predicted = restored.predict(frame).tolist()
        if not np.array_equal(predicted, pipeline.predict(frame)):
            raise ValueError("persisted pipeline changed predictions")
        runs = []
        for run in sorted({r["run_id"] for r in rows}):
            indexes = [i for i, r in enumerate(rows) if r["run_id"] == run]
            label = "malicious" if any(predicted[i] == "malicious" for i in indexes) else "benign"
            runs.append((rows[indexes[0]]["source_type"], rows[indexes[0]]["attack_label"], label))
            decisions.append(dict(split=split, run_id=run, source_type=runs[-1][0],
                                  predicted_label=label, row_ids=[rows[i]["row_id"] for i in indexes]))
        report[split] = dict(
            observation_metrics=binary_metrics([r["attack_label"] for r in rows], predicted),
            run_metrics=binary_metrics([r[1] for r in runs], [r[2] for r in runs]),
            by_source={s: binary_metrics([r[1] for r in runs if r[0] == s],
                                        [r[2] for r in runs if r[0] == s]) for s in FEATURES})
    train = feature_frame(splits["train"])
    transform = pipeline.named_steps["features"]
    values = dict(
        config=dict(model="LogisticRegression", seed=SEED, C=1.0, solver="lbfgs", max_iter=1000,
                    sample_weight="inverse observation count per run", threshold="sklearn predict default",
                    train_runs=18, validation_runs=6, dataset_sha256=ARCHIVE_SHA,
                    numeric_features=NUMERIC, categorical_features=["source_type"],
                    absent_source_features="zero; applicable missing values fail closed",
                    scaler_fit="training observations only", run_aggregation="any malicious observation",
                    prohibited_inputs=["attack_label", "scenario", "run_id", "row_id", "event_ids",
                                       "raw_source_files", "source_ip", "target", "timestamps", "split"],
                    final_test_evaluated=False),
        metrics=report, predictions=decisions,
        feature_review=dict(transformed_names=transform.get_feature_names_out().tolist(),
                            input_sample=train.iloc[0].to_dict(),
                            transformed_sample=transform.transform(train.iloc[:1])[0].tolist(),
                            scaler_mean=transform.named_transformers_["numeric"].mean_.tolist(),
                            review="Agent audit: allowlisted observable counts/rates, no identity or label inputs; no independent human sign-off",
                            limitations="Token heuristics, accepted-connection visibility, tiny scripted sample and lab-specific source correlations remain"),
        environment=dict(python=platform.python_version(), sklearn=sklearn.__version__, scipy=scipy.__version__,
                         numpy=np.__version__, pandas=pd.__version__, joblib=joblib.__version__),
    )
    values["config"]["source_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in ("backend/app/ml/dataset_v1.py", "scripts/train_day27.py", "requirements/day27.txt")}
    for name, value in values.items():
        (output / f"{name}.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8", newline="\n")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
    (output / "checksums.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", newline="\n")
    print(json.dumps(report["validation"]["run_metrics"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
