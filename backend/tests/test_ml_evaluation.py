import json

import joblib
import pytest

from app.ml.evaluation import (
    evaluate_and_select,
    train_selected_model,
    write_evaluation_outputs,
)
from test_ml_training import balanced_rows, seed_rows


def test_evaluation_is_reproducible_and_covers_every_run_once_per_model():
    rows = balanced_rows()
    first_report, first_predictions = evaluate_and_select(rows)
    second_report, second_predictions = evaluate_and_select(list(reversed(rows)))
    assert first_report == second_report
    assert first_predictions == second_predictions
    assert len(first_predictions) == 90
    for model_name in ("logistic_regression", "decision_tree", "random_forest"):
        model_predictions = [
            item for item in first_predictions if item.model_name == model_name
        ]
        assert len({item.run_id for item in model_predictions}) == 30


def test_report_includes_overall_and_per_source_metrics():
    report, _ = evaluate_and_select(balanced_rows())
    assert report.fold_count == 5
    assert report.stratification.endswith("grouped by controlled variant")
    assert {item.model_name for item in report.candidates} == {
        "logistic_regression",
        "decision_tree",
        "random_forest",
    }
    for candidate in report.candidates:
        assert {item.source_type for item in candidate.by_source} == {
            "auth",
            "web",
            "network",
        }
        assert all(item.sample_count == 10 for item in candidate.by_source)


def test_selection_uses_documented_tie_break_and_records_limitations():
    report, _ = evaluate_and_select(balanced_rows())
    assert report.selected_model in {
        "logistic_regression",
        "decision_tree",
        "random_forest",
    }
    assert report.selection_criteria[-1].startswith("simplest model")
    assert any("production traffic" in item for item in report.limitations)


def test_predictions_keep_ground_truth_separate(tmp_path):
    report, predictions = evaluate_and_select(balanced_rows())
    write_evaluation_outputs(report, predictions, tmp_path)
    records = [
        json.loads(line)
        for line in (tmp_path / "cross-validation-predictions.jsonl")
        .read_text()
        .splitlines()
    ]
    assert all("attack_label" not in item and "scenario" not in item for item in records)
    assert {item["split"] for item in records} == {"cross_validation"}


def test_evaluation_rejects_too_small_dataset():
    with pytest.raises(ValueError, match="at least 10"):
        evaluate_and_select(seed_rows())


def test_every_variant_is_held_out_in_exactly_one_fold():
    _, predictions = evaluate_and_select(balanced_rows())
    logistic = [
        item for item in predictions if item.model_name == "logistic_regression"
    ]
    fold_by_variant = {}
    for item in logistic:
        variant = item.run_id.rsplit("-", 1)[-1]
        fold_by_variant.setdefault(variant, set()).add(item.fold)
    assert set(fold_by_variant) == {"01", "02", "03", "04", "05"}
    assert all(len(folds) == 1 for folds in fold_by_variant.values())


def test_selected_model_is_refit_on_all_runs_with_metadata(tmp_path):
    rows = balanced_rows()
    report, _ = evaluate_and_select(rows)
    model_path = train_selected_model(rows, report, tmp_path)
    model = joblib.load(model_path)
    metadata = json.loads((tmp_path / "selected-model-metadata.json").read_text())
    assert hasattr(model, "predict")
    assert metadata["model_name"] == report.selected_model
    assert len(metadata["model_sha256"]) == 64
    assert metadata["training_sample_count"] == 30
    assert metadata["intended_use"] == "controlled-lab capstone detection only"
