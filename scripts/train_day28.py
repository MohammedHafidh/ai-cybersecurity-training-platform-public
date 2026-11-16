"""Train the official Random Forest candidate on development evidence only."""
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
import scipy
import sklearn
from app.ml.dataset_v1 import ARCHIVE_SHA, FEATURES, feature_frame, load_development
from app.ml.random_forest_v1 import PARAMETERS, fit_random_forest
from app.detection.auth_baseline import binary_metrics


def build(output):
    splits = load_development(ROOT)
    model = fit_random_forest(splits["train"])
    output.mkdir(parents=True, exist_ok=False)
    joblib.dump(model, output / "pipeline.joblib")
    restored = joblib.load(output / "pipeline.joblib")
    metrics, decisions, errors = {}, [], []
    for split, rows in splits.items():
        frame = feature_frame(rows)
        predicted = restored.predict(frame).tolist()
        np.testing.assert_array_equal(predicted, model.predict(frame))
        runs = []
        for run in sorted({row["run_id"] for row in rows}):
            indexes = [i for i, row in enumerate(rows) if row["run_id"] == run]
            label = "malicious" if any(predicted[i] == "malicious" for i in indexes) else "benign"
            source, truth = rows[indexes[0]]["source_type"], rows[indexes[0]]["attack_label"]
            runs.append((source, truth, label))
            decision = dict(split=split, run_id=run, source_type=source, predicted_label=label,
                            row_ids=[rows[i]["row_id"] for i in indexes])
            decisions.append(decision)
            if label != truth:
                errors.append(dict(**decision, ground_truth=truth,
                    error_type="false_positive" if truth == "benign" else "false_negative",
                    observations=[dict(row_id=rows[i]["row_id"], event_ids=rows[i]["event_ids"],
                        raw_source_files=rows[i]["raw_source_files"],
                        observable_features={name: rows[i][name] for name in FEATURES[source]}) for i in indexes],
                    interpretation={
                        "auth": "Legitimate password retries can overlap failed-login bursts; slow or distributed attacks can resemble normal authentication.",
                        "web": "Benign SQL-like text can share suspicious tokens and error responses with injection; these observables do not establish intent.",
                        "network": "Legitimate multi-service activity can resemble scanning; service logs omit closed-port and SYN-only probes."
                    }[source]))
        metrics[split] = dict(
            observation_metrics=binary_metrics([row["attack_label"] for row in rows], predicted),
            run_metrics=binary_metrics([r[1] for r in runs], [r[2] for r in runs]),
            by_source={source: binary_metrics([r[1] for r in runs if r[0] == source],
                [r[2] for r in runs if r[0] == source]) for source in FEATURES})
    baseline = json.loads((ROOT / "data/processed/day27/config.json").read_text())
    config = {key: value for key, value in baseline.items() if key not in
              {"model", "C", "solver", "max_iter", "source_sha256"}}
    config.update(model="RandomForestClassifier", parameters=PARAMETERS)
    source_paths = ("backend/app/ml/dataset_v1.py", "backend/app/ml/random_forest_v1.py",
                    "scripts/train_day28.py", "requirements/day27.txt")
    config["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in source_paths}
    transform = model.named_steps["features"]
    names = transform.get_feature_names_out().tolist()
    classifier = model.named_steps["classifier"]
    importance = dict(method="training-only mean decrease in impurity",
        features=[dict(feature=name, importance=float(value)) for name, value in
                  zip(names, classifier.feature_importances_)],
        limitations="Correlated counts/rates split importance; source indicators and zero-filled fields can reflect lab structure. Not causal or deployment evidence; no final-test permutation used.")
    values = dict(config=config, metrics=metrics, predictions=decisions, error_review=dict(
        errors=errors, false_negatives=sum(e["error_type"] == "false_negative" for e in errors),
        false_positives=sum(e["error_type"] == "false_positive" for e in errors),
        reviewer="Agent review of development features and trusted labels; no independent teammate sign-off claimed",
        evidence_archive_sha256=ARCHIVE_SHA,
        final_test_evaluated=False), feature_importance=importance,
        feature_review=dict(transformed_names=names,
            scaler_mean=transform.named_transformers_["numeric"].mean_.tolist(),
            transformed_sample=transform.transform(feature_frame(splits["train"][:1]))[0].tolist(),
            input_sample=feature_frame(splits["train"][:1]).iloc[0].to_dict()),
        environment=dict(python=platform.python_version(), sklearn=sklearn.__version__,
            scipy=scipy.__version__, numpy=np.__version__, pandas=pd.__version__, joblib=joblib.__version__))
    for name, value in values.items():
        (output / f"{name}.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
    (output / "checksums.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", newline="\n")
    print(json.dumps(metrics["validation"]["run_metrics"]))
    print(f"Reviewed {len(errors)} development errors; final-test evidence untouched")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
