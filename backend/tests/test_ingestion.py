from pathlib import Path

from app.ingestion.raw_reader import read_raw_log
from app.ingestion.validation import validate_run_metadata
from app.models.runs import RunMetadata


FIXTURE = Path(__file__).parent / "fixtures" / "sample_auth.log"


def test_raw_reader_does_not_modify_source_file() -> None:
    before = FIXTURE.read_bytes()
    lines = read_raw_log(FIXTURE)
    after = FIXTURE.read_bytes()

    assert len(lines) == 2
    assert "Accepted password" in lines[0]
    assert before == after


def test_valid_run_metadata_has_no_errors() -> None:
    metadata = RunMetadata(
        run_id="auth-benign-001",
        scenario="benign",
        expected_label="benign",
        start_time="2026-10-06T10:00:00+04:00",
        end_time="2026-10-06T10:01:00+04:00",
        source="lab-client",
        target="auth-target",
        tool_or_method="normal SSH login",
        log_sources=["auth.log"],
        notes="Benign authentication fixture",
        status="valid",
    )

    assert validate_run_metadata(metadata) == []


def test_valid_sql_injection_metadata_has_no_errors() -> None:
    metadata = RunMetadata(
        run_id="web-sqli-001",
        scenario="sql_injection",
        expected_label="malicious",
        start_time="2026-10-17T10:00:00+04:00",
        end_time="2026-10-17T10:01:00+04:00",
        source="web-client",
        target="sql-target",
        tool_or_method="two fixed SQL-injection requests",
        log_sources=["web-server.log", "malicious-responses.jsonl"],
        status="valid",
    )

    assert validate_run_metadata(metadata) == []


def test_benign_scenario_rejects_malicious_label() -> None:
    metadata = RunMetadata(
        run_id="web-benign-wrong-label",
        scenario="benign",
        expected_label="malicious",
        start_time="2026-10-17T10:00:00+04:00",
        end_time="2026-10-17T10:01:00+04:00",
        source="web-client",
        target="sql-target",
        tool_or_method="two normal user lookups",
        log_sources=["web-server.log"],
        status="valid",
    )

    assert "benign scenario requires expected_label='benign'" in validate_run_metadata(
        metadata
    )


def test_attack_scenario_rejects_benign_label() -> None:
    metadata = RunMetadata(
        run_id="web-sqli-wrong-label",
        scenario="sql_injection",
        expected_label="benign",
        start_time="2026-10-17T10:00:00+04:00",
        end_time="2026-10-17T10:01:00+04:00",
        source="web-client",
        target="sql-target",
        tool_or_method="two fixed SQL-injection requests",
        log_sources=["web-server.log"],
        status="valid",
    )

    assert (
        "sql_injection scenario requires expected_label='malicious'"
        in validate_run_metadata(metadata)
    )


def test_invalid_time_range_is_reported() -> None:
    metadata = RunMetadata(
        run_id="auth-benign-bad-time",
        scenario="benign",
        expected_label="benign",
        start_time="2026-10-06T10:02:00+04:00",
        end_time="2026-10-06T10:01:00+04:00",
        source="lab-client",
        target="auth-target",
        tool_or_method="normal SSH login",
        log_sources=["auth.log"],
        status="valid",
    )

    assert "end_time must be on or after start_time" in validate_run_metadata(metadata)
