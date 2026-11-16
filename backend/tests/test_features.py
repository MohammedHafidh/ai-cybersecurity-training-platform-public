import csv
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.ingestion.pipeline import normalize_manifest
from app.processing.features import (
    build_run_features,
    read_normalized_jsonl,
    write_feature_csv,
    write_feature_jsonl,
)


FIXTURES = Path(__file__).parent / "fixtures" / "day7"


def fixture_events():
    return normalize_manifest(FIXTURES / "manifest.json")


def test_builds_one_feature_row_per_run():
    rows = build_run_features(fixture_events())
    assert len(rows) == 4
    assert {row.scenario for row in rows} == {
        "benign",
        "brute_force",
        "sql_injection",
        "reconnaissance",
    }
    assert len({row.feature_id for row in rows}) == 4


def test_authentication_features_are_correct():
    row = next(row for row in build_run_features(fixture_events()) if row.scenario == "brute_force")
    assert row.event_count == 2
    assert row.auth_attempt_count == 2
    assert row.failed_login_count == 2
    assert row.successful_login_count == 0
    assert row.unique_username_count == 2


def test_web_features_separate_observations_from_labels():
    rows = build_run_features(fixture_events())
    benign = next(row for row in rows if row.scenario == "benign")
    malicious = next(row for row in rows if row.scenario == "sql_injection")
    assert (benign.web_request_count, benign.suspicious_token_count) == (1, 0)
    assert (malicious.web_request_count, malicious.suspicious_token_count) == (1, 1)
    assert malicious.max_request_length == len("1 OR 1=1")
    assert malicious.attack_label == "malicious"


def test_network_features_are_correct():
    row = next(row for row in build_run_features(fixture_events()) if row.scenario == "reconnaissance")
    assert row.connection_count == 2
    assert row.unique_destination_port_count == 2


def test_features_are_deterministic_when_input_order_changes():
    events = fixture_events()
    first = build_run_features(events)
    second = build_run_features(list(reversed(events)))
    assert first == second


def test_inconsistent_ground_truth_within_run_is_rejected():
    events = fixture_events()
    changed = events[0].model_copy(update={"attack_label": "benign"})
    with pytest.raises(ValueError, match="inconsistent trusted context"):
        build_run_features([changed, events[1]])


def test_jsonl_reader_and_both_outputs_round_trip(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        "".join(json.dumps(event.model_dump(mode="json")) + "\n" for event in fixture_events())
    )
    rows = build_run_features(read_normalized_jsonl(events_path))
    jsonl_path = tmp_path / "features.jsonl"
    csv_path = tmp_path / "features.csv"
    write_feature_jsonl(rows, jsonl_path)
    write_feature_csv(rows, csv_path)

    json_records = [json.loads(line) for line in jsonl_path.read_text().splitlines()]
    with csv_path.open(newline="") as source:
        csv_records = list(csv.DictReader(source))
    assert len(json_records) == len(csv_records) == 4
    assert [record["run_id"] for record in json_records] == [
        record["run_id"] for record in csv_records
    ]

