"""Ingest caller-supplied normalized JSON. Raw files stay outside the API."""
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.ingestion.service import RunIngestionRequest, RunIngestionResult, store_run
from app.persistence.database import session_factory
from app.persistence.runtime import request_engine

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/runs", response_model=RunIngestionResult, status_code=201)
def ingest_run(body: RunIngestionRequest, request: Request) -> RunIngestionResult:
    try:
        with request_engine(request) as engine:
            with session_factory(engine)() as session:
                return store_run(session, body)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="run or event ID already exists") from exc
    except (SQLAlchemyError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="database operation failed") from exc
