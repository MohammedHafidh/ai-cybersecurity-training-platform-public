"""Ingest caller-supplied normalized JSON. Raw files stay outside the API."""
import os

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.ingestion.service import RunIngestionRequest, RunIngestionResult, store_run
from app.persistence.database import build_engine, session_factory

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/runs", response_model=RunIngestionResult, status_code=201)
def ingest_run(request: RunIngestionRequest) -> RunIngestionResult:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="database is not configured")
    try:
        engine = build_engine(url)
        try:
            with session_factory(engine)() as session:
                return store_run(session, request)
        finally:
            engine.dispose()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="run or event ID already exists") from exc
    except (SQLAlchemyError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="database operation failed") from exc
