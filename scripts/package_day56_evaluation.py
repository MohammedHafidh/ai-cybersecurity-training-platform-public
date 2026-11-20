"""Present frozen held-out results without rerunning or fitting detectors."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/processed/day56"
SCOPES = ("overall", "auth", "web", "network")
METRICS = ("accuracy", "precision", "recall", "f1", "false_positive_rate")


def package():
    source = ROOT / "data/processed/day32/evaluation.json"
    report = json.loads(source.read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "data/releases/capstone-ml-v1/metadata.json").read_text(encoding="utf-8"))
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("detector", "scope", "sample_count", *METRICS, "tn", "fp", "fn", "tp"))
    table = ["# Frozen held-out evaluation", "",
             "| Detector | Scope | Runs | Accuracy | Precision | Recall | F1 | FPR | TN | FP | FN | TP |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for detector in ("rule", "ml"):
        for scope in SCOPES:
            row = report["metrics"][detector][scope]
            (tn, fp), (fn, tp) = row["confusion_matrix"]
            writer.writerow((detector, scope, row["sample_count"], *(row[key] for key in METRICS), tn, fp, fn, tp))
            table.append("| " + " | ".join([
                detector, scope, str(row["sample_count"]),
                *(f"{row[key]:.1%}" for key in METRICS), *(str(value) for value in (tn, fp, fn, tp)),
            ]) + " |")
    table += ["", "Rows in confusion matrices are actual labels; columns are predictions.",
              "Both axes use benign, malicious order. The positive class is malicious.",
              "Results aggregate by run using any malicious observation.",
              "Zero-denominator rates use the frozen report's zero convention.", ""]
    provenance = {
        "integrated_system_commit": "6eac44f562c6db31dcdf42db7cd725917169e838",
        "evaluation": "day32-reserved-lab-results",
        "evaluation_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "dataset_version": "dataset-v1",
        "development_dataset_sha256": metadata["dataset_sha256"],
        "evaluation_population": "12 reserved lab runs; two benign and two malicious per source",
        "model_version": report["model_version"],
        "model_sha256": metadata["model_sha256"],
        "rule_version": report["rule_version"],
        "run_aggregation": report["run_aggregation"],
        "model_metadata_context": "Day 31 training freeze; final_test_evaluated=false records the state before Day 32",
    }
    return {"metrics.csv": stream.getvalue(), "tables.md": "\n".join(table),
            "provenance.json": json.dumps(provenance, indent=2, sort_keys=True) + "\n"}, report


def figures(report):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 4, figsize=(13, 6), layout="constrained")
    for i, detector in enumerate(("rule", "ml")):
        for j, scope in enumerate(SCOPES):
            ax = axes[i, j]
            matrix = report["metrics"][detector][scope]["confusion_matrix"]
            ax.imshow(matrix, vmin=0, vmax=6, cmap="Blues")
            for row in range(2):
                for col in range(2):
                    ax.text(col, row, str(matrix[row][col]), ha="center", va="center")
            ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Benign", "Malicious"],
                   yticklabels=["Benign", "Malicious"], xlabel="Predicted", ylabel="Actual",
                   title=f"{detector.upper()} / {scope}")
    fig.suptitle("Frozen Day 32 confusion matrices (run counts)")
    fig.savefig(OUTPUT / "confusion-matrices.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4), layout="constrained")
    for offset, detector in ((-0.18, "rule"), (0.18, "ml")):
        ax.bar([i + offset for i in range(5)],
               [report["metrics"][detector]["overall"][key] for key in METRICS],
               width=.36, label=detector.upper())
    ax.set(xticks=range(5), xticklabels=["Accuracy", "Precision", "Recall", "F1", "FPR"],
           ylim=(0, 1), ylabel="Rate", title="Frozen Day 32 rules vs ML (12 lab runs)")
    ax.legend()
    fig.savefig(OUTPUT / "overall-comparison.png", dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files, report = package()
    if args.check:
        for name, text in files.items():
            if (OUTPUT / name).read_text(encoding="utf-8") != text:
                parser.exit(1, f"Evaluation package mismatch: {name}\n")
        print("Day 56 tables and provenance reproduce the frozen report")
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (OUTPUT / name).write_text(text, encoding="utf-8", newline="\n")
        figures(report)


if __name__ == "__main__":
    main()
