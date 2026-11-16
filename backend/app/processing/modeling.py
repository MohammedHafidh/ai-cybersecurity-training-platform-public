"""Scenario-specific modeling tables preserve each observation unit."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from app.ingestion.validation import validate_run_metadata
from app.processing.auth_features import build_auth_windows
from app.processing.network_features import build_network_windows
from app.processing.web_features import build_web_features


FEATURES = {
    "auth": {
        "attempt_count": ("integer", "Observed SSH password events in window"),
        "failed_login_count": ("integer", "Failed password events in window"),
        "successful_login_count": ("integer", "Successful password events in window"),
        "unique_username_count": ("integer", "Distinct observed usernames in window"),
        "attempts_per_second": ("number", "Attempt count divided by fixed 60 seconds"),
        "success_after_failure": ("boolean", "Success strictly later than failure in same window"),
    },
    "web": {
        "request_count": ("integer", "HTTP requests in run"),
        "missing_input_count": ("integer", "Requests without id input"),
        "empty_input_count": ("integer", "Requests with empty id input"),
        "max_request_length": ("integer", "Maximum decoded id character length; zero if absent"),
        "suspicious_token_count": ("integer", "Regex token matches; heuristic, never ground truth"),
        "residual_encoded_count": ("integer", "Requests retaining percent escapes after one decode"),
        "error_response_count": ("integer", "Responses with HTTP status at least 400"),
    },
    "network": {
        "connection_count": ("integer", "Connections accepted by logged services in window"),
        "unique_destination_port_count": ("integer", "Distinct observed listening ports in window"),
        "connections_per_second": ("number", "Connections divided by fixed 60 seconds"),
        "observed_span_seconds": ("number", "Last minus first connection timestamp"),
    },
}


def build_modeling_tables(events, metadata):
    ids = [event.event_id for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate normalized event IDs")
    observed_runs = {event.run_id for event in events}
    if observed_runs != set(metadata):
        raise ValueError("metadata and observed run coverage differ")
    source_by_run = {}
    for event in events:
        run = metadata[event.run_id]
        if validate_run_metadata(run) or run.status != "valid" or run.run_id != event.run_id:
            raise ValueError("invalid trusted metadata")
        if event.attack_label != run.expected_label or event.scenario != run.scenario:
            raise ValueError("trusted label disagreement")
        if event.timestamp.tzinfo is None or not run.start_time <= event.timestamp <= run.end_time:
            raise ValueError("event outside trusted time context")
        if event.raw_source_file not in run.log_sources:
            raise ValueError("undeclared raw evidence")
        if source_by_run.setdefault(event.run_id, event.source_type) != event.source_type:
            raise ValueError("mixed sources in one run")
    inputs = {
        "auth": build_auth_windows(events, metadata),
        "web": build_web_features(events),
        "network": [row.model_dump(mode="json") for row in build_network_windows(events, metadata)],
    }
    tables = {}
    for source, rows in inputs.items():
        table = []
        for row in rows:
            run = metadata[row["run_id"]]
            identity = json.dumps([source, row["run_id"], sorted(row["event_ids"])])
            record = dict(row_id=hashlib.sha256(identity.encode()).hexdigest()[:24],
                run_id=run.run_id, source_type=source,
                attack_label=run.expected_label, scenario=run.scenario,
                event_ids=sorted(row["event_ids"]),
                raw_source_files=sorted({e.raw_source_file for e in events if e.event_id in row["event_ids"]}))
            if source != "web":
                record.update(source_ip=row["source_ip"], target=row["target"],
                    window_start=row["window_start"], window_end=row["window_end"])
            for name, (kind, _) in FEATURES[source].items():
                value = row[name]
                if kind == "boolean" and type(value) is not bool:
                    raise ValueError("invalid boolean feature")
                if kind == "integer" and type(value) is not int:
                    raise ValueError("invalid integer feature")
                if kind != "boolean" and value < 0:
                    raise ValueError("negative feature")
                record[name] = value
            table.append(record)
        tables[source] = sorted(table, key=lambda r: (r["run_id"], r["row_id"]))
        consumed = [eid for row in table for eid in row["event_ids"]]
        expected = [e.event_id for e in events if e.source_type == source]
        if Counter(consumed) != Counter(expected):
            raise ValueError("events lost or counted twice in modeling table")
    return tables


def write_modeling_outputs(tables, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    dictionary, report = {}, {}
    for source, rows in tables.items():
        if not rows:
            raise ValueError(f"missing {source} table")
        columns = {}
        for name in rows[0]:
            if name in FEATURES[source]:
                kind, meaning = FEATURES[source][name]
                columns[name] = dict(type=kind, role="feature", definition=meaning,
                    encoding="0/1" if kind == "boolean" else "numeric; fit any scaling on training only")
            else:
                kind = "array[string]" if name in ("event_ids", "raw_source_files") else "string"
                role = "target" if name == "attack_label" else "context; excluded from model inputs"
                columns[name] = dict(type=kind, role=role,
                    definition={"attack_label": "Trusted run metadata label", "scenario": "Trusted scenario context; excluded to prevent label leakage",
                        "window_start": "Inclusive UTC window start", "window_end": "Exclusive UTC window end"}.get(name, "Identity or traceability context"),
                    encoding="benign=0, malicious=1" if name == "attack_label" else "not encoded as model input")
        dictionary[source] = dict(unit="run" if source == "web" else "run/source/target/60-second UTC window",
            columns=columns, feature_columns=list(FEATURES[source]))
        (output / f"{source}.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
        with (output / f"{source}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows({k: json.dumps(v) if isinstance(v, list) else v for k,v in row.items()} for row in rows)
        run_labels = {row["run_id"]: row["attack_label"] for row in rows}
        report[source] = dict(row_count=len(rows), run_count=len(run_labels),
            run_label_counts=dict(sorted(Counter(run_labels.values()).items())),
            row_label_counts=dict(sorted(Counter(row["attack_label"] for row in rows).items())),
            scenario_counts=dict(sorted(Counter(row["scenario"] for row in rows).items())),
            missingness={name: sum(row.get(name) is None for row in rows) for name in rows[0]})
    report["coverage_decision"] = "Adequate for Day 20 table construction: five runs per source/label. No further collection required for this gate. Small controlled templates remain insufficient for broad performance claims. Independent split review remains Day 21."
    for name, value in (("data-dictionary.json", dictionary), ("coverage-report.json", report)):
        (output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
    (output / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
