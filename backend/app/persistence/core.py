"""Day 33 audit schema, separate from the legacy comparison tables."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class RunRecord(Base):
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("run_id", "source_type"),
        CheckConstraint("source_type IN ('auth', 'web', 'network')"),
        CheckConstraint("expected_label IN ('benign', 'malicious')"),
        CheckConstraint("end_time >= start_time"),
    )

    run_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20))
    scenario: Mapped[str] = mapped_column(String(30))
    expected_label: Mapped[str] = mapped_column(String(20))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(200))
    target: Mapped[str] = mapped_column(String(200))


class EventRecord(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("run_id", "event_id"),
        ForeignKeyConstraint(("run_id", "source_type"), ("runs.run_id", "runs.source_type")),
    )

    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str] = mapped_column(String(50))
    raw_source_file: Mapped[str] = mapped_column(String)
    attributes: Mapped[dict] = mapped_column(JSON)


class DetectionRecord(Base):
    __tablename__ = "detections"
    __table_args__ = (
        ForeignKeyConstraint(("run_id", "event_id"), ("events.run_id", "events.event_id")),
        CheckConstraint("detector IN ('rule', 'ml')"),
        CheckConstraint("predicted_label IN ('benign', 'malicious')"),
    )

    detection_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True)
    event_id: Mapped[str | None] = mapped_column(String(100))
    detector: Mapped[str] = mapped_column(String(20))
    detector_version: Mapped[str] = mapped_column(String(100))
    predicted_label: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict] = mapped_column(JSON)


CORE_TABLES = (RunRecord.__table__, EventRecord.__table__, DetectionRecord.__table__)


def setup_core_schema(engine):
    """Install the additive v1 schema in one PostgreSQL transaction."""
    with engine.begin() as connection:
        Base.metadata.create_all(connection, tables=CORE_TABLES)
