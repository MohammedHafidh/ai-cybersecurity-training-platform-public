import argparse
from pathlib import Path

from app.detection.rules import read_feature_jsonl
from app.ml.evaluation import (
    evaluate_and_select,
    train_selected_model,
    write_evaluation_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate and select the Day 13 model")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    rows = read_feature_jsonl(args.feature_jsonl)
    report, predictions = evaluate_and_select(rows)
    write_evaluation_outputs(report, predictions, args.output_directory)
    train_selected_model(rows, report, args.output_directory)
    print(
        f"selected {report.selected_model} from {len(report.candidates)} candidates "
        f"using {report.fold_count}-fold cross-validation"
    )


if __name__ == "__main__":
    main()
