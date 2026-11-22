"""Typed, bounded projections of accepted events. Originals never leave private storage."""
import hashlib
import json


def safe_input(value):
    # Exact approved lab inputs only. Unknown content may contain secrets or instructions.
    approved = {"1 OR 1=1", "1", "2", "select a category"}
    return value if value in approved else f"[input redacted; {len(value or '')} characters]"


def projection(events):
    output = []
    for i, event in enumerate(events[:100]):
        timestamp = event.timestamp.isoformat()
        normalized = {"event_id":event.event_id, "timestamp":timestamp, "event_type":event.event_type, "source":"source A"}
        if event.source_type == "auth":
            normalized.update(username="learner A", outcome=event.outcome)
            line = f"{timestamp} sshd: {'Failed' if event.outcome == 'failure' else 'Accepted'} password for [learner A] from [source A]"
        elif event.source_type == "web":
            normalized.update(method="GET", path="/users", request_data=safe_input(event.request_data), status_code=event.status_code)
            line = f"{timestamp} HTTP GET /users input={safe_input(event.request_data)!r} status={event.status_code}"
        else:
            normalized.update(destination_port=event.destination_port, protocol=event.protocol)
            line = f"{timestamp} TCP accepted from [source A] destination_port={event.destination_port}"
        output.append({"number":i+1, "event_id":event.event_id, "sanitized_log":line, "normalized":normalized})
    return {"records":output, "total_records":len(events), "redaction_notice":"Sanitized log projection: source addresses and usernames replaced. Only accepted events are shown; originals remain private.", "projection_sha256":hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest()}
