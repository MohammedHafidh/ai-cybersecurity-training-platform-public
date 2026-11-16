"""Read a stored run and compare the frozen rule and ML detectors."""

from datetime import datetime, timezone
from pathlib import Path
from pickle import UnpicklingError

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detection.scenario_baselines import INPUT_MODELS, detect_scenario_rows
from app.ml.frozen_v1 import load_pipeline, predict_observations
from app.models.events import Label, NormalizedEvent, Scenario, SourceType
from app.models.runs import RunMetadata
from app.persistence.core import EventRecord, RunRecord
from app.processing.modeling import FEATURES, build_modeling_tables


class DetectionServiceError(ValueError):
    """The stored evidence or model bundle cannot be scored."""


class RunNotFound(DetectionServiceError):
    """No ingested run matches the requested identity."""


class GroundTruth(BaseModel):
    scenario: Scenario
    expected_label: Label


class RulePrediction(BaseModel):
    detection_id: str
    rule_version: str
    predicted_label: Label
    predicted_scenario: Scenario
    triggered: bool
    evidence: dict


class MLPrediction(BaseModel):
    model_version: str
    predicted_label: Label
    malicious_probability: float


class ObservationDetection(BaseModel):
    row_id: str
    event_ids: list[str]
    raw_source_files: list[str]
    observed_features: dict[str, int | float | bool]
    rule: RulePrediction
    ml: MLPrediction


class CombinedDetection(BaseModel):
    run_id: str
    source_type: SourceType
    ground_truth: GroundTruth
    rule_label: Label
    ml_label: Label
    observations: list[ObservationDetection]


class DetectionService:
    def __init__(self, bundle: Path):
        try:
            self._pipeline = load_pipeline(bundle)
        except (OSError, ValueError, KeyError, TypeError, ImportError, EOFError, UnpicklingError) as exc:
            raise DetectionServiceError("frozen ML bundle unavailable or invalid") from exc

    def detect(self, session: Session, run_id: str) -> CombinedDetection:
        run = session.get(RunRecord, run_id)
        if run is None:
            raise RunNotFound("ingested run not found")
        records = list(session.scalars(select(EventRecord).where(EventRecord.run_id == run_id)))
        if not records:
            raise DetectionServiceError("ingested run has no normalized events")
        try:
            context = RunMetadata(
                run_id=run_id, source=run.source, target=run.target, scenario=run.scenario,
                expected_label=run.expected_label, start_time=as_utc(run.start_time),
                end_time=as_utc(run.end_time), tool_or_method="stored normalized evidence",
                log_sources=sorted({record.raw_source_file for record in records}),
            )
            events = [
                NormalizedEvent(
                    **record.attributes, event_id=record.event_id, run_id=record.run_id,
                    source_type=record.source_type, timestamp=as_utc(record.timestamp),
                    event_type=record.event_type, raw_source_file=record.raw_source_file,
                    attack_label=context.expected_label, scenario=context.scenario,
                )
                for record in records
            ]
            rows = build_modeling_tables(events, {run_id: context})[run.source_type]
            observations = self.score_observations(run.source_type, rows)
        except (KeyError, TypeError, ValueError) as exc:
            raise DetectionServiceError("stored run cannot be scored") from exc
        return CombinedDetection(
            run_id=run_id, source_type=run.source_type,
            ground_truth=GroundTruth(scenario=context.scenario, expected_label=context.expected_label),
            rule_label="malicious" if any(row.rule.triggered for row in observations) else "benign",
            ml_label="malicious" if any(row.ml.predicted_label == "malicious" for row in observations) else "benign",
            observations=observations,
        )

    def score_observations(self, source: SourceType, rows: list[dict]) -> list[ObservationDetection]:
        """Score prepared rows using explicit observable-field allowlists."""
        schema = INPUT_MODELS[source]
        rules = {record["row_id"]: record for record in detect_scenario_rows(source, [
            schema(**{field: row[field] for field in schema.model_fields}) for row in rows
        ])}
        features = [{field: row[field] for field in FEATURES[source]} for row in rows]
        ml = predict_observations(self._pipeline, [dict(source_type=source, **row) for row in features])
        return [
            ObservationDetection(
                row_id=row["row_id"], event_ids=row["event_ids"], raw_source_files=row["raw_source_files"],
                observed_features=observed, rule=RulePrediction.model_validate(rules[row["row_id"]]),
                ml=MLPrediction.model_validate(prediction),
            )
            for row, observed, prediction in zip(rows, features, ml, strict=True)
        ]


def as_utc(value: datetime) -> datetime:
    # SQLite loses timezone information. The ingestion service writes UTC.
    return value.replace(tzinfo=timezone.utc) if value.utcoffset() is None else value.astimezone(timezone.utc)
