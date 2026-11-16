import json

import pytest

from app.ml.holdout import evaluate_untouched_holdout, write_holdout_outputs
from test_ml_training import balanced_rows


def test_variant_five_is_untouched_during_selection():
    report, predictions, model = evaluate_untouched_holdout(balanced_rows())

    assert report.development_sample_count == 24
    assert report.holdout_sample_count == 6
    assert report.holdout_group == "variant-05"
    assert report.selection.fold_count == 4
    assert set(report.development_run_ids).isdisjoint(report.holdout_run_ids)
    assert all(run_id.endswith("-05") for run_id in report.holdout_run_ids)
    assert all(not run_id.endswith("-05") for run_id in report.development_run_ids)
    assert len(predictions) == 6
    assert hasattr(model, "predict")


def test_holdout_covers_every_source_and_label_once():
    report, _, _ = evaluate_untouched_holdout(balanced_rows())
    assert {item.source_type for item in report.final_test.by_source} == {
        "auth",
        "web",
        "network",
    }
    assert all(item.sample_count == 2 for item in report.final_test.by_source)
    assert report.final_test.overall.confusion_matrix


def test_holdout_outputs_keep_predictions_separate_from_truth(tmp_path):
    report, predictions, model = evaluate_untouched_holdout(balanced_rows())
    write_holdout_outputs(report, predictions, model, tmp_path)
    records = [
        json.loads(line)
        for line in (tmp_path / "holdout-predictions.jsonl").read_text().splitlines()
    ]
    assert {record["split"] for record in records} == {"final_holdout"}
    assert all("attack_label" not in record and "scenario" not in record for record in records)
    assert (tmp_path / "holdout-evaluated-model.joblib").is_file()
    metadata = json.loads(
        (tmp_path / "holdout-evaluated-model-metadata.json").read_text()
    )
    assert metadata["training_sample_count"] == 24
    assert metadata["holdout_sample_count"] == 6
    assert len(metadata["model_sha256"]) == 64


def test_incomplete_holdout_is_rejected():
    rows = [row for row in balanced_rows() if row.run_id != "run-auth-benign-05"]
    with pytest.raises(ValueError, match="every source-label stratum"):
        evaluate_untouched_holdout(rows)
