"""Day 36 API for stored observations and frozen detector results."""
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.detection.service import CombinedDetection, DetectionService, DetectionServiceError, RunNotFound, as_utc
from app.detection.explanation import (
    Explanation, ExplanationUnavailable, InvalidExplanation, Question, evidence_sentences, explain,
)
from app.detection.rag_explanation import RagExplanation, explain_with_context
from app.models.events import Label, Scenario, SourceType
from app.persistence.core import DetectionRecord, EventRecord, RunRecord
from app.persistence.database import session_factory
from app.persistence.runtime import request_engine

router = APIRouter()
BUNDLE = Path(__file__).resolve().parents[3] / "data/releases/capstone-ml-v1"
Limit = Annotated[int, Query(ge=1, le=100, description="Maximum records to return")]


def database_session(request: Request):
    try:
        with request_engine(request) as engine:
            with session_factory(engine)() as session:
                yield session
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="detection storage conflict; retry processing") from exc
    except (SQLAlchemyError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="database operation failed") from exc


DB = Annotated[Session, Depends(database_session)]


@lru_cache(maxsize=1)
def detection_service():
    return DetectionService(BUNDLE)


class EventSummary(BaseModel):
    event_id: str
    run_id: str
    source_type: SourceType
    timestamp: datetime
    event_type: str
    raw_source_file: str


class DetectionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detection_id: str
    run_id: str
    event_id: str | None
    detector: Literal["rule", "ml"]
    detector_version: str
    predicted_label: Label
    created_at: datetime


class RunContext(BaseModel):
    source_type: SourceType
    scenario: Scenario
    expected_label: Label
    start_time: datetime
    end_time: datetime
    source: str
    target: str


class DetectionEvidence(DetectionSummary):
    evidence: dict


class DetectionDetail(DetectionEvidence):
    run: RunContext
    counterparts: list[DetectionEvidence]


class ProcessingResult(BaseModel):
    result: CombinedDetection
    detection_ids: list[str]


@router.post("/runs/{run_id}/process", response_model=ProcessingResult, tags=["detections"])
def process_run(run_id: str, session: DB) -> ProcessingResult:
    """Score an ingested run and atomically store both predictions per observation."""
    try:
        service = detection_service()
    except DetectionServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with session.begin():
        run = session.scalar(select(RunRecord).where(RunRecord.run_id == run_id).with_for_update())
        if run is None:
            raise HTTPException(status_code=404, detail="ingested run not found")
        try:
            result = service.detect(session, run_id)
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DetectionServiceError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        ids = []
        now = datetime.now(timezone.utc)
        for observation in result.observations:
            event_id = observation.event_ids[0] if len(observation.event_ids) == 1 else None
            evidence = {
                "row_id": observation.row_id, "event_ids": observation.event_ids,
                "raw_source_files": observation.raw_source_files,
                "observed_features": observation.observed_features,
            }
            for detector, version, label, details in (
                ("rule", observation.rule.rule_version, observation.rule.predicted_label,
                 {"rule": observation.rule.evidence, "predicted_scenario": observation.rule.predicted_scenario}),
                ("ml", observation.ml.model_version, observation.ml.predicted_label,
                 {"malicious_probability": observation.ml.malicious_probability}),
            ):
                identity = f"{run_id}\0{observation.row_id}\0{detector}\0{version}"
                key = "det-" + hashlib.sha256(identity.encode()).hexdigest()
                ids.append(key)
                if session.get(DetectionRecord, key) is None:
                    session.add(DetectionRecord(
                        detection_id=key, run_id=run_id, event_id=event_id, detector=detector,
                        detector_version=version, predicted_label=label, created_at=now,
                        evidence={**evidence, **details},
                    ))
    return ProcessingResult(result=result, detection_ids=ids)


@router.get("/events", response_model=list[EventSummary], tags=["events"])
def recent_events(session: DB, limit: Limit = 20) -> list[EventSummary]:
    """List recent normalized events with source references."""
    rows = session.scalars(select(EventRecord).order_by(
        EventRecord.timestamp.desc(), EventRecord.event_id.desc()).limit(limit))
    return [EventSummary(event_id=row.event_id, run_id=row.run_id,
        source_type=row.source_type, timestamp=as_utc(row.timestamp), event_type=row.event_type,
        raw_source_file=row.raw_source_file) for row in rows]


@router.get("/detections", response_model=list[DetectionSummary], tags=["detections"])
def recent_detections(session: DB, limit: Limit = 20) -> list[DetectionSummary]:
    """List recent stored predictions, identified by detector and version."""
    rows = session.scalars(select(DetectionRecord).order_by(
        DetectionRecord.created_at.desc(), DetectionRecord.detection_id.desc()).limit(limit))
    return [DetectionSummary.model_validate(row).model_copy(
        update={"created_at": as_utc(row.created_at)}) for row in rows]


@router.get("/detections/{detection_id}", response_model=DetectionDetail, tags=["detections"])
def detection_detail(detection_id: str, session: DB) -> DetectionDetail:
    """Return one prediction and its supporting observation evidence."""
    record = session.get(DetectionRecord, detection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="detection not found")
    run = session.get(RunRecord, record.run_id)
    row_id = record.evidence.get("row_id")
    counterparts = []
    if isinstance(row_id, str) and row_id:
        matches = session.scalars(select(DetectionRecord).where(
            DetectionRecord.run_id == record.run_id,
            DetectionRecord.evidence["row_id"].as_string() == row_id,
            DetectionRecord.detector != record.detector,
        ).order_by(DetectionRecord.created_at.desc(), DetectionRecord.detection_id))
        counterparts = [DetectionEvidence.model_validate(match).model_copy(
            update={"created_at": as_utc(match.created_at)}) for match in matches]
    return DetectionDetail(
        **DetectionEvidence.model_validate(record).model_dump(exclude={"created_at"}),
        created_at=as_utc(record.created_at),
        run=RunContext(source_type=run.source_type, scenario=run.scenario,
                       expected_label=run.expected_label, start_time=as_utc(run.start_time),
                       end_time=as_utc(run.end_time), source=run.source, target=run.target),
        counterparts=counterparts,
    )


@router.get("/detections/{detection_id}/explanation", response_model=Explanation, tags=["explanations"])
def detection_explanation(detection_id: str, request: Request, question: Question = Question.summary) -> Explanation:
    """Explain a stored detection without rescoring or updating it."""
    facts, _ = read_explanation_input(detection_id, request)
    try:
        return explain(detection_id, question, facts)
    except ExplanationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InvalidExplanation as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def read_explanation_input(detection_id: str, request: Request) -> tuple[dict[str, str], str]:
    """Copy typed facts and the source family before doing any model work."""
    try:
        with request_engine(request) as engine:
            with session_factory(engine)() as session:
                record = session.get(DetectionRecord, detection_id)
                if record is None:
                    raise HTTPException(status_code=404, detail="detection not found")
                facts = evidence_sentences(record.detector, record.predicted_label, record.evidence)
                run = session.get(RunRecord, record.run_id)
                return facts, run.source_type
    except (SQLAlchemyError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="database operation failed") from exc


@router.get("/detections/{detection_id}/rag-explanation", response_model=RagExplanation, tags=["explanations"])
def detection_rag_explanation(
    detection_id: str,
    request: Request,
    question: Annotated[str, Query(max_length=160)] = Question.summary,
) -> RagExplanation:
    """Explain a stored prediction with cited context from the frozen lab corpus."""
    facts, source_type = read_explanation_input(detection_id, request)
    try:
        return explain_with_context(detection_id, source_type, question, facts)
    except ExplanationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InvalidExplanation as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
