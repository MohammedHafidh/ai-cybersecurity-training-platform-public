"""Validate and persist a normalized run as a single database transaction."""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.ingestion.validation import validate_run_metadata
from app.models.events import NormalizedEvent, SourceType
from app.models.runs import RunMetadata
from app.persistence.core import EventRecord, RunRecord


class IngestRunMetadata(RunMetadata):
    model_config = ConfigDict(extra="forbid")


class IngestEvent(NormalizedEvent):
    model_config = ConfigDict(extra="forbid")


class RunIngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    run: IngestRunMetadata
    events: list[IngestEvent] = Field(min_length=1)

    @model_validator(mode="after")
    def check_consistency(self):
        run = self.run
        errors = validate_run_metadata(run)
        if errors:
            raise ValueError("; ".join(errors))
        if run.status != "valid":
            raise ValueError("only valid runs can be ingested")
        scenario_for_source = {"auth": "brute_force", "web": "sql_injection", "network": "reconnaissance"}
        if run.scenario not in ("benign", scenario_for_source[self.source_type]):
            raise ValueError("run scenario does not match source_type")
        for key in ("run_id", "source", "target"):
            check_text(getattr(run, key), key, 200)
        seen = set()
        required_fields = {
            "auth": ("source_ip", "username", "outcome"),
            "web": ("source_ip",),
            "network": ("source_ip", "destination_port", "protocol"),
        }[self.source_type]
        for i, event in enumerate(self.events):
            prefix = f"events[{i}]"
            check_text(event.event_id, f"{prefix}.event_id", 100)
            check_text(event.event_type, f"{prefix}.event_type", 50)
            check_text(event.raw_source_file, f"{prefix}.raw_source_file")
            if event.event_id in seen:
                raise ValueError(f"{prefix} duplicates an event ID")
            seen.add(event.event_id)
            if event.run_id != run.run_id or event.source_type != self.source_type:
                raise ValueError(f"{prefix} does not match the run ID and source type")
            if event.scenario != run.scenario or event.attack_label != run.expected_label:
                raise ValueError(f"{prefix} disagrees with the run metadata label or scenario")
            if event.timestamp.utcoffset() is None or not run.start_time <= event.timestamp <= run.end_time:
                raise ValueError(f"{prefix} needs a timezone-aware timestamp within the run window")
            if event.raw_source_file not in run.log_sources:
                raise ValueError(f"{prefix} references an undeclared raw source file")
            for field in required_fields:
                value = getattr(event, field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    raise ValueError(f"{prefix}.{field} is required for {self.source_type}")
        return self


def check_text(value: str, field: str, limit: int | None = None) -> None:
    if not value.strip() or "\0" in value or (limit is not None and len(value) > limit):
        raise ValueError(f"{field} is empty, contains a null character, or exceeds its length limit")


class RunIngestionResult(BaseModel):
    run_id: str
    event_count: int


def store_run(session: Session, request: RunIngestionRequest) -> RunIngestionResult:
    run = request.run
    with session.begin():
        session.add(RunRecord(source_type=request.source_type, **run.model_dump(
            include={"run_id", "scenario", "expected_label", "start_time", "end_time", "source", "target"}
        )))
        session.flush()
        for event in request.events:
            columns = {"event_id", "run_id", "source_type", "timestamp", "event_type", "raw_source_file"}
            session.add(EventRecord(
                **event.model_dump(include=columns),
                attributes=event.model_dump(mode="json", exclude=columns | {"attack_label", "scenario"}, exclude_none=True),
            ))
    return RunIngestionResult(run_id=run.run_id, event_count=len(request.events))
