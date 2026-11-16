from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import sys

import pytest

from app.detection.auth_baseline import AuthWindowInput,detect_auth_window,detect_auth_windows,binary_metrics


def observation(failures=3,successes=0,**extra):
    start=datetime(2026,10,27,tzinfo=timezone.utc)
    return AuthWindowInput(**(dict(row_id="row",run_id="run",source_ip="172.20.0.2",target="auth-target",
        window_start=start,window_end=start+timedelta(seconds=60),attempt_count=failures+successes,
        failed_login_count=failures,successful_login_count=successes,
        event_ids=[str(i) for i in range(failures+successes)])|extra))


def test_threshold_and_benign_retry_boundary():
    assert not detect_auth_window(observation(1,2))["triggered"]
    assert not detect_auth_window(observation(2,1))["triggered"]
    assert detect_auth_window(observation(3))["triggered"]
    assert detect_auth_window(observation(4,2))["triggered"]
    evidence=detect_auth_window(observation())["evidence"]
    assert evidence["threshold"]==evidence["observed"]==3
    assert evidence["window_seconds"]==60


def test_documented_false_positive_and_false_negative_risks():
    # Synthetic unit cases, not reserved evidence: a legitimate three-typo burst
    # fires; a slow attack split into two subthreshold windows can evade.
    assert detect_auth_window(observation(3,1))["predicted_label"]=="malicious"
    assert not detect_auth_window(observation(2))["triggered"]
    assert not detect_auth_window(observation(2,row_id="next"))["triggered"]


@pytest.mark.parametrize("extra",[
    {"attack_label":"malicious"}, {"scenario":"brute_force"},
    {"attempt_count":99}, {"event_ids":["same"]*3},
    {"window_end":datetime(2026,10,27,0,2,tzinfo=timezone.utc)},
    {"window_start":datetime(2026,10,27)},
])
def test_invalid_or_labeled_detector_inputs_rejected(extra):
    with pytest.raises(ValueError):
        observation(**extra)


def test_duplicate_evidence_rejected():
    with pytest.raises(ValueError,match="duplicate"):
        detect_auth_windows([observation(),observation(row_id="other")])


def test_metrics_known_confusion_matrix():
    result=binary_metrics(["benign","benign","malicious","malicious"],
        ["benign","malicious","benign","malicious"])
    assert result["confusion_matrix"]==[[1,1],[1,1]]
    assert result["precision"]==result["recall"]==result["f1"]==result["false_positive_rate"]==0.5


def test_harness_reproducible_and_training_validation_only(tmp_path,monkeypatch):
    sys.path.insert(0,str(Path(__file__).parents[2]/"scripts"))
    from build_day24_auth_baseline import build
    original=Path.read_text
    def guard(path,*args,**kwargs):
        assert "reserved-final" not in str(path)
        assert not str(path).endswith("day21/test.json")
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"read_text",guard)
    first,second=tmp_path/"first",tmp_path/"second"
    build(first)
    build(second)
    assert {p.name:p.read_bytes() for p in first.iterdir()}=={p.name:p.read_bytes() for p in second.iterdir()}
    decisions=json.loads((first/"window-decisions.json").read_text())
    assert all("attack_label" not in row and "scenario" not in row for row in decisions)
    report=json.loads((first/"validation-report.json").read_text())
    assert report["metrics"]["train"]["run_metrics"]["sample_count"]==6
    assert report["metrics"]["validation"]["run_metrics"]["sample_count"]==2
