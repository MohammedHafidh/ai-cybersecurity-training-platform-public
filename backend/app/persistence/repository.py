from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.detections import DetectorComparison, RuleDetection
from app.models.ml import MLDetection, MLInferenceRequest
from app.persistence.database import (
    DetectorComparisonRecord,
    FeatureRunRecord,
    MLDetectionRecord,
    RuleDetectionRecord,
)


def save_comparison(
    session: Session,
    request: MLInferenceRequest,
    comparison: DetectorComparison,
) -> DetectorComparison:
    existing = session.scalar(
        select(DetectorComparisonRecord).where(
            DetectorComparisonRecord.run_id == request.run_id
        )
    )
    if existing:
        stored = get_comparison(session, request.run_id)
        if stored != comparison:
            raise ValueError("run ID already has a different stored comparison")
        return stored

    session.add(
        FeatureRunRecord(
            run_id=request.run_id,
            source_type=request.source_type,
            observed_features=request.model_dump(exclude={"run_id"}),
        )
    )
    session.flush()
    rule = comparison.rule_detection
    session.add(
        RuleDetectionRecord(
            detection_id=rule.detection_id,
            run_id=request.run_id,
            predicted_label=rule.predicted_label,
            predicted_scenario=rule.predicted_scenario,
            triggered_rule=rule.triggered_rule,
            evidence=[item.model_dump() for item in rule.evidence],
        )
    )
    ml = comparison.ml_detection
    session.add(
        MLDetectionRecord(
            detection_id=ml.detection_id,
            run_id=request.run_id,
            model_name=ml.model_name,
            model_sha256=ml.model_sha256,
            predicted_label=ml.predicted_label,
            malicious_probability=ml.malicious_probability,
            decision_threshold=ml.decision_threshold,
        )
    )
    session.flush()
    session.add(
        DetectorComparisonRecord(
            comparison_id=comparison.comparison_id,
            run_id=request.run_id,
            rule_detection_id=rule.detection_id,
            ml_detection_id=ml.detection_id,
            agreement=comparison.agreement,
            outcome=comparison.outcome,
            review_recommended=comparison.review_recommended,
        )
    )
    session.commit()
    return comparison


def get_comparison(session: Session, run_id: str) -> DetectorComparison | None:
    comparison = session.scalar(
        select(DetectorComparisonRecord).where(DetectorComparisonRecord.run_id == run_id)
    )
    if comparison is None:
        return None
    rule = session.get(RuleDetectionRecord, comparison.rule_detection_id)
    ml = session.get(MLDetectionRecord, comparison.ml_detection_id)
    if rule is None or ml is None:
        raise ValueError("stored comparison references missing detector records")
    return DetectorComparison(
        comparison_id=comparison.comparison_id,
        run_id=comparison.run_id,
        rule_detection=RuleDetection(
            detection_id=rule.detection_id,
            run_id=rule.run_id,
            predicted_label=rule.predicted_label,
            predicted_scenario=rule.predicted_scenario,
            triggered_rule=rule.triggered_rule,
            evidence=rule.evidence,
        ),
        ml_detection=MLDetection(
            detection_id=ml.detection_id,
            run_id=ml.run_id,
            model_name=ml.model_name,
            model_sha256=ml.model_sha256,
            predicted_label=ml.predicted_label,
            malicious_probability=ml.malicious_probability,
            decision_threshold=ml.decision_threshold,
        ),
        agreement=comparison.agreement,
        outcome=comparison.outcome,
        review_recommended=comparison.review_recommended,
    )
