import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.ml.readiness import audit_ml_readiness
from app.models.features import RunFeatures
from app.models.ml import MLPrediction, ModelMetrics, ModelTrainingReport


RANDOM_STATE = 42
NUMERIC_FEATURES = [
    "event_count",
    "auth_attempt_count",
    "failed_login_count",
    "successful_login_count",
    "unique_username_count",
    "web_request_count",
    "max_request_length",
    "suspicious_token_count",
    "connection_count",
    "unique_destination_port_count",
]
CATEGORICAL_FEATURES = ["source_type"]
FEATURE_COLUMNS = [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]


def feature_frame(rows: list[RunFeatures]) -> tuple[pd.DataFrame, pd.Series]:
    records = [row.model_dump(mode="json") for row in rows]
    frame = pd.DataFrame(records).set_index("run_id", drop=False)
    return frame[FEATURE_COLUMNS], frame["attack_label"]


def split_run_ids(rows: list[RunFeatures]) -> tuple[list[str], list[str]]:
    frame = pd.DataFrame(
        {"run_id": [row.run_id for row in rows], "label": [row.attack_label for row in rows]}
    ).sort_values("run_id")
    train_ids, validation_ids = train_test_split(
        frame["run_id"],
        test_size=0.3,
        random_state=RANDOM_STATE,
        stratify=frame["label"],
    )
    return sorted(train_ids.tolist()), sorted(validation_ids.tolist())


def _preprocessor(scale: bool) -> ColumnTransformer:
    numeric_transformer = StandardScaler() if scale else "passthrough"
    return ColumnTransformer(
        [
            ("numeric", numeric_transformer, NUMERIC_FEATURES),
            (
                "source",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def candidate_models() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            [
                ("features", _preprocessor(scale=True)),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE
                    ),
                ),
            ]
        ),
        "decision_tree": Pipeline(
            [
                ("features", _preprocessor(scale=False)),
                (
                    "classifier",
                    DecisionTreeClassifier(
                        max_depth=4, class_weight="balanced", random_state=RANDOM_STATE
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("features", _preprocessor(scale=False)),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=100,
                        max_depth=5,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
    }


def _metrics(model_name: str, truth: pd.Series, predictions) -> ModelMetrics:
    matrix = confusion_matrix(truth, predictions, labels=["benign", "malicious"])
    true_negative, false_positive, false_negative, true_positive = matrix.ravel()
    denominator = false_positive + true_negative
    return ModelMetrics(
        model_name=model_name,
        accuracy=accuracy_score(truth, predictions),
        precision=precision_score(truth, predictions, pos_label="malicious", zero_division=0),
        recall=recall_score(truth, predictions, pos_label="malicious", zero_division=0),
        f1=f1_score(truth, predictions, pos_label="malicious", zero_division=0),
        false_positive_rate=false_positive / denominator if denominator else 0.0,
        confusion_matrix=matrix.tolist(),
    )


def train_and_compare(
    rows: list[RunFeatures], output_directory: Path
) -> tuple[ModelTrainingReport, list[MLPrediction]]:
    readiness = audit_ml_readiness(rows)
    if not readiness.ready_for_training:
        raise ValueError(f"dataset is not ML-ready: {readiness.blockers}")

    output_directory.mkdir(parents=True, exist_ok=True)
    models_directory = output_directory / "models"
    models_directory.mkdir(exist_ok=True)
    train_ids, validation_ids = split_run_ids(rows)
    features, labels = feature_frame(rows)
    train_features = features.loc[train_ids]
    validation_features = features.loc[validation_ids]
    train_labels = labels.loc[train_ids]
    validation_labels = labels.loc[validation_ids]

    metrics: list[ModelMetrics] = []
    prediction_records: list[MLPrediction] = []
    for model_name, model in candidate_models().items():
        model.fit(train_features, train_labels)
        predictions = model.predict(validation_features)
        probabilities = model.predict_proba(validation_features)
        malicious_index = list(model.classes_).index("malicious")
        metrics.append(_metrics(model_name, validation_labels, predictions))
        prediction_records.extend(
            MLPrediction(
                model_name=model_name,
                run_id=run_id,
                predicted_label=prediction,
                malicious_probability=float(probability[malicious_index]),
            )
            for run_id, prediction, probability in zip(
                validation_ids, predictions, probabilities, strict=True
            )
        )
        joblib.dump(model, models_directory / f"{model_name}.joblib")

    report = ModelTrainingReport(
        training_sample_count=len(train_ids),
        validation_sample_count=len(validation_ids),
        random_state=RANDOM_STATE,
        stratified=True,
        feature_columns=FEATURE_COLUMNS,
        train_run_ids=train_ids,
        validation_run_ids=validation_ids,
        candidates=metrics,
        selected_model=None,
        selection_note=(
            "Day 12 trains and compares candidates only. Final selection is deferred "
            "to the dedicated evaluation stage."
        ),
    )
    return report, prediction_records


def write_training_outputs(
    report: ModelTrainingReport,
    predictions: list[MLPrediction],
    output_directory: Path,
) -> None:
    (output_directory / "training-report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_directory / "validation-predictions.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as output:
        for prediction in predictions:
            output.write(
                json.dumps(prediction.model_dump(mode="json"), sort_keys=True) + "\n"
            )

