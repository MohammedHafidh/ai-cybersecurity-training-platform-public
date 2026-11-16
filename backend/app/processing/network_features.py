"""Observed service connections in fixed UTC windows; not scan verdicts."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address

from pydantic import BaseModel

from app.models.events import NormalizedEvent
from app.models.runs import RunMetadata
from app.ingestion.validation import validate_run_metadata


class NetworkWindow(BaseModel):
    run_id: str
    source_ip: str
    target: str
    protocol: str
    window_start: datetime
    window_end: datetime
    connection_count: int
    unique_destination_port_count: int
    connections_per_second: float
    observed_span_seconds: float
    event_ids: list[str]
    raw_source_files: list[str]


def build_network_windows(
    events: list[NormalizedEvent], metadata: dict[str, RunMetadata], window_seconds: int = 60
) -> list[NetworkWindow]:
    if type(window_seconds) is not int or not 1 <= window_seconds <= 3600:
        raise ValueError("window_seconds must be an integer between 1 and 3600")
    grouped = defaultdict(list)
    seen = set()
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for event in events:
        if event.source_type != "network":
            continue
        run = metadata.get(event.run_id)
        if run is None or validate_run_metadata(run) or run.status != "valid":
            raise ValueError("missing or invalid trusted run metadata")
        if run.run_id != event.run_id or not run.target:
            raise ValueError("run identity or target missing")
        if event.event_id in seen:
            raise ValueError("duplicate event ID; resolve upstream before aggregation")
        seen.add(event.event_id)
        if event.timestamp.tzinfo is None or event.timestamp.utcoffset() is None:
            raise ValueError("timezone-aware timestamps required")
        if not run.start_time <= event.timestamp <= run.end_time:
            raise ValueError("event outside trusted run boundary")
        if event.attack_label != run.expected_label or event.scenario != run.scenario:
            raise ValueError("event disagrees with trusted context")
        if event.raw_source_file not in run.log_sources:
            raise ValueError("undeclared raw source file")
        if event.event_type != "tcp_connection" or event.protocol != "tcp" or event.destination_port is None:
            raise ValueError("complete TCP connection evidence required")
        source = str(ip_address(event.source_ip or ""))
        timestamp = event.timestamp.astimezone(timezone.utc)
        bucket = (timestamp - epoch) // timedelta(seconds=window_seconds)
        start = epoch + timedelta(seconds=bucket * window_seconds)
        grouped[(event.run_id, source, run.target, event.protocol, start)].append(event)
    result = []
    for (run_id, source, target, protocol, start), members in sorted(grouped.items()):
        times = [event.timestamp for event in members]
        result.append(NetworkWindow(
            run_id=run_id, source_ip=source, target=target, protocol=protocol,
            window_start=start, window_end=start + timedelta(seconds=window_seconds),
            connection_count=len(members),
            unique_destination_port_count=len({event.destination_port for event in members}),
            connections_per_second=len(members) / window_seconds,
            observed_span_seconds=(max(times) - min(times)).total_seconds(),
            event_ids=sorted(event.event_id for event in members),
            raw_source_files=sorted({event.raw_source_file for event in members}),
        ))
    return result
