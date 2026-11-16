from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class FeatureRunRecord(Base):
    __tablename__ = "feature_runs"

    run_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_features: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RuleDetectionRecord(Base):
    __tablename__ = "rule_detections"

    detection_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("feature_runs.run_id"), unique=True, nullable=False
    )
    predicted_label: Mapped[str] = mapped_column(String(20), nullable=False)
    predicted_scenario: Mapped[str] = mapped_column(String(30), nullable=False)
    triggered_rule: Mapped[str | None] = mapped_column(String(100))
    evidence: Mapped[list] = mapped_column(JSON, nullable=False)


class MLDetectionRecord(Base):
    __tablename__ = "ml_detections"

    detection_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("feature_runs.run_id"), unique=True, nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(40), nullable=False)
    model_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_label: Mapped[str] = mapped_column(String(20), nullable=False)
    malicious_probability: Mapped[float] = mapped_column(Float, nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)


class DetectorComparisonRecord(Base):
    __tablename__ = "detector_comparisons"

    comparison_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("feature_runs.run_id"), unique=True, nullable=False
    )
    rule_detection_id: Mapped[str] = mapped_column(
        ForeignKey("rule_detections.detection_id"), unique=True, nullable=False
    )
    ml_detection_id: Mapped[str] = mapped_column(
        ForeignKey("ml_detections.detection_id"), unique=True, nullable=False
    )
    agreement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    review_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False)


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def session_factory(engine: Engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
