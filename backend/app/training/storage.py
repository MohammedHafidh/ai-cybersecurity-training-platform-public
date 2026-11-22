from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.persistence.database import Base
from app.persistence.core import RunRecord


class Exercise(Base):
    __tablename__ = "training_exercises"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    scenario: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="running")
    stage: Mapped[str] = mapped_column(String(20), default="preparing")
    active_slot: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey(RunRecord.run_id), nullable=True)
    history: Mapped[list] = mapped_column(JSON, default=list)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(String(300), default="")


class QuizAttempt(Base):
    __tablename__ = "training_quiz_attempts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey(Exercise.id))
    version: Mapped[str] = mapped_column(String(40))
    answers: Mapped[list] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    passed: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def setup_training(engine):
    Base.metadata.create_all(engine, tables=[Exercise.__table__, QuizAttempt.__table__])
