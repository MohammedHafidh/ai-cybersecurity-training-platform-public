import argparse
from pathlib import Path

from app.detection.rules import detect_runs, read_feature_jsonl, write_detection_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the transparent rule baseline")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    args = parser.parse_args()

    detections = detect_runs(read_feature_jsonl(args.feature_jsonl))
    write_detection_jsonl(detections, args.output_jsonl)
    malicious = sum(item.predicted_label == "malicious" for item in detections)
    print(
        f"wrote {len(detections)} rule decisions to {args.output_jsonl} "
        f"({malicious} malicious, {len(detections) - malicious} benign)"
    )


if __name__ == "__main__":
    main()

