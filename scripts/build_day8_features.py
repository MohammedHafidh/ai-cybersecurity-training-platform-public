import argparse
from pathlib import Path

from app.processing.features import (
    build_run_features,
    read_normalized_jsonl,
    write_feature_csv,
    write_feature_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one feature row per trusted run")
    parser.add_argument("normalized_events", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    rows = build_run_features(read_normalized_jsonl(args.normalized_events))
    write_feature_jsonl(rows, args.output_directory / "run-features.jsonl")
    write_feature_csv(rows, args.output_directory / "run-features.csv")
    print(f"wrote {len(rows)} feature rows to {args.output_directory}")


if __name__ == "__main__":
    main()

