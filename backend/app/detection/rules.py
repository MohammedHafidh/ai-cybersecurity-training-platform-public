import hashlib
import json
from pathlib import Path

from app.models.detections import RuleDetection, RuleEvidence
from app.models.features import RunFeatures
from app.models.ml import MLInferenceRequest


RULES = {
    "auth": ("AUTH_FAILED_LOGIN_BURST", "brute_force", "failed_login_count", 2),
    "web": ("WEB_SQL_TOKEN_PRESENT", "sql_injection", "suspicious_token_count", 1),
    "network": (
        "NETWORK_MULTI_PORT_SCAN",
        "reconnaissance",
        "unique_destination_port_count",
        2,
    ),
}


def read_feature_jsonl(path: Path) -> list[RunFeatures]:
    rows: list[RunFeatures] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(RunFeatures.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"invalid feature row on line {line_number}: {exc}") from exc
    if not rows:
        raise ValueError("feature input is empty")
    return rows


def _detection_id(row: RunFeatures, rule_id: str | None) -> str:
    identity = f"{row.feature_id}\0{rule_id or 'NO_RULE'}".encode()
    return "det-" + hashlib.sha256(identity).hexdigest()[:24]


def detect_run(row: RunFeatures) -> RuleDetection:
    rule_id, scenario, feature, threshold = RULES[row.source_type]
    observed = getattr(row, feature)
    triggered = observed >= threshold
    return RuleDetection(
        detection_id=_detection_id(row, rule_id if triggered else None),
        run_id=row.run_id,
        predicted_label="malicious" if triggered else "benign",
        predicted_scenario=scenario if triggered else "benign",
        triggered_rule=rule_id if triggered else None,
        evidence=[
            RuleEvidence(
                feature=feature,
                observed=observed,
                threshold=threshold,
            )
        ],
    )


def detect_runs(rows: list[RunFeatures]) -> list[RuleDetection]:
    run_ids = [row.run_id for row in rows]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("feature input contains duplicate run IDs")
    return [detect_run(row) for row in sorted(rows, key=lambda value: value.run_id)]


def detect_inference_request(request: MLInferenceRequest) -> RuleDetection:
    """Apply the transparent baseline to the same unlabeled inputs used by ML."""
    rule_id, scenario, feature, threshold = RULES[request.source_type]
    observed = getattr(request, feature)
    triggered = observed >= threshold
    fingerprint = json.dumps(request.model_dump(), sort_keys=True, separators=(",", ":"))
    detection_id = "rule-det-" + hashlib.sha256(
        f"{fingerprint}\0{rule_id if triggered else 'NO_RULE'}".encode("utf-8")
    ).hexdigest()[:24]
    return RuleDetection(
        detection_id=detection_id,
        run_id=request.run_id,
        predicted_label="malicious" if triggered else "benign",
        predicted_scenario=scenario if triggered else "benign",
        triggered_rule=rule_id if triggered else None,
        evidence=[
            RuleEvidence(feature=feature, observed=observed, threshold=threshold)
        ],
    )


def write_detection_jsonl(detections: list[RuleDetection], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for detection in detections:
            output.write(
                json.dumps(detection.model_dump(mode="json"), sort_keys=True) + "\n"
            )

