import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.detection.comparison import compare_detectors
from app.detection.evaluation import router as evaluation_router
from app.detection.routes import router as detection_router
from app.ingestion.routes import router as ingestion_router
from app.ml.inference import load_selected_model, predict_run
from app.models.detections import DetectorComparison
from app.models.ml import MLDetection, MLInferenceRequest
from app.persistence.core import CORE_TABLES
from app.persistence.database import create_schema, session_factory
from app.persistence.repository import get_comparison, save_comparison
from app.persistence.runtime import database_lifespan, request_engine

app = FastAPI(
    title="AI-Assisted Cybersecurity Training Platform API",
    version="0.1.0",
    lifespan=database_lifespan,
)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
if "*" in frontend_origin:
    raise RuntimeError("FRONTEND_ORIGIN must be one explicit origin")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Capstone-Token"],
)
app.include_router(ingestion_router)
app.include_router(evaluation_router)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Report field errors without reflecting input values or the submitted body."""
    errors = [{key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Simple readiness check used during local development and integration."""
    return {"status": "ok"}


@app.get("/health/database", tags=["system"])
def database_readiness(request: Request) -> dict[str, str]:
    try:
        with request_engine(request) as engine:
            with engine.connect() as connection:
                for table in CORE_TABLES:
                    connection.execute(select(table).limit(0))
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
    request: MLInferenceRequest, http_request: Request,
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
        with request_engine(http_request) as engine:
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
def read_detector_comparison(run_id: str, request: Request) -> DetectorComparison:
    try:
        with request_engine(request) as engine:
            with session_factory(engine)() as session:
                comparison = get_comparison(session, run_id)
    except (ValueError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=503, detail="database operation failed") from exc
    if comparison is None:
        raise HTTPException(status_code=404, detail="comparison not found")
    return comparison


app.include_router(detection_router)

from app.training.routes import router as training_router
app.include_router(training_router)

if os.getenv("CAPSTONE_SERVE_FRONTEND") == "1":
    from fastapi.staticfiles import StaticFiles
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend/dist"
    if not frontend_dist.is_dir():
        raise RuntimeError("Build the frontend before starting the platform")
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="platform")
