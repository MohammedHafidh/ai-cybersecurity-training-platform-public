from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys

import pytest

from app.detection.scenario_baselines import WebRunInput,NetworkWindowInput,detect_web_run,detect_network_window,detect_scenario_rows
from app.models.events import NormalizedEvent
from app.processing.web_features import build_web_features


def web_observation(value):
    event=NormalizedEvent(event_id="event",run_id="run",timestamp="2026-10-28T00:00:00Z",
        source_type="web",event_type="http_request",source_ip="172.20.0.2",request_data=value,
        raw_source_file="web.log",attack_label="benign",scenario="benign")
    features=build_web_features([event])[0]
    return WebRunInput(row_id="row",**{name:features[name] for name in ("run_id","event_ids","request_count","suspicious_token_count")})


@pytest.mark.parametrize("payload",["1 OR 2=2","0 UNION SELECT 4,'guest','visitor'","1 -- trailing","/* marker */1"])
def test_sql_rule_uses_token_features_across_payload_shapes(payload):
    assert detect_web_run(web_observation(payload))["triggered"]


@pytest.mark.parametrize("value",["1","003",None,"","1 OR word"])
def test_normal_missing_and_benign_lookalikes_without_matching_tokens(value):
    assert not detect_web_run(web_observation(value))["triggered"]


def test_sql_keyword_false_positive_is_explicit_not_silently_suppressed():
    result=detect_web_run(web_observation("select a product"))
    assert result["triggered"]
    assert result["evidence"]["threshold"]==1
    assert "attack_label" not in result


def network(ports=2,count=2,**updates):
    start=datetime(2026,10,28,tzinfo=timezone.utc)
    return NetworkWindowInput(**(dict(row_id="row",run_id="run",source_ip="172.20.0.2",target="recon-target",
        window_start=start,window_end=start+timedelta(seconds=60),connection_count=count,
        unique_destination_port_count=ports,event_ids=[str(i) for i in range(count)])|updates))


def test_scan_threshold_and_legitimate_burst_limitations():
    assert not detect_network_window(network(1,20))["triggered"]
    assert detect_network_window(network(2,2))["triggered"]
    assert detect_network_window(network(3,5))["triggered"]
    # Legitimate two-port maintenance is indistinguishable using this feature alone.
    assert detect_network_window(network(2,6))["predicted_label"]=="malicious"


@pytest.mark.parametrize("changes",[
    {"attack_label":"benign"},{"scenario":"reconnaissance"},
    {"unique_destination_port_count":3},{"connection_count":0},
    {"window_start":datetime(2026,10,28)},
    {"window_end":datetime(2026,10,28,0,2,tzinfo=timezone.utc)},
])
def test_invalid_and_labeled_network_inputs_rejected(changes):
    with pytest.raises(ValueError):
        network(**changes)


def test_dispatcher_rejects_mismatched_sources_and_duplicate_evidence():
    with pytest.raises(ValueError,match="mismatch"):
        detect_scenario_rows("web",[network()])
    with pytest.raises(ValueError,match="duplicate"):
        detect_scenario_rows("network",[network(),network(row_id="other")])
    with pytest.raises(ValueError):
        WebRunInput(row_id="row",run_id="run",request_count=2,event_ids=["only-one"],suspicious_token_count=0)


def test_all_three_harness_outputs_reproducible_and_isolated(tmp_path,monkeypatch):
    sys.path.insert(0,str(Path(__file__).parents[2]/"scripts"))
    from build_day25_rules import build
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
    decisions=json.loads((first/"observation-decisions.json").read_text())
    assert {d["source_type"] for d in decisions}=={"auth","web","network"}
    assert all("attack_label" not in d and "scenario" not in d for d in decisions)
    previous=json.loads((Path(__file__).parents[2]/"data/processed/day24/window-decisions.json").read_text())
    assert [{k:v for k,v in d.items() if k!="source_type"} for d in decisions if d["source_type"]=="auth"]==previous
    report=json.loads((first/"validation-report.json").read_text())
    assert report["metrics"]["train"]["overall_run_metrics"]["sample_count"]==18
    assert report["metrics"]["validation"]["overall_run_metrics"]["sample_count"]==6
