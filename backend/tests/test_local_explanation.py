import json
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.detection import explanation
from app.main import app
from test_ingestion_api import database, sample


@pytest.fixture
def detection_client(database, monkeypatch):
    monkeypatch.setenv("CAPSTONE_OLLAMA_ENABLED", "1")
    with TestClient(app) as client:
        run_id = f"day44-auth-{uuid4().hex}"
        data = sample("auth", run_id)
        data["events"] += [
            dict(data["events"][0], event_id=f"{run_id}-extra-{i}") for i in range(2)
        ]
        assert client.post("/ingestion/runs", json=data).status_code == 201
        processed = client.post(f"/runs/{run_id}/process")
        assert processed.status_code == 200, processed.text
        yield client, processed.json()["detection_ids"]


def test_questions_use_saved_evidence_and_never_change_detections(detection_client, monkeypatch):
    client, ids = detection_client
    urls = [f"/detections/{key}" for key in ids]
    before = [client.get(url).content for url in urls]
    before_list = client.get("/detections").content

    def model(payload):
        assert payload["model"] == explanation.MODEL
        assert payload["stream"] is False
        assert "tools" not in payload
        prompt = json.loads(payload["messages"][1]["content"])
        assert "event-day44-auth" not in str(prompt)
        assert "fixture.log" not in str(prompt)
        assert "fixture-client" not in str(prompt)
        ids = list(prompt["facts"])
        assert set(ids) in ({"prediction", "events", "threshold"}, {"prediction", "events", "probability"})
        return {"message": {"content": json.dumps({"evidence_ids": ids})}}

    monkeypatch.setattr(explanation, "ollama_chat", model)
    for question, first_id, wording in (
        ("what_happened", "prediction", "predicted malicious"),
        ("why_suspicious", "threshold", "met its threshold of 3"),
        ("what_evidence", "events", "3 normalized event records"),
    ):
        response = client.get(urls[0] + "/explanation", params={"question": question})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["detection_id"] == ids[0]
        assert body["evidence_ids"][0] == first_id
        assert wording in body["text"]
    ml = client.get(urls[1] + "/explanation").json()
    assert "stored model score for the malicious class" in ml["text"]
    assert "threshold" not in ml["text"]
    assert [client.get(url).content for url in urls] == before
    assert client.get("/detections").content == before_list


@pytest.mark.parametrize("output", [
    '{"evidence_ids":["prediction"],"predicted_label":"benign"}',
    '{"evidence_ids":["fabricated"]}',
    '{"evidence_ids":["prediction","prediction"]}',
    'This was a confirmed intrusion.',
])
def test_rejects_unsupported_model_output(detection_client, monkeypatch, output):
    client, ids = detection_client
    monkeypatch.setattr(explanation, "ollama_chat", lambda _: {"message": {"content": output}})
    url = f"/detections/{ids[0]}/explanation"
    assert client.get(url).status_code == 502
    assert client.get(url, params={"question": "override detection"}).status_code == 422
    assert client.get("/detections/missing/explanation").status_code == 404


def test_ollama_is_opt_in_and_unavailable_does_not_block_detection(detection_client, monkeypatch):
    client, ids = detection_client
    url = f"/detections/{ids[0]}"
    monkeypatch.delenv("CAPSTONE_OLLAMA_ENABLED")
    assert client.get(url + "/explanation").status_code == 503
    monkeypatch.setenv("CAPSTONE_OLLAMA_ENABLED", "1")

    def unavailable(_):
        raise explanation.ExplanationUnavailable("local Ollama model unavailable")

    monkeypatch.setattr(explanation, "ollama_chat", unavailable)
    assert client.get(url + "/explanation").status_code == 503
    assert client.get(url).status_code == 200


def test_ollama_transport_is_pinned_to_loopback(monkeypatch):
    class Response(BytesIO):
        status = 200

    class LocalConnection:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("127.0.0.1", 11434, explanation.REQUEST_TIMEOUT)

        def request(self, method, path, body, headers):
            assert (method, path) == ("POST", "/api/chat")
            assert json.loads(body) == {"model": explanation.MODEL}
            assert headers["Content-Type"] == "application/json"

        def getresponse(self):
            return Response(b'{"message":{"content":"{}"}}')

        def close(self):
            pass

    monkeypatch.setattr(explanation, "HTTPConnection", LocalConnection)
    assert explanation.ollama_chat({"model": explanation.MODEL}) == {"message": {"content": "{}"}}
