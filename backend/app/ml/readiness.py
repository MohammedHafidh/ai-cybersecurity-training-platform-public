import json
from collections import Counter
from pathlib import Path

from app.models.features import RunFeatures
from app.models.readiness import DatasetReadinessReport, ReadinessCheck


ATTACK_SCENARIOS = {"brute_force", "sql_injection", "reconnaissance"}
SOURCE_TYPES = ("auth", "web", "network")
LABELS = ("benign", "malicious")
MINIMUM_SAMPLES_PER_LABEL = 5


def _check(
    check_id: str, passed: bool, observed: str, required: str, message: str
) -> ReadinessCheck:
    return ReadinessCheck(
        check_id=check_id,
        status="pass" if passed else "fail",
        observed=observed,
        required=required,
        message=message,
    )


def _feature_vector(row: RunFeatures) -> tuple:
    return (
        row.source_type,
        row.event_count,
        row.auth_attempt_count,
        row.failed_login_count,
        row.successful_login_count,
        row.unique_username_count,
        row.web_request_count,
        row.max_request_length,
        row.suspicious_token_count,
        row.connection_count,
        row.unique_destination_port_count,
    )


def audit_ml_readiness(rows: list[RunFeatures]) -> DatasetReadinessReport:
    label_counts = Counter(row.attack_label for row in rows)
    scenario_counts = Counter(row.scenario for row in rows)
    source_label_counts = {
        source: {
            label: sum(
                row.source_type == source and row.attack_label == label for row in rows
            )
            for label in LABELS
        }
        for source in SOURCE_TYPES
    }

    run_ids = [row.run_id for row in rows]
    feature_ids = [row.feature_id for row in rows]
    vectors: dict[tuple, set[str]] = {}
    for row in rows:
        vectors.setdefault(_feature_vector(row), set()).add(row.attack_label)
    conflicting_vectors = sum(len(labels) > 1 for labels in vectors.values())

    checks = [
        _check(
            "non_empty_dataset",
            bool(rows),
            str(len(rows)),
            ">= 1",
            "At least one trusted feature row is required.",
        ),
        _check(
            "unique_run_ids",
            len(run_ids) == len(set(run_ids)),
            f"{len(set(run_ids))} unique of {len(run_ids)}",
            "all unique",
            "A controlled run may appear only once.",
        ),
        _check(
            "unique_feature_ids",
            len(feature_ids) == len(set(feature_ids)),
            f"{len(set(feature_ids))} unique of {len(feature_ids)}",
            "all unique",
            "Feature artifacts may not be duplicated.",
        ),
        _check(
            "both_labels_present",
            all(label_counts[label] > 0 for label in LABELS),
            json.dumps(dict(sorted(label_counts.items())), sort_keys=True),
            "benign and malicious",
            "Binary training requires both trusted classes.",
        ),
        _check(
            "minimum_samples_per_label",
            all(label_counts[label] >= MINIMUM_SAMPLES_PER_LABEL for label in LABELS),
            json.dumps(dict(sorted(label_counts.items())), sort_keys=True),
            f">= {MINIMUM_SAMPLES_PER_LABEL} per label",
            "Each class needs enough independent runs for a small stratified split.",
        ),
        _check(
            "all_attack_scenarios_present",
            ATTACK_SCENARIOS.issubset(scenario_counts),
            json.dumps(dict(sorted(scenario_counts.items())), sort_keys=True),
            ", ".join(sorted(ATTACK_SCENARIOS)),
            "Every mandatory attack must be represented.",
        ),
        _check(
            "source_label_coverage",
            all(
                source_label_counts[source][label] > 0
                for source in SOURCE_TYPES
                for label in LABELS
            ),
            json.dumps(source_label_counts, sort_keys=True),
            "benign and malicious for auth, web, and network",
            "The model must not learn that a log source itself means malicious.",
        ),
        _check(
            "no_conflicting_feature_vectors",
            conflicting_vectors == 0,
            str(conflicting_vectors),
            "0",
            "Identical observable vectors may not carry conflicting labels.",
        ),
    ]
    blockers = [check.check_id for check in checks if check.status == "fail"]
    return DatasetReadinessReport(
        ready_for_training=not blockers,
        sample_count=len(rows),
        label_counts={label: label_counts[label] for label in LABELS},
        scenario_counts=dict(sorted(scenario_counts.items())),
        source_label_counts=source_label_counts,
        checks=checks,
        blockers=blockers,
    )


def write_readiness_report(report: DatasetReadinessReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

