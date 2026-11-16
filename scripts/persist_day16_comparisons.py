import argparse
import json
from pathlib import Path

from sqlalchemy import func, select

from app.detection.comparison import compare_detectors
from app.detection.rules import read_feature_jsonl
from app.ml.inference import inference_request_from_features, load_selected_model
from app.persistence.database import (
    DetectorComparisonRecord,
    FeatureRunRecord,
    MLDetectionRecord,
    RuleDetectionRecord,
    build_engine,
    create_schema,
    session_factory,
)
from app.persistence.repository import get_comparison, save_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist Day 16 detector comparisons")
    parser.add_argument("feature_jsonl", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("database_url")
    parser.add_argument("summary_json", type=Path)
    args = parser.parse_args()

    bundle = load_selected_model(args.model, args.metadata)
    rows = read_feature_jsonl(args.feature_jsonl)
    engine = build_engine(args.database_url)
    create_schema(engine)
    with session_factory(engine)() as session:
        for row in sorted(rows, key=lambda item: item.run_id):
            request = inference_request_from_features(row)
            save_comparison(session, request, compare_detectors(bundle, request))
        counts = {
            "feature_runs": session.scalar(select(func.count()).select_from(FeatureRunRecord)),
            "rule_detections": session.scalar(
                select(func.count()).select_from(RuleDetectionRecord)
            ),
            "ml_detections": session.scalar(
                select(func.count()).select_from(MLDetectionRecord)
            ),
            "detector_comparisons": session.scalar(
                select(func.count()).select_from(DetectorComparisonRecord)
            ),
        }
        stored_runs = session.scalars(select(FeatureRunRecord)).all()
        if any(
            "attack_label" in run.observed_features
            or "scenario" in run.observed_features
            for run in stored_runs
        ):
            raise RuntimeError("ground truth crossed into observed feature storage")
        if any(get_comparison(session, row.run_id) is None for row in rows):
            raise RuntimeError("stored comparison round-trip failed")

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(
        json.dumps(
            {
                "database": "postgresql" if args.database_url.startswith("postgresql") else "other",
                "counts": counts,
                "ground_truth_stored_with_features": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"persisted and read back {counts['detector_comparisons']} comparisons")


if __name__ == "__main__":
    main()
