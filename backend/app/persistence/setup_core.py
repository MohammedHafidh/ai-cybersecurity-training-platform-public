"""Run with python -m app.persistence.setup_core from backend/."""
import os

from app.persistence.core import setup_core_schema
from app.persistence.database import build_engine


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    engine = build_engine(url)
    try:
        setup_core_schema(engine)
    finally:
        engine.dispose()
    print("Core schema ready")


if __name__ == "__main__":
    main()
