import argparse
import json
from pathlib import Path

from app.detection.rules import read_feature_jsonl
from app.ml.inference import (
    inference_request_from_features,
    load_selected_model,
    predict_run,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the selected Day 14 ML detector")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    args = parser.parse_args()

    bundle = load_selected_model(args.model, args.metadata)
    rows = read_feature_jsonl(args.feature_jsonl)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8", newline="\n") as output:
        for row in sorted(rows, key=lambda value: value.run_id):
            detection = predict_run(bundle, inference_request_from_features(row))
            output.write(json.dumps(detection.model_dump(), sort_keys=True) + "\n")
    print(f"wrote {len(rows)} ML detections using {bundle.model_name}")


if __name__ == "__main__":
    main()
