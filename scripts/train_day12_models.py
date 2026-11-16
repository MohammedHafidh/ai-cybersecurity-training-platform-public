import argparse
from pathlib import Path

from app.detection.rules import read_feature_jsonl
from app.ml.training import train_and_compare, write_training_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Day 12 classical ML candidates")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    report, predictions = train_and_compare(
        read_feature_jsonl(args.feature_jsonl), args.output_directory
    )
    write_training_outputs(report, predictions, args.output_directory)
    print(
        f"trained {len(report.candidates)} candidates on {report.training_sample_count} "
        f"runs and validated on {report.validation_sample_count} runs"
    )


if __name__ == "__main__":
    main()

