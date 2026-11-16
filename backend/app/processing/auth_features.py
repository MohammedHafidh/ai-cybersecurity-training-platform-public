"""Authentication counts grouped by run, source, target and fixed UTC window."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address

from app.ingestion.validation import validate_run_metadata


def build_auth_windows(events, metadata, window_seconds=60):
    if type(window_seconds) is not int or not 1 <= window_seconds <= 3600:
        raise ValueError("invalid window size")
    groups = defaultdict(list)
    seen = set()
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for event in events:
        if event.source_type != "auth":
            continue
        run = metadata.get(event.run_id)
        if run is None or validate_run_metadata(run) or run.status != "valid" or run.run_id != event.run_id:
            raise ValueError("invalid run metadata")
        if event.event_id in seen:
            raise ValueError("duplicate event ID")
        seen.add(event.event_id)
        if event.timestamp.tzinfo is None or not run.start_time <= event.timestamp <= run.end_time:
            raise ValueError("invalid event time")
        if event.raw_source_file not in run.log_sources or event.attack_label != run.expected_label or event.scenario != run.scenario:
            raise ValueError("inconsistent trusted context")
        if event.outcome not in ("success", "failure") or not event.username:
            raise ValueError("incomplete auth evidence")
        source = str(ip_address(event.source_ip or ""))
        bucket = (event.timestamp.astimezone(timezone.utc) - epoch) // timedelta(seconds=window_seconds)
        start = epoch + timedelta(seconds=bucket * window_seconds)
        groups[(event.run_id, source, run.target, start)].append(event)
    output = []
    for (run_id, source, target, start), members in sorted(groups.items()):
        ordered = sorted(members, key=lambda e: (e.timestamp, e.event_id))
        failures = sum(e.outcome == "failure" for e in members)
        output.append(dict(run_id=run_id, source_ip=source, target=target,
            window_start=start.isoformat(), window_end=(start + timedelta(seconds=window_seconds)).isoformat(),
            attempt_count=len(members), failed_login_count=failures,
            successful_login_count=len(members)-failures,
            unique_username_count=len({e.username for e in members}),
            attempts_per_second=len(members)/window_seconds,
            success_after_failure=any(e.outcome == "success" and any(f.outcome == "failure" and f.timestamp < e.timestamp for f in ordered) for e in ordered),
            event_ids=sorted(e.event_id for e in members)))
    return output
