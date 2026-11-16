import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.ingestion.corpus import audit_corpus
from app.ingestion.parsers import parse_web_line
from app.ingestion.validation import validate_run_metadata
from app.models.events import NormalizedEvent
from app.models.runs import RunMetadata
from app.processing.auth_features import build_auth_windows
from app.processing.web_features import build_web_features


START = datetime(2026, 10, 22, tzinfo=timezone.utc)


def metadata():
    return RunMetadata(run_id="retry", scenario="benign", expected_label="benign",
        start_time=START, end_time=START + timedelta(minutes=2), source="client",
        target="auth-target", tool_or_method="one typo then success", log_sources=["auth.log"])


def auth(n, seconds, outcome="failure", source="172.20.0.2"):
    return NormalizedEvent(event_id=str(n), run_id="retry", timestamp=START + timedelta(seconds=seconds),
        source_type="auth", event_type="ssh_password", source_ip=source, username="student",
        outcome=outcome, raw_source_file="auth.log", attack_label="benign", scenario="benign")


def test_retry_and_boundary_and_source_separation():
    events = [auth(1, 0), auth(2, 2, "success"), auth(3, 60), auth(4, 2, source="172.20.0.3")]
    rows = build_auth_windows(events, {"retry": metadata()})
    retry = next(row for row in rows if row["attempt_count"] == 2)
    assert retry["failed_login_count"] == retry["successful_login_count"] == 1
    assert retry["success_after_failure"]
    assert retry["attempts_per_second"] == 2 / 60
    assert len(rows) == 3
    assert rows == build_auth_windows(list(reversed(events)), {"retry": metadata()})
    with pytest.raises(ValueError, match="duplicate"):
        build_auth_windows([events[0], events[0]], {"retry": metadata()})


@pytest.mark.parametrize("updates", [
    {"source": " "}, {"target": ""}, {"run_id": ""},
    {"start_time": START.replace(tzinfo=None)},
    {"log_sources": ["../secret"]}, {"log_sources": ["auth.log", "auth.log"]},
    {"status": "needs_review"},
])
def test_metadata_bad_inputs_report_errors(updates):
    assert validate_run_metadata(metadata().model_copy(update=updates))


@pytest.mark.parametrize("query,value", [("id=1%20OR%201%3D1", "1 OR 1=1"), ("id=%2531", "%31"), ("", None), ("id=", "")])
def test_raw_query_decoded_once_missing_distinct_from_empty(query, value):
    record = dict(event_type="http_request", timestamp=START.isoformat(), raw_query=query)
    assert parse_web_line(json.dumps(record))["request_data"] == value


def test_already_decoded_input_not_decoded_again():
    record = dict(event_type="http_request", timestamp=START.isoformat(), id_input="%31", raw_query="id=%2531")
    assert parse_web_line(json.dumps(record))["request_data"] == "%31"


def test_benign_web_lookalike_is_observed_without_relabeling():
    events = [NormalizedEvent(event_id=str(i), run_id="web", timestamp=START,
        source_type="web", event_type="http_request", source_ip="172.20.0.2",
        request_data=value, status_code=400, raw_source_file="web.log",
        attack_label="benign", scenario="benign")
        for i, value in enumerate(["select", None, "", "%31"])]
    row = build_web_features(events)[0]
    assert row["missing_input_count"] == row["empty_input_count"] == 1
    assert row["suspicious_token_count"] == row["residual_encoded_count"] == 1
    assert row["error_response_count"] == 4
    assert all(e.attack_label == "benign" for e in events)


def corpus(tmp_path):
    source = Path(__file__).parent / "fixtures" / "day7"
    shutil.copytree(source, tmp_path / "corpus")
    return tmp_path / "corpus" / "manifest.json"


def test_corpus_duplicate_exclusion_and_raw_immutability(tmp_path):
    manifest = corpus(tmp_path)
    entry = json.loads(manifest.read_text())["runs"][0]
    log = manifest.parent / entry["log"]
    original = log.read_text()
    log.write_text(original + "\n" + original)
    before = log.read_bytes()
    events, ledger, report, snapshot = audit_corpus(manifest)
    assert log.read_bytes() == before
    assert any(row["reason"] == "duplicate_observation" for row in ledger)
    assert report["counts"]["accepted_records"] == len(events)
    assert snapshot["files"]


def test_duplicate_run_identity_rejected(tmp_path):
    manifest = corpus(tmp_path)
    data = json.loads(manifest.read_text())
    data["runs"].append(data["runs"][0])
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="duplicate run"):
        audit_corpus(manifest)


def test_excluded_run_stays_in_provenance_and_ledger(tmp_path):
    manifest = corpus(tmp_path)
    entry = json.loads(manifest.read_text())["runs"][0]
    path = manifest.parent / entry["metadata"]
    run = json.loads(path.read_text())
    run.update(status="excluded", exclusion_reason="ambiguous timing reviewed")
    path.write_text(json.dumps(run))
    events, ledger, _, snapshot = audit_corpus(manifest)
    assert not any(event.run_id == run["run_id"] for event in events)
    assert any(row.get("scope") == "run" for row in ledger)
    assert snapshot["runs"][0]["status"] == "excluded"
