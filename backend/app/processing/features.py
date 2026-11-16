import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from app.models.events import NormalizedEvent
from app.models.features import RunFeatures


SUSPICIOUS_SQL_TOKENS = re.compile(
    r"(?:\bunion\b|\bselect\b|\bor\b\s+\S+\s*=|--|/\*|\*/)",
    re.IGNORECASE,
)


def read_normalized_jsonl(path: Path) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(NormalizedEvent.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"invalid normalized event on line {line_number}: {exc}") from exc
    if not events:
        raise ValueError("normalized event input is empty")
    return events


def _feature_id(run_id: str, events: list[NormalizedEvent]) -> str:
    event_ids = "\0".join(sorted(event.event_id for event in events))
    return "feat-" + hashlib.sha256(f"{run_id}\0{event_ids}".encode()).hexdigest()[:24]


def build_run_features(events: list[NormalizedEvent]) -> list[RunFeatures]:
    """Aggregate normalized observations without changing their trusted labels."""
    grouped: dict[str, list[NormalizedEvent]] = defaultdict(list)
    for event in events:
        grouped[event.run_id].append(event)

    rows: list[RunFeatures] = []
    for run_id in sorted(grouped):
        run_events = sorted(grouped[run_id], key=lambda event: (event.timestamp, event.event_id))
        labels = {event.attack_label for event in run_events}
        scenarios = {event.scenario for event in run_events}
        source_types = {event.source_type for event in run_events}
        if len(labels) != 1 or len(scenarios) != 1 or len(source_types) != 1:
            raise ValueError(f"run {run_id} contains inconsistent trusted context")

        usernames = {event.username for event in run_events if event.username}
        ports = {
            event.destination_port
            for event in run_events
            if event.destination_port is not None
        }
        request_values = [event.request_data or "" for event in run_events if event.source_type == "web"]
        rows.append(
            RunFeatures(
                feature_id=_feature_id(run_id, run_events),
                run_id=run_id,
                window_start=run_events[0].timestamp,
                window_end=run_events[-1].timestamp,
                source_type=next(iter(source_types)),
                event_count=len(run_events),
                auth_attempt_count=sum(event.source_type == "auth" for event in run_events),
                failed_login_count=sum(event.outcome == "failure" for event in run_events),
                successful_login_count=sum(event.outcome == "success" for event in run_events),
                unique_username_count=len(usernames),
                web_request_count=len(request_values),
                max_request_length=max((len(value) for value in request_values), default=0),
                suspicious_token_count=sum(
                    len(SUSPICIOUS_SQL_TOKENS.findall(value)) for value in request_values
                ),
                connection_count=sum(event.source_type == "network" for event in run_events),
                unique_destination_port_count=len(ports),
                attack_label=next(iter(labels)),
                scenario=next(iter(scenarios)),
            )
        )
    return rows


def write_feature_jsonl(rows: list[RunFeatures], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(json.dumps(row.model_dump(mode="json"), sort_keys=True) + "\n")


def write_feature_csv(rows: list[RunFeatures], path: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty feature table")
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [row.model_dump(mode="json") for row in rows]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

