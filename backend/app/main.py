import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.detection.comparison import compare_detectors
from app.detection.routes import router as detection_router
from app.ingestion.routes import router as ingestion_router
from app.ml.inference import load_selected_model, predict_run
from app.models.detections import DetectorComparison
from app.models.ml import MLDetection, MLInferenceRequest
from app.persistence.core import CORE_TABLES
from app.persistence.database import build_engine, create_schema, session_factory
from app.persistence.repository import get_comparison, save_comparison

app = FastAPI(
    title="AI-Assisted Cybersecurity Training Platform API",
    version="0.1.0",
)
app.include_router(ingestion_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Simple readiness check used during local development and integration."""
    return {"status": "ok"}


@app.get("/health/database", tags=["system"])
def database_readiness() -> dict[str, str]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="database is not configured")
    try:
        engine = build_engine(database_url)
        try:
            with engine.connect() as connection:
                for table in CORE_TABLES:
                    connection.execute(select(table).limit(0))
        finally:
            engine.dispose()
    except (SQLAlchemyError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="core database schema unavailable") from exc
    return {"status": "ok"}


@app.post("/detections/ml", response_model=MLDetection, tags=["detections"])
def create_ml_detection(request: MLInferenceRequest) -> MLDetection:
    """Run the verified selected model against one bounded feature record."""
    model_path = os.environ.get("ML_MODEL_PATH")
    metadata_path = os.environ.get("ML_MODEL_METADATA_PATH")
    if not model_path or not metadata_path:
        raise HTTPException(status_code=503, detail="selected ML model is not configured")
    try:
        bundle = load_selected_model(Path(model_path), Path(metadata_path))
        return predict_run(bundle, request)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/detections/compare", response_model=DetectorComparison, tags=["detections"]
)
def create_detector_comparison(request: MLInferenceRequest) -> DetectorComparison:
    """Compare independent rule and ML predictions without inventing ground truth."""
    model_path = os.environ.get("ML_MODEL_PATH")
    metadata_path = os.environ.get("ML_MODEL_METADATA_PATH")
    if not model_path or not metadata_path:
        raise HTTPException(status_code=503, detail="selected ML model is not configured")
    try:
        bundle = load_selected_model(Path(model_path), Path(metadata_path))
        return compare_detectors(bundle, request)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/detections/compare/store", response_model=DetectorComparison, tags=["detections"]
)
def create_and_store_detector_comparison(
    request: MLInferenceRequest,
) -> DetectorComparison:
    """Create and transactionally store separate run and detector records."""
    database_url = os.environ.get("DATABASE_URL")
    model_path = os.environ.get("ML_MODEL_PATH")
    metadata_path = os.environ.get("ML_MODEL_METADATA_PATH")
    if not database_url:
        raise HTTPException(status_code=503, detail="database is not configured")
    if not model_path or not metadata_path:
        raise HTTPException(status_code=503, detail="selected ML model is not configured")
    try:
        bundle = load_selected_model(Path(model_path), Path(metadata_path))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    comparison = compare_detectors(bundle, request)
    try:
        engine = build_engine(database_url)
        create_schema(engine)
        with session_factory(engine)() as session:
            return save_comparison(session, request, comparison)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database operation failed") from exc


@app.get(
    "/detections/comparisons/{run_id}",
    response_model=DetectorComparison,
    tags=["detections"],
)
def read_detector_comparison(run_id: str) -> DetectorComparison:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="database is not configured")
    try:
        engine = build_engine(database_url)
        with session_factory(engine)() as session:
            comparison = get_comparison(session, run_id)
    except (ValueError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="database operation failed") from exc
    if comparison is None:
        raise HTTPException(status_code=404, detail="comparison not found")
    return comparison


app.include_router(detection_router)
