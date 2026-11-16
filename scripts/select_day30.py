"""One predeclared development experiment and practical candidate selection."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import joblib
import numpy as np
from app.ml.dataset_v1 import feature_frame, load_development, make_pipeline
from app.detection.auth_baseline import binary_metrics
from train_day27 import build as logistic
from train_day28 import build as forest
from train_day29 import build as boosting
from verify_day27 import compare


def evaluate(model, splits):
    reports, predictions, errors = {}, [], []
    for split, rows in splits.items():
        predicted = model.predict(feature_frame(rows)).tolist()
        runs = []
        for run in sorted({r["run_id"] for r in rows}):
            indices = [i for i, r in enumerate(rows) if r["run_id"] == run]
            source, truth = rows[indices[0]]["source_type"], rows[indices[0]]["attack_label"]
            label = "malicious" if any(predicted[i] == "malicious" for i in indices) else "benign"
            runs.append((source, truth, label))
            row = dict(split=split, run_id=run, source_type=source, predicted_label=label,
                       row_ids=[rows[i]["row_id"] for i in indices])
            predictions.append(row)
            if label != truth:
                errors.append(dict(**row, ground_truth=truth, event_ids=[e for i in indices for e in rows[i]["event_ids"]]))
        reports[split] = dict(observation_metrics=binary_metrics([r["attack_label"] for r in rows], predicted),
            run_metrics=binary_metrics([r[1] for r in runs], [r[2] for r in runs]),
            by_source={s: binary_metrics([r[1] for r in runs if r[0] == s], [r[2] for r in runs if r[0] == s])
                       for s in ("auth", "web", "network")})
    return reports, predictions, errors


def build(output):
    protocol = json.loads((ROOT / "docs/day30-protocol.json").read_text())
    splits = load_development(ROOT)
    reports, models, predictions = {}, {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, day, builder in (("logistic_regression", 27, logistic), ("random_forest", 28, forest),
                                   ("gradient_boosting", 29, boosting)):
            path = Path(tmp) / name
            builder(path)
            for file in ("metrics", "predictions", "config"):
                compare(json.loads((ROOT / f"data/processed/day{day}/{file}.json").read_text()),
                        json.loads((path / f"{file}.json").read_text()))
            models[name] = joblib.load(path / "pipeline.joblib")
            reports[name], predictions[name], _ = evaluate(models[name], splits)
            compare(json.loads((path / "metrics.json").read_text()), reports[name])
        changed = make_pipeline().set_params(classifier__C=0.1)
        counts = Counter(r["run_id"] for r in splits["train"])
        changed.fit(feature_frame(splits["train"]), [r["attack_label"] for r in splits["train"]],
                    classifier__sample_weight=[1 / counts[r["run_id"]] for r in splits["train"]])
        if changed.named_steps["classifier"].n_iter_.max() >= 1000:
            raise ValueError("Improvement candidate failed to converge")
        name = "logistic_regression_C_0.1"
        models[name] = changed
        reports[name], predictions[name], experiment_errors = evaluate(changed, splits)
        preference = ["logistic_regression", name, "random_forest", "gradient_boosting"]
        def ranking(name):
            m = reports[name]["validation"]["run_metrics"]
            return (-m["f1"], -m["recall"], m["false_positive_rate"], preference.index(name))
        selected = min(preference, key=ranking)
        metrics, selected_predictions, selected_errors = evaluate(models[selected], splits)
        output.mkdir(parents=True, exist_ok=False)
        joblib.dump(models[selected], output / "selected-pipeline.joblib")
        restored = joblib.load(output / "selected-pipeline.joblib")
        np.testing.assert_array_equal(restored.predict(feature_frame(splits["validation"])),
                                      models[selected].predict(feature_frame(splits["validation"])))
        values = dict(comparison=reports,
            improvement=dict(protocol=protocol, before=reports["logistic_regression"], after=reports[name],
                errors=experiment_errors, extra_attempts=0),
            selection=dict(candidate=selected, metrics=metrics, training_runs=18, validation_runs=6,
                rationale="Predeclared validation metric ranking with simplicity tie-break; no test evaluation or combined-data refit",
                final_test_evaluated=False, bounded_rounds=1),
            predictions=selected_predictions,
            security_review=dict(errors=selected_errors,
                interpretation="Benign SQL-like input overlaps token/error indicators. Preserve trusted intent labels. No validation improvement establishes deployment performance; scripted counts, timing and source structure remain risks.",
                reviewer="Agent review and automated development evidence checks; no independent teammate sign-off claimed"))
        source_paths = ["docs/day30-protocol.json", "scripts/select_day30.py", "backend/app/ml/dataset_v1.py",
                        "backend/app/ml/random_forest_v1.py", "backend/app/ml/gradient_boosting_v1.py", "requirements/day27.txt"]
        values["manifest"] = dict(source_sha256={p: hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in source_paths},
            model_sha256=hashlib.sha256((output / "selected-pipeline.joblib").read_bytes()).hexdigest(),
            dataset_sha256=json.loads((ROOT / "data/processed/day27/config.json").read_text())["dataset_sha256"])
        for name, value in values.items():
            (output / f"{name}.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        lines = ["# Day 30 development model comparison", "", "| Candidate | Accuracy | Precision | Recall | F1 | FPR | Confusion matrix |", "|---|---:|---:|---:|---:|---:|---|"]
        for name, report in reports.items():
            m = report["validation"]["run_metrics"]
            lines.append(f"| {name} | {m['accuracy']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['false_positive_rate']:.4f} | {m['confusion_matrix']} |")
        lines += ["", f"Selected: {selected}. Matrices use benign/malicious order; six validation runs only.", "",
                  "One predeclared C=0.1 experiment only. Final-test evidence remains sealed until Day 32.", ""]
        (output / "comparison.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"Selected {selected}; one bounded experiment; final evidence sealed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
