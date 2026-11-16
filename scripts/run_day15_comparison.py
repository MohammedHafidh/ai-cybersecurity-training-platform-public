import argparse
import json
from pathlib import Path

from app.detection.comparison import compare_detectors
from app.detection.rules import read_feature_jsonl
from app.ml.inference import inference_request_from_features, load_selected_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Day 15 rule and ML detectors")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    args = parser.parse_args()

    bundle = load_selected_model(args.model, args.metadata)
    rows = read_feature_jsonl(args.feature_jsonl)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    comparisons = [
        compare_detectors(bundle, inference_request_from_features(row))
        for row in sorted(rows, key=lambda item: item.run_id)
    ]
    with args.output_jsonl.open("w", encoding="utf-8", newline="\n") as output:
        for comparison in comparisons:
            output.write(json.dumps(comparison.model_dump(), sort_keys=True) + "\n")
    disagreements = sum(not item.agreement for item in comparisons)
    print(f"wrote {len(comparisons)} comparisons; disagreements={disagreements}")


if __name__ == "__main__":
    main()
