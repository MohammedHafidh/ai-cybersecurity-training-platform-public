import json
from pathlib import Path

from app.ingestion.pipeline import normalize_manifest
from app.ml.readiness import audit_ml_readiness, write_readiness_report
from app.processing.features import build_run_features


FIXTURES = Path(__file__).parent / "fixtures" / "day7"


def feature_rows():
    return build_run_features(normalize_manifest(FIXTURES / "manifest.json"))


def test_current_lab_extract_is_correctly_blocked_from_training():
    report = audit_ml_readiness(feature_rows())
    assert report.ready_for_training is False
    assert report.sample_count == 4
    assert report.blockers == ["minimum_samples_per_label", "source_label_coverage"]


def test_report_quantifies_current_label_and_scenario_coverage():
    report = audit_ml_readiness(feature_rows())
    assert report.label_counts == {"benign": 1, "malicious": 3}
    assert report.scenario_counts == {
        "benign": 1,
        "brute_force": 1,
        "reconnaissance": 1,
        "sql_injection": 1,
    }
    assert report.source_label_counts["web"] == {"benign": 1, "malicious": 1}
    assert report.source_label_counts["auth"]["benign"] == 0
    assert report.source_label_counts["network"]["benign"] == 0


def test_duplicate_run_and_feature_ids_are_reported():
    row = feature_rows()[0]
    report = audit_ml_readiness([row, row])
    assert "unique_run_ids" in report.blockers
    assert "unique_feature_ids" in report.blockers


def test_conflicting_identical_vectors_are_reported():
    row = feature_rows()[0]
    conflict = row.model_copy(
        update={
            "feature_id": "feat-conflict",
            "run_id": "run-conflict",
            "attack_label": "benign",
            "scenario": "benign",
        }
    )
    report = audit_ml_readiness([row, conflict])
    assert "no_conflicting_feature_vectors" in report.blockers


def test_balanced_independent_lab_runs_pass_readiness():
    seeds = feature_rows()
    web_benign = next(row for row in seeds if row.source_type == "web" and row.attack_label == "benign")
    attack_by_source = {
        source: next(
            row for row in seeds if row.source_type == source and row.attack_label == "malicious"
        )
        for source in ("auth", "web", "network")
    }
    rows = []
    for index in range(5):
        for source in ("auth", "web", "network"):
            benign = web_benign.model_copy(
                update={
                    "feature_id": f"feat-{source}-benign-{index}",
                    "run_id": f"run-{source}-benign-{index}",
                    "source_type": source,
                }
            )
            if source == "auth":
                benign = benign.model_copy(update={"auth_attempt_count": 1, "successful_login_count": 1, "web_request_count": 0, "max_request_length": 0})
            if source == "network":
                benign = benign.model_copy(update={"connection_count": 1, "unique_destination_port_count": 1, "web_request_count": 0, "max_request_length": 0})
            attack = attack_by_source[source].model_copy(
                update={
                    "feature_id": f"feat-{source}-malicious-{index}",
                    "run_id": f"run-{source}-malicious-{index}",
                }
            )
            rows.extend([benign, attack])
    assert audit_ml_readiness(rows).ready_for_training is True


def test_report_output_is_deterministic_json(tmp_path):
    report = audit_ml_readiness(feature_rows())
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_readiness_report(report, first)
    write_readiness_report(report, second)
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text())["ready_for_training"] is False

