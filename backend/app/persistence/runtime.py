"""Reuse the application database pool and close it on shutdown."""
from contextlib import asynccontextmanager, contextmanager
import os

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from app.persistence.database import build_engine


@asynccontextmanager
async def database_lifespan(app: FastAPI):
    url = os.getenv("DATABASE_URL")
    try:
        engine = build_engine(url) if url else None
    except (SQLAlchemyError, ValueError, ImportError):
        raise RuntimeError("invalid database configuration") from None
    app.state.database_engine = engine
    try:
        yield
    finally:
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
