import argparse
from pathlib import Path

from app.detection.rules import read_feature_jsonl
from app.ml.holdout import evaluate_untouched_holdout, write_holdout_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the historical Day 18 reserved-variant evaluation")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    report, predictions, model = evaluate_untouched_holdout(
        read_feature_jsonl(args.feature_jsonl)
    )
    write_holdout_outputs(report, predictions, model, args.output_directory)
    print(
        f"evaluated {report.selection.selected_model} once on "
        f"{report.holdout_sample_count} reserved-variant runs (previously explored templates)"
    )


if __name__ == "__main__":
    main()
