import json
from pathlib import Path

import pytest

from app.detection.rules import detect_run, detect_runs, read_feature_jsonl, write_detection_jsonl
from app.ingestion.pipeline import normalize_manifest
from app.processing.features import build_run_features


FIXTURES = Path(__file__).parent / "fixtures" / "day7"


def feature_rows():
    return build_run_features(normalize_manifest(FIXTURES / "manifest.json"))


def test_rule_baseline_returns_one_decision_per_run():
    detections = detect_runs(feature_rows())
    assert len(detections) == 4
    assert len({detection.detection_id for detection in detections}) == 4
    assert sum(detection.predicted_label == "malicious" for detection in detections) == 3
    assert sum(detection.predicted_label == "benign" for detection in detections) == 1


def test_all_three_attack_rules_return_explainable_evidence():
    detections = detect_runs(feature_rows())
    observed = {
        detection.triggered_rule: detection.evidence[0].model_dump()
        for detection in detections
        if detection.triggered_rule
    }
    assert observed == {
        "AUTH_FAILED_LOGIN_BURST": {
            "feature": "failed_login_count",
            "observed": 2,
            "operator": ">=",
            "threshold": 2,
        },
        "WEB_SQL_TOKEN_PRESENT": {
            "feature": "suspicious_token_count",
            "observed": 1,
            "operator": ">=",
            "threshold": 1,
        },
        "NETWORK_MULTI_PORT_SCAN": {
            "feature": "unique_destination_port_count",
            "observed": 2,
            "operator": ">=",
            "threshold": 2,
        },
    }


def test_benign_decision_records_the_inspected_threshold():
    row = next(row for row in feature_rows() if row.scenario == "benign")
    detection = detect_run(row)
    assert detection.predicted_label == "benign"
    assert detection.predicted_scenario == "benign"
    assert detection.triggered_rule is None
    assert detection.evidence[0].feature == "suspicious_token_count"
    assert detection.evidence[0].observed == 0


def test_rule_prediction_does_not_read_ground_truth_label():
    row = next(row for row in feature_rows() if row.scenario == "sql_injection")
    relabeled = row.model_copy(update={"attack_label": "benign", "scenario": "benign"})
    assert detect_run(row).model_dump() == detect_run(relabeled).model_dump()


def test_below_threshold_attack_shapes_are_benign_predictions():
    rows = feature_rows()
    auth = next(row for row in rows if row.source_type == "auth").model_copy(
        update={"failed_login_count": 1}
    )
    network = next(row for row in rows if row.source_type == "network").model_copy(
        update={"unique_destination_port_count": 1}
    )
    assert detect_run(auth).predicted_label == "benign"
    assert detect_run(network).predicted_label == "benign"


def test_duplicate_run_ids_are_rejected():
    row = feature_rows()[0]
    with pytest.raises(ValueError, match="duplicate run IDs"):
        detect_runs([row, row])


def test_feature_reader_and_detection_writer_round_trip(tmp_path):
    rows = feature_rows()
    feature_path = tmp_path / "features.jsonl"
    feature_path.write_text(
        "".join(json.dumps(row.model_dump(mode="json")) + "\n" for row in rows)
    )
    output_path = tmp_path / "detections.jsonl"
    write_detection_jsonl(detect_runs(read_feature_jsonl(feature_path)), output_path)
    records = [json.loads(line) for line in output_path.read_text().splitlines()]
    assert len(records) == 4
    assert all("attack_label" not in record and "scenario" not in record for record in records)

