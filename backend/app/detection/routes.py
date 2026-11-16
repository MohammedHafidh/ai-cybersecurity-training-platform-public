"""Day 36 API for stored observations and frozen detector results."""
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.detection.service import CombinedDetection, DetectionService, DetectionServiceError, RunNotFound, as_utc
from app.models.events import Label, SourceType
from app.persistence.core import DetectionRecord, EventRecord, RunRecord
from app.persistence.database import build_engine, session_factory

router = APIRouter()
BUNDLE = Path(__file__).resolve().parents[3] / "data/releases/capstone-ml-v1"
Limit = Annotated[int, Query(ge=1, le=100, description="Maximum records to return")]


def database_session():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="database is not configured")
    try:
        engine = build_engine(url)
        try:
            with session_factory(engine)() as session:
                yield session
        finally:
            engine.dispose()
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


class DetectionDetail(DetectionSummary):
    evidence: dict


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
    return DetectionDetail.model_validate(record).model_copy(
        update={"created_at": as_utc(record.created_at)})
