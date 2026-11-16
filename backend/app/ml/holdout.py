import hashlib
import json
from pathlib import Path

import joblib

from app.ml.evaluation import _source_metrics, _variant_group, evaluate_and_select
from app.ml.training import FEATURE_COLUMNS, RANDOM_STATE, _metrics, candidate_models, feature_frame
from app.models.features import RunFeatures
from app.models.ml import (
    HoldoutEvaluationReport,
    HoldoutPrediction,
    ModelEvaluation,
)


HOLDOUT_GROUP = "variant-05"


def evaluate_untouched_holdout(
    rows: list[RunFeatures], holdout_group: str = HOLDOUT_GROUP
) -> tuple[HoldoutEvaluationReport, list[HoldoutPrediction], object]:
    ordered = sorted(rows, key=lambda row: row.run_id)
    development = [row for row in ordered if _variant_group(row.run_id) != holdout_group]
    holdout = [row for row in ordered if _variant_group(row.run_id) == holdout_group]

    expected_strata = {
        (source, label)
        for source in ("auth", "web", "network")
        for label in ("benign", "malicious")
    }
    observed_holdout = {(row.source_type, row.attack_label) for row in holdout}
    if len(holdout) != 6 or observed_holdout != expected_strata:
        raise ValueError("holdout group must contain one run from every source-label stratum")
    if len(development) != 24:
        raise ValueError("development set must contain four complete six-run variants")

    selection, _ = evaluate_and_select(development, fold_count=4)
    development_features, development_labels = feature_frame(development)
    holdout_features, holdout_labels = feature_frame(holdout)
    model = candidate_models()[selection.selected_model]
    model.fit(development_features, development_labels)
    predicted = model.predict(holdout_features)
    probabilities = model.predict_proba(holdout_features)
    malicious_index = list(model.classes_).index("malicious")

    predicted_by_run = {
        run_id: str(label)
        for run_id, label in zip(holdout_features.index, predicted, strict=True)
    }
    by_source = []
    source_by_run = {row.run_id: row.source_type for row in holdout}
    for source in ("auth", "web", "network"):
        source_ids = [run_id for run_id in holdout_features.index if source_by_run[run_id] == source]
        by_source.append(
            _source_metrics(
                selection.selected_model,
                source,
                holdout_labels.loc[source_ids],
                [predicted_by_run[run_id] for run_id in source_ids],
            )
        )

    final_test = ModelEvaluation(
        model_name=selection.selected_model,
        overall=_metrics(selection.selected_model, holdout_labels, predicted),
        by_source=by_source,
    )
    report = HoldoutEvaluationReport(
        development_sample_count=len(development),
        holdout_sample_count=len(holdout),
        holdout_group=holdout_group,
        development_run_ids=[row.run_id for row in development],
        holdout_run_ids=[row.run_id for row in holdout],
        selection=selection,
        final_test=final_test,
        limitations=[
            "Reserved-variant evaluation contains only six controlled-lab runs.",
            "Variant 05 was explored in earlier experiments; this is not an untouched final benchmark.",
            "The result does not estimate production-network performance.",
            "The holdout must not be reused for model or threshold selection.",
        ],
    )
    predictions = [
        HoldoutPrediction(
            model_name=selection.selected_model,
            run_id=run_id,
            predicted_label=str(label),
            malicious_probability=float(probability[malicious_index]),
        )
        for run_id, label, probability in zip(
            holdout_features.index, predicted, probabilities, strict=True
        )
    ]
    return report, predictions, model


def write_holdout_outputs(report, predictions, model, output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "holdout-evaluation-report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_directory / "holdout-predictions.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as output:
        for prediction in predictions:
            output.write(json.dumps(prediction.model_dump(mode="json"), sort_keys=True) + "\n")

    model_path = output_directory / "holdout-evaluated-model.joblib"
    joblib.dump(model, model_path)
    (output_directory / "holdout-evaluated-model-metadata.json").write_text(
        json.dumps(
            {
                "model_name": report.selection.selected_model,
                "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                "training_sample_count": report.development_sample_count,
                "holdout_sample_count": report.holdout_sample_count,
                "holdout_group": report.holdout_group,
                "feature_columns": FEATURE_COLUMNS,
                "random_state": RANDOM_STATE,
                "intended_use": "controlled-lab capstone detection only",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
