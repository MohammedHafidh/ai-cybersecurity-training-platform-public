from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.persistence.core import DetectionRecord, EventRecord, RunRecord
from test_ingestion_api import database, sample


@pytest.mark.parametrize(("family", "attributes", "rule_label"), [
    ("auth", [{"outcome": "failure"}, {"outcome": "success"}], "benign"),
    ("web", [{"request_data": "select a category", "status_code": 200}], "malicious"),
    ("network", [{"destination_port": 8080}, {"destination_port": 8080}], "benign"),
])
def test_benign_run_context_and_predictions_survive_round_trip(database, family, attributes, rule_label):
    run_id = f"day52-{family}-{uuid4().hex}"
    body = sample(family, run_id)
    run = body["run"]
    run.update(scenario="benign", expected_label="benign")
    template, = body["events"]
    body["events"] = [
        dict(template, **fields) | {"event_id": f"{run_id}-{i}", "scenario": "benign", "attack_label": "benign"}
        for i, fields in enumerate(attributes)
    ]
    event_ids = {event["event_id"] for event in body["events"]}
    with TestClient(app) as client:
        assert client.post("/ingestion/runs", json=body).status_code == 201
        processed = client.post(f"/runs/{run_id}/process")
        assert processed.status_code == 200, processed.text
        result = processed.json()
        assert result["result"]["ground_truth"] == {"scenario": "benign", "expected_label": "benign"}
        observation, = result["result"]["observations"]
        assert observation["rule"]["predicted_label"] == rule_label
        assert set(observation["event_ids"]) == event_ids
        with database() as session:
            stored_run = session.get(RunRecord, run_id)
            assert (stored_run.source, stored_run.target, stored_run.source_type) == (run["source"], run["target"], family)
            assert (stored_run.scenario, stored_run.expected_label) == ("benign", "benign")
            for event in body["events"]:
                row = session.get(EventRecord, event["event_id"])
                assert (row.run_id, row.source_type, row.raw_source_file) == (run_id, family, event["raw_source_file"])
                assert row.timestamp.replace(tzinfo=None) == datetime.fromisoformat(event["timestamp"]).replace(tzinfo=None)
                assert row.attributes["source_ip"] == event["source_ip"]
                assert {"attack_label", "scenario"}.isdisjoint(row.attributes)
            for key in result["detection_ids"]:
                stored = session.get(DetectionRecord, key)
                response = client.get(f"/detections/{key}")
                assert response.status_code == 200
                detail = response.json()
                assert detail["run"] == {
                    "source_type": family, **{k: run[k] for k in (
                        "source", "target", "scenario", "expected_label", "start_time", "end_time",
                    )},
                }
                assert detail["predicted_label"] == stored.predicted_label == observation[stored.detector]["predicted_label"]
                assert detail["evidence"] == stored.evidence
                assert set(detail["evidence"]["event_ids"]) == event_ids
                assert detail["event_id"] == (next(iter(event_ids)) if len(event_ids) == 1 else None)
                assert {"attack_label", "expected_label", "ground_truth"}.isdisjoint(detail["evidence"])
        print(f"{family}: rule={rule_label}, ML={observation['ml']['predicted_label']}")
