"""Reuse the application database pool and close it on shutdown."""
from contextlib import asynccontextmanager, contextmanager
import os

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.persistence.database import build_engine


@asynccontextmanager
async def database_lifespan(app: FastAPI):
    url = os.getenv("DATABASE_URL")
    try:
        engine = build_engine(url) if url else None
    except (SQLAlchemyError, ValueError, ImportError):
        raise RuntimeError("invalid database configuration") from None
    app.state.database_engine = engine
    training_lock = None
    if engine is not None and os.getenv("CAPSTONE_TRAINING_ENABLED") == "1":
        from app.training.storage import setup_training
        setup_training(engine)
        if engine.dialect.name == "postgresql":
            training_lock = engine.connect()
            if not training_lock.execute(text("SELECT pg_try_advisory_lock(63002026)")).scalar():
                training_lock.close(); engine.dispose()
                raise RuntimeError("Another training platform instance is already using this database")
            from app.training.worker import recover
            try: recover(engine)
            except Exception:
                training_lock.execute(text("SELECT pg_advisory_unlock(63002026)"));training_lock.close();engine.dispose()
                raise RuntimeError("Cannot safely recover an interrupted exercise; check Docker readiness") from None
    try:
        yield
    finally:
        if training_lock is not None:
            training_lock.execute(text("SELECT pg_advisory_unlock(63002026)"));training_lock.close()
        if engine is not None:
            engine.dispose()
        app.state.database_engine = None


@contextmanager
def request_engine(request: Request):
    engine = getattr(request.app.state, "database_engine", None)
    if engine is not None:
        yield engine
        return
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="database is not configured")
    engine = build_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()
