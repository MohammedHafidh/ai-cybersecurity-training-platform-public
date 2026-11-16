import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.ingestion.pipeline import (
    load_run_metadata,
    normalize_log,
    normalize_manifest,
    write_jsonl,
)


FIXTURES = Path(__file__).parent / "fixtures" / "day7"


def test_manifest_normalizes_all_three_real_log_shapes():
    events = normalize_manifest(FIXTURES / "manifest.json")

    assert len(events) == 6
    assert {event.source_type for event in events} == {"auth", "web", "network"}
    assert {event.scenario for event in events} == {
        "benign",
        "brute_force",
        "sql_injection",
        "reconnaissance",
    }
    assert {event.attack_label for event in events} == {"benign", "malicious"}
    assert len({event.event_id for event in events}) == len(events)


def test_expected_fields_are_preserved():
    events = normalize_manifest(FIXTURES / "manifest.json")
    auth = next(event for event in events if event.source_type == "auth")
    web = next(event for event in events if event.scenario == "sql_injection")
    network = next(event for event in events if event.destination_port == 9090)

    assert (auth.username, auth.outcome, auth.source_ip) == (
        "student",
        "failure",
        "172.28.0.3",
    )
    assert web.request_data == "1 OR 1=1"
    assert (web.method, web.path, web.status_code) == ("GET", "/users", 200)
    assert (network.destination_port, network.protocol) == (9090, "tcp")


def test_label_is_joined_from_metadata_not_payload(tmp_path):
    source = FIXTURES / "web.log"
    raw_metadata = json.loads((FIXTURES / "web-benign-metadata.json").read_text())
    changed = deepcopy(raw_metadata)
    changed.update(
        run_id="day7-web-relabeled",
        scenario="sql_injection",
        expected_label="malicious",
    )
    log = tmp_path / "web.log"
    log.write_text(source.read_text().replace("day7-web-benign", "day7-web-relabeled"))
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(changed))

    metadata = load_run_metadata(metadata_path)
    event = normalize_log(log, metadata, "web")[0]
    assert event.attack_label == "malicious"
    assert event.scenario == "sql_injection"


def test_raw_log_is_not_modified_and_ids_are_deterministic():
    log = FIXTURES / "network.log"
    before = log.read_bytes()
    metadata = load_run_metadata(FIXTURES / "network-metadata.json")
    first = normalize_log(log, metadata, "network")
    second = normalize_log(log, metadata, "network")

    assert log.read_bytes() == before
    assert [event.event_id for event in first] == [event.event_id for event in second]


def test_cross_run_and_out_of_window_records_are_excluded():
    metadata = load_run_metadata(FIXTURES / "network-metadata.json")
    events = normalize_log(FIXTURES / "network.log", metadata, "network")
    assert {event.destination_port for event in events} == {8080, 9090}


def test_invalid_or_untrusted_metadata_is_rejected(tmp_path):
    raw = json.loads((FIXTURES / "auth-metadata.json").read_text())
    raw["status"] = "needs_review"
    raw["exclusion_reason"] = "awaiting security review"
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="status='valid'"):
        load_run_metadata(path)


def test_jsonl_output_is_round_trip_valid(tmp_path):
    events = normalize_manifest(FIXTURES / "manifest.json")
    output = tmp_path / "events.jsonl"
    write_jsonl(events, output)
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(records) == len(events)
    assert all(record["raw_source_file"] for record in records)


def test_concatenated_network_json_records_are_both_normalized(tmp_path):
    metadata = load_run_metadata(FIXTURES / "network-metadata.json")
    lines = (FIXTURES / "network.log").read_text().splitlines()
    log = tmp_path / "network.log"
    log.write_text(lines[0] + lines[1][lines[1].find("{"):] + "\n", encoding="utf-8")
    events = normalize_log(log, metadata, "network")
    assert {event.destination_port for event in events} == {8080, 9090}
    assert len({event.event_id for event in events}) == 2

