import json
from pathlib import Path

import joblib
import pytest

from app.ingestion.pipeline import normalize_manifest
from app.ml.training import (
    FEATURE_COLUMNS,
    feature_frame,
    split_run_ids,
    train_and_compare,
    write_training_outputs,
)
from app.processing.features import build_run_features


FIXTURES = Path(__file__).parent / "fixtures" / "day7"


def seed_rows():
    return build_run_features(normalize_manifest(FIXTURES / "manifest.json"))


def balanced_rows():
    seeds = seed_rows()
    web_benign = next(
        row for row in seeds if row.source_type == "web" and row.attack_label == "benign"
    )
    attack_by_source = {
        source: next(
            row
            for row in seeds
            if row.source_type == source and row.attack_label == "malicious"
        )
        for source in ("auth", "web", "network")
    }
    rows = []
    for index in range(1, 6):
        for source in ("auth", "web", "network"):
            benign_updates = {
                "feature_id": f"feat-{source}-benign-{index}",
                "run_id": f"run-{source}-benign-{index:02d}",
                "source_type": source,
                "web_request_count": 0 if source != "web" else 1,
                "max_request_length": 0 if source != "web" else 1,
            }
            if source == "auth":
                benign_updates.update(
                    auth_attempt_count=1,
                    successful_login_count=1,
                    unique_username_count=1,
                )
            if source == "network":
                benign_updates.update(
                    connection_count=1,
                    unique_destination_port_count=1,
                )
            benign = web_benign.model_copy(update=benign_updates)
            attack = attack_by_source[source].model_copy(
                update={
                    "feature_id": f"feat-{source}-malicious-{index}",
                    "run_id": f"run-{source}-malicious-{index:02d}",
                }
            )
            rows.extend([benign, attack])
    return rows


def test_feature_frame_excludes_identity_timestamps_and_ground_truth():
    features, labels = feature_frame(balanced_rows())
    assert list(features.columns) == FEATURE_COLUMNS
    assert "attack_label" not in features
    assert "scenario" not in features
    assert "run_id" not in features
    assert set(labels) == {"benign", "malicious"}


def test_stratified_run_split_is_disjoint_and_reproducible():
    rows = balanced_rows()
    first = split_run_ids(rows)
    second = split_run_ids(list(reversed(rows)))
    assert first == second
    train_ids, validation_ids = first
    assert len(train_ids) == 21
    assert len(validation_ids) == 9
    assert set(train_ids).isdisjoint(validation_ids)


def test_training_saves_three_loadable_candidates(tmp_path):
    report, predictions = train_and_compare(balanced_rows(), tmp_path)
    assert {metric.model_name for metric in report.candidates} == {
        "logistic_regression",
        "decision_tree",
        "random_forest",
    }
    assert report.selected_model is None
    assert len(predictions) == 27
    for model_name in ("logistic_regression", "decision_tree", "random_forest"):
        model = joblib.load(tmp_path / "models" / f"{model_name}.joblib")
        assert hasattr(model, "predict")


def test_predictions_are_separate_from_ground_truth(tmp_path):
    report, predictions = train_and_compare(balanced_rows(), tmp_path)
    write_training_outputs(report, predictions, tmp_path)
    records = [
        json.loads(line)
        for line in (tmp_path / "validation-predictions.jsonl").read_text().splitlines()
    ]
    assert records
    assert all("attack_label" not in record and "scenario" not in record for record in records)
    assert {record["split"] for record in records} == {"validation"}


def test_metrics_include_required_capstone_measures(tmp_path):
    report, _ = train_and_compare(balanced_rows(), tmp_path)
    for metric in report.candidates:
        assert 0 <= metric.accuracy <= 1
        assert 0 <= metric.precision <= 1
        assert 0 <= metric.recall <= 1
        assert 0 <= metric.f1 <= 1
        assert 0 <= metric.false_positive_rate <= 1
        assert len(metric.confusion_matrix) == 2


def test_training_refuses_the_original_four_row_extract(tmp_path):
    with pytest.raises(ValueError, match="not ML-ready"):
        train_and_compare(seed_rows(), tmp_path)

