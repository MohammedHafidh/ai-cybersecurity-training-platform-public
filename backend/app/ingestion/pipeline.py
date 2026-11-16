import hashlib
import json
from pathlib import Path

from app.ingestion.parsers import parsed_lines
from app.ingestion.raw_reader import read_raw_log
from app.ingestion.validation import validate_run_metadata
from app.models.events import NormalizedEvent
from app.models.runs import RunMetadata


def load_run_metadata(path: Path) -> RunMetadata:
    metadata = RunMetadata.model_validate(json.loads(path.read_text(encoding="utf-8")))
    errors = validate_run_metadata(metadata)
    if errors:
        raise ValueError("; ".join(errors))
    if metadata.status != "valid":
        raise ValueError("only runs with status='valid' can be normalized")
    return metadata


def _event_id(
    run_id: str, source_file: str, line_number: int, record_number: int, line: str
) -> str:
    identity = (
        f"{run_id}\0{source_file}\0{line_number}\0{record_number}\0{line}".encode()
    )
    return "evt-" + hashlib.sha256(identity).hexdigest()[:24]


def normalize_log(
    log_path: Path, metadata: RunMetadata, source_type: str
) -> list[NormalizedEvent]:
    """Normalize one immutable raw log and join its trusted run label."""
    if log_path.name not in metadata.log_sources:
        raise ValueError(f"{log_path.name} is not declared in metadata.log_sources")

    events: list[NormalizedEvent] = []
    for line_number, record_number, line, parsed in parsed_lines(
        read_raw_log(log_path), source_type
    ):
        embedded_run_id = parsed.pop("embedded_run_id", None)
        if embedded_run_id is not None and embedded_run_id != metadata.run_id:
            continue
        timestamp = parsed["timestamp"]
        if not metadata.start_time <= timestamp <= metadata.end_time:
            continue
        events.append(
            NormalizedEvent(
                event_id=_event_id(
                    metadata.run_id, log_path.name, line_number, record_number, line
                ),
                run_id=metadata.run_id,
                raw_source_file=log_path.name,
                attack_label=metadata.expected_label,
                scenario=metadata.scenario,
                **parsed,
            )
        )
    return events


def normalize_manifest(manifest_path: Path) -> list[NormalizedEvent]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    events: list[NormalizedEvent] = []
    for run in manifest["runs"]:
        metadata = load_run_metadata(base / run["metadata"])
        normalized = normalize_log(base / run["log"], metadata, run["source_type"])
        if not normalized:
            raise ValueError(f"no events normalized for run {metadata.run_id}")
        events.extend(normalized)
    return events


def write_jsonl(events: list[NormalizedEvent], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as output:
        for event in events:
            output.write(json.dumps(event.model_dump(mode="json"), sort_keys=True) + "\n")

