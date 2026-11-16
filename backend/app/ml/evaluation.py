import json
import hashlib
import re
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.model_selection import StratifiedGroupKFold

from app.ml.training import (
    FEATURE_COLUMNS,
    RANDOM_STATE,
    _metrics,
    candidate_models,
    feature_frame,
)
from app.models.features import RunFeatures
from app.models.ml import (
    EvaluationPrediction,
    ModelEvaluation,
    ModelSelectionReport,
    SourceMetrics,
)


FOLD_COUNT = 5
MODEL_SIMPLICITY_ORDER = {
    "logistic_regression": 0,
    "decision_tree": 1,
    "random_forest": 2,
}
SELECTION_CRITERIA = [
    "highest malicious recall",
    "lowest false-positive rate",
    "highest F1 score",
    "highest accuracy",
    "simplest model when all measured metrics tie",
]
VARIANT_PATTERN = re.compile(
    r"-(?:auth|web|network)-(?:benign|malicious)-(\d{2})(?:-|$)"
)


def _variant_group(run_id: str) -> str:
    match = VARIANT_PATTERN.search(run_id)
    if not match:
        raise ValueError(
            f"run ID {run_id!r} does not contain a two-digit controlled variant"
        )
    return f"variant-{match.group(1)}"


def _source_metrics(model_name, source_type, truth, predictions) -> SourceMetrics:
    metric = _metrics(model_name, truth, predictions)
    return SourceMetrics(
        **metric.model_dump(), source_type=source_type, sample_count=len(truth)
    )


def evaluate_and_select(
    rows: list[RunFeatures],
    *,
    fold_count: int = FOLD_COUNT,
) -> tuple[ModelSelectionReport, list[EvaluationPrediction]]:
    if fold_count < 2:
        raise ValueError("evaluation requires at least two folds")
    if len(rows) < fold_count * 2:
        raise ValueError(f"at least {fold_count * 2} runs are required")

    ordered = sorted(rows, key=lambda row: row.run_id)
    features, labels = feature_frame(ordered)
    run_ids = features.index.to_numpy()
    strata = np.array(
        [f"{row.source_type}:{row.attack_label}" for row in ordered], dtype=object
    )
    groups = np.array([_variant_group(row.run_id) for row in ordered], dtype=object)
    if min(np.unique(strata, return_counts=True)[1]) < fold_count:
        raise ValueError(
            f"each source-label stratum requires at least {fold_count} runs"
        )

    unique_groups = sorted(set(groups))
    if len(unique_groups) != fold_count:
        raise ValueError(
            f"exactly {fold_count} controlled variant groups are required"
        )
    for group in unique_groups:
        group_strata = set(strata[groups == group])
        if len(group_strata) != 6:
            raise ValueError(f"{group} must cover every source-label stratum")

    splitter = StratifiedGroupKFold(
        n_splits=fold_count, shuffle=True, random_state=RANDOM_STATE
    )
    source_by_run = {row.run_id: row.source_type for row in ordered}
    evaluations: list[ModelEvaluation] = []
    output_predictions: list[EvaluationPrediction] = []

    for model_name, template in candidate_models().items():
        predicted_by_run: dict[str, str] = {}
        probability_by_run: dict[str, float] = {}
        fold_by_run: dict[str, int] = {}
        for fold, (train_indexes, test_indexes) in enumerate(
            splitter.split(features, strata, groups), 1
        ):
            model = clone(template)
            train_ids = run_ids[train_indexes].tolist()
            test_ids = run_ids[test_indexes].tolist()
            model.fit(features.loc[train_ids], labels.loc[train_ids])
            predictions = model.predict(features.loc[test_ids])
            probabilities = model.predict_proba(features.loc[test_ids])
            malicious_index = list(model.classes_).index("malicious")
            for run_id, prediction, probability in zip(
                test_ids, predictions, probabilities, strict=True
            ):
                predicted_by_run[run_id] = str(prediction)
                probability_by_run[run_id] = float(probability[malicious_index])
                fold_by_run[run_id] = fold

        predictions = [predicted_by_run[run_id] for run_id in run_ids]
        overall = _metrics(model_name, labels.loc[run_ids], predictions)
        by_source: list[SourceMetrics] = []
        for source_type in ("auth", "web", "network"):
            source_ids = [
                run_id for run_id in run_ids if source_by_run[run_id] == source_type
            ]
            by_source.append(
                _source_metrics(
                    model_name,
                    source_type,
                    labels.loc[source_ids],
                    [predicted_by_run[run_id] for run_id in source_ids],
                )
            )
        evaluations.append(
            ModelEvaluation(model_name=model_name, overall=overall, by_source=by_source)
        )
        output_predictions.extend(
            EvaluationPrediction(
                model_name=model_name,
                run_id=run_id,
                fold=fold_by_run[run_id],
                predicted_label=predicted_by_run[run_id],
                malicious_probability=probability_by_run[run_id],
            )
            for run_id in run_ids
        )

    ranked = sorted(
        evaluations,
        key=lambda item: (
            -item.overall.recall,
            item.overall.false_positive_rate,
            -item.overall.f1,
            -item.overall.accuracy,
            MODEL_SIMPLICITY_ORDER[item.model_name],
        ),
    )
    selected = ranked[0]
    report = ModelSelectionReport(
        sample_count=len(ordered),
        fold_count=fold_count,
        random_state=RANDOM_STATE,
        stratification=(
            "source_type plus trusted attack_label, grouped by controlled variant"
        ),
        selection_criteria=SELECTION_CRITERIA,
        candidates=evaluations,
        selected_model=selected.model_name,
        selection_reason=(
            f"{selected.model_name} ranked first using the documented lexicographic "
            "criteria. The final criterion deliberately prefers the simplest model "
            "only when measured performance is tied."
        ),
        limitations=[
            f"Evaluation uses {len(ordered)} controlled lab runs, not production traffic.",
            f"Each source-label group contains only {fold_count} bounded scenario variants.",
            "Every controlled variant is held out as one group to prevent template leakage.",
            "The selected model must be re-evaluated as the dataset grows.",
        ],
    )
    return report, output_predictions


def write_evaluation_outputs(report, predictions, output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "model-selection-report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_directory / "cross-validation-predictions.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as output:
        for prediction in predictions:
            output.write(
                json.dumps(prediction.model_dump(mode="json"), sort_keys=True) + "\n"
            )


def train_selected_model(
    rows: list[RunFeatures], report: ModelSelectionReport, output_directory: Path
) -> Path:
    """Fit the selected algorithm on all available runs after out-of-fold selection."""
    features, labels = feature_frame(sorted(rows, key=lambda row: row.run_id))
    model = candidate_models()[report.selected_model]
    model.fit(features, labels)
    model_path = output_directory / "selected-model.joblib"
    joblib.dump(model, model_path)
    model_sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
    (output_directory / "selected-model-metadata.json").write_text(
        json.dumps(
            {
                "model_name": report.selected_model,
                "model_sha256": model_sha256,
                "training_sample_count": len(rows),
                "feature_columns": FEATURE_COLUMNS,
                "random_state": RANDOM_STATE,
                "selection_report": "model-selection-report.json",
                "intended_use": "controlled-lab capstone detection only",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return model_path
