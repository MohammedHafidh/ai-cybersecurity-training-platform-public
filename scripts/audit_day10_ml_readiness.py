import argparse
from pathlib import Path

from app.detection.rules import read_feature_jsonl
from app.ml.readiness import audit_ml_readiness, write_readiness_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit whether lab features are ML-ready")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("output_report", type=Path)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="exit unsuccessfully when the dataset is not ready for training",
    )
    args = parser.parse_args()

    report = audit_ml_readiness(read_feature_jsonl(args.feature_jsonl))
    write_readiness_report(report, args.output_report)
    state = "ready" if report.ready_for_training else "not ready"
    print(f"ML dataset is {state}; blockers: {report.blockers}")
    if args.require_ready and not report.ready_for_training:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

