import hashlib

from app.detection.rules import detect_inference_request
from app.ml.inference import SelectedModel, predict_run
from app.models.detections import DetectorComparison
from app.models.ml import MLInferenceRequest


def compare_detectors(
    bundle: SelectedModel, request: MLInferenceRequest
) -> DetectorComparison:
    rule_detection = detect_inference_request(request)
    ml_detection = predict_run(bundle, request)
    agreement = rule_detection.predicted_label == ml_detection.predicted_label
    if not agreement:
        outcome = "detector_disagreement"
    elif rule_detection.predicted_label == "malicious":
        outcome = "consensus_malicious"
    else:
        outcome = "consensus_benign"
    identity = (
        f"{rule_detection.detection_id}\0{ml_detection.detection_id}".encode("utf-8")
    )
    return DetectorComparison(
        comparison_id="cmp-" + hashlib.sha256(identity).hexdigest()[:24],
        run_id=request.run_id,
        rule_detection=rule_detection,
        ml_detection=ml_detection,
        agreement=agreement,
        outcome=outcome,
        review_recommended=not agreement,
    )
