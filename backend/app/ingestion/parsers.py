import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import parse_qs


AUTH_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})).*?"
    r"(?P<outcome>Accepted|Failed) password for (?:invalid user )?"
    r"(?P<username>\S+) from (?P<source_ip>[0-9a-fA-F:.]+) port \d+ ssh2"
)


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def parse_auth_line(line: str) -> dict[str, Any] | None:
    """Parse one timestamped OpenSSH password event."""
    match = AUTH_PATTERN.search(line)
    if not match:
        return None
    outcome = match.group("outcome")
    return {
        "timestamp": parse_timestamp(match.group("timestamp")),
        "source_type": "auth",
        "event_type": "ssh_password",
        "source_ip": match.group("source_ip"),
        "username": match.group("username"),
        "outcome": "success" if outcome == "Accepted" else "failure",
    }


def _json_records(line: str):
    """Yield every JSON object, including objects concatenated by concurrent logs."""
    decoder = json.JSONDecoder()
    position = line.find("{")
    while position >= 0:
        try:
            value, consumed = decoder.raw_decode(line[position:])
        except json.JSONDecodeError:
            position = line.find("{", position + 1)
            continue
        if isinstance(value, dict):
            yield value
        position = line.find("{", position + consumed)


def parse_web_line(line: str) -> dict[str, Any] | None:
    """Parse one structured Day 5 HTTP request record."""
    return next(parse_web_records(line), None)


def parse_web_records(line: str):
    for record in _json_records(line):
        if record.get("event_type") != "http_request":
            continue
        # id_input is already decoded by the target. Decode raw query exactly once
        # only when that field is absent; missing input remains explicitly missing.
        value = record.get("id_input")
        if value is None:
            value = parse_qs(record.get("raw_query") or "", keep_blank_values=True).get("id", [None])[0]
        yield {
            "timestamp": parse_timestamp(record["timestamp"]),
            "source_type": "web",
            "event_type": "http_request",
            "source_ip": record.get("source_ip"),
            "method": record.get("method"),
            "path": record.get("path"),
            "request_data": value,
            "status_code": record.get("status_code"),
            "embedded_run_id": record.get("run_id"),
        }


def parse_network_line(line: str) -> dict[str, Any] | None:
    """Parse one structured Day 6 TCP connection record."""
    return next(parse_network_records(line), None)


def parse_network_records(line: str):
    for record in _json_records(line):
        if record.get("event_type") != "tcp_connection":
            continue
        yield {
            "timestamp": parse_timestamp(record["timestamp"]),
            "source_type": "network",
            "event_type": "tcp_connection",
            "source_ip": record.get("source_ip"),
            "destination_port": record.get("destination_port"),
            "protocol": record.get("protocol"),
            "request_data": record.get("request_line") or None,
            "embedded_run_id": record.get("run_id"),
        }


PARSERS = {
    "auth": lambda line: [parsed] if (parsed := parse_auth_line(line)) else [],
    "web": parse_web_records,
    "network": parse_network_records,
}


def parsed_lines(lines: Iterable[str], source_type: str):
    try:
        parser = PARSERS[source_type]
    except KeyError as exc:
        raise ValueError(f"unsupported source_type: {source_type}") from exc
    for line_number, line in enumerate(lines, start=1):
        for record_number, parsed in enumerate(parser(line), start=1):
            yield line_number, record_number, line, parsed

