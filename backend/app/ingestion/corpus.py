"""Deterministic corpus audit and immutable snapshot manifest; never repairs raw data."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from app.ingestion.parsers import parsed_lines
from app.ingestion.pipeline import _event_id
from app.ingestion.validation import validate_run_metadata
from app.models.events import NormalizedEvent
from app.models.runs import RunMetadata


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_corpus(manifest_path: Path):
    base = manifest_path.parent.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    events, ledger, provenance = [], [], []
    run_ids, seen = set(), set()
    counts = Counter()
    files = {"manifest.json": digest(manifest_path)}

    def resolve(name):
        path = (base / name).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError(f"missing/unsafe evidence path: {name}")
        files[str(path.relative_to(base)).replace("\\", "/")] = digest(path)
        return path

    for entry in manifest["runs"]:
        metadata_path = resolve(entry["metadata"])
        run = RunMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        errors = validate_run_metadata(run)
        if errors:
            raise ValueError(f"{run.run_id}: {errors}")
        if run.run_id in run_ids:
            raise ValueError(f"duplicate run ID: {run.run_id}")
        run_ids.add(run.run_id)
        log_path = resolve(entry["log"])
        for name in run.log_sources:
            resolve(name)
        if entry["log"] not in run.log_sources:
            raise ValueError("primary log must be declared")
        accepted_before = len(events)
        if run.status != "valid":
            ledger.append(dict(run_id=run.run_id, reason=run.exclusion_reason, status=run.status, scope="run"))
            counts["excluded_runs"] += 1
        else:
            for line_no, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
                counts["input_lines"] += 1
                try:
                    records = list(parsed_lines([line], entry["source_type"]))
                except (ValueError, KeyError, TypeError) as exc:
                    ledger.append(dict(run_id=run.run_id, line=line_no, reason="parse_error", detail=str(exc)))
                    counts["parse_error_lines"] += 1
                    continue
                if not records:
                    reason = "unparsed_candidate" if ("password for" in line or '"http_request"' in line or '"tcp_connection"' in line) else "background_or_non_event"
                    ledger.append(dict(run_id=run.run_id, line=line_no, reason=reason))
                    counts[reason] += 1
                for _, record_no, _, parsed in records:
                    counts["parsed_records"] += 1
                    embedded = parsed.pop("embedded_run_id", None)
                    timestamp = parsed["timestamp"]
                    reason = None
                    if embedded is not None and embedded != run.run_id:
                        reason = "other_run"
                    elif not run.start_time <= timestamp <= run.end_time:
                        reason = "outside_window"
                    key = json.dumps([run.run_id, parsed], default=str, sort_keys=True)
                    if not reason and key in seen:
                        reason = "duplicate_observation"
                    if reason:
                        counts[reason] += 1
                        ledger.append(dict(run_id=run.run_id, line=line_no, record=record_no, reason=reason))
                        continue
                    try:
                        event = NormalizedEvent(run_id=run.run_id,
                            event_id=_event_id(run.run_id, entry["log"], line_no, record_no, line),
                            raw_source_file=entry["log"], attack_label=run.expected_label, scenario=run.scenario, **parsed)
                        required = [event.source_ip]
                        if event.source_type == "auth":
                            required += [event.username, event.outcome]
                        if event.source_type == "network":
                            required += [event.destination_port, event.protocol]
                        if any(value is None or value == "" for value in required):
                            raise ValueError("missing required observation fields")
                    except ValueError as exc:
                        counts["invalid_record"] += 1
                        ledger.append(dict(run_id=run.run_id, line=line_no, record=record_no, reason="invalid_record", detail=str(exc)))
                        continue
                    seen.add(key)
                    events.append(event)
        provenance.append(dict(run_id=run.run_id, scenario=run.scenario, expected_label=run.expected_label,
            source_type=entry["source_type"], metadata=entry["metadata"], log=entry["log"],
            start_time=run.start_time.isoformat(), end_time=run.end_time.isoformat(), status=run.status,
            accepted_count=len(events)-accepted_before, exclusion_reason=run.exclusion_reason))
    counts["accepted_records"] = len(events)
    report = dict(counts= dict(sorted(counts.items())), coverage=dict(sorted(Counter(f"{e.source_type}:{e.attack_label}" for e in events).items())),
        missing_web_input_count=sum(e.source_type == "web" and e.request_data is None for e in events),
        policy="Exact semantic duplicates within a run are excluded; distinct timestamps remain distinct. All exclusions are logged. Unknown/malformed candidate lines require review.")
    snapshot = dict(version="raw-corpus-v0.1", files=dict(sorted(files.items())), runs=provenance)
    return events, ledger, report, snapshot


def freeze_corpus(manifest_path: Path, output: Path):
    events, ledger, report, snapshot = audit_corpus(manifest_path)
    if any(report["counts"].get(name, 0) for name in ("parse_error_lines", "unparsed_candidate", "invalid_record")):
        raise ValueError("unresolved corpus-quality errors prevent freeze")
    if set(report["coverage"]) != {f"{s}:{l}" for s in ("auth", "web", "network") for l in ("benign", "malicious")}:
        raise ValueError("all six source/label strata required")
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("provenance-manifest.json", snapshot), ("exclusion-ledger.json", ledger), ("corpus-quality-report.json", report)):
        (output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    from app.ingestion.pipeline import write_jsonl
    write_jsonl(events, output / "normalized-events.jsonl")
    return events, snapshot
