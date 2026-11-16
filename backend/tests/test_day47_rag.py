import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.detection import explanation, rag_explanation
from app.main import app
from test_ingestion_api import database, sample


@pytest.fixture
def stored_prediction(database, monkeypatch):
    monkeypatch.setenv("CAPSTONE_OLLAMA_ENABLED", "1")
    run_id = f"day47-{uuid4().hex}"
    with TestClient(app) as client:
        capture = sample("auth", run_id)
        capture["events"] += [dict(capture["events"][0], event_id=f"{run_id}-{i}") for i in range(2)]
        assert client.post("/ingestion/runs", json=capture).status_code == 201
        result = client.post(f"/runs/{run_id}/process")
        assert result.status_code == 200, result.text
        yield client, result.json()["detection_ids"]


def test_rag_uses_relevant_frozen_citations_and_keeps_prediction_unchanged(stored_prediction, monkeypatch):
    client, (rule_id, ml_id) = stored_prediction
    detail = f"/detections/{rule_id}"
    before = client.get(detail).content
    before_ml = client.get(f"/detections/{ml_id}").content
    artifact = Path(__file__).resolve().parents[2] / "data/knowledge/day45/chunks.json"
    chunks = json.loads(artifact.read_text(encoding="utf-8"))["chunks"]
    expected = next(chunk for chunk in chunks if chunk["chunk_id"] == "v1:brute_force:02")

    class RankedCorpus:
        def search(self, query, top_k):
            assert "SSH failed password attempts" in query
            assert top_k == 6
            return list(reversed(chunks))

    def model(payload):
        prompt = json.loads(payload["messages"][1]["content"])
        assert set(prompt["trusted_context"]) == {"v1:brute_force:01", expected["chunk_id"]}
        assert prompt["trusted_context"][expected["chunk_id"]] == expected["text"]
        assert "fixture.log" not in str(prompt)
        assert "fixture-client" not in str(prompt)
        return {"message": {"content": json.dumps({"evidence_ids": [expected["chunk_id"], "events"]})}}

    monkeypatch.setattr(rag_explanation, "load_retriever", RankedCorpus)
    monkeypatch.setattr(explanation, "ollama_chat", model)
    response = client.get(detail + "/rag-explanation", params={"question": "Why was this suspicious?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "grounded"
    assert body["evidence_ids"] == ["threshold", "events"]
    assert "met its threshold of 3" in body["text"]
    citation, = body["sources"]
    assert all(expected[key] == value for key, value in citation.items())
    assert client.get(detail).content == before
    assert client.get(f"/detections/{ml_id}").content == before_ml


def test_unsupported_questions_bypass_retrieval_and_ollama(stored_prediction, monkeypatch):
    client, (rule_id, ml_id) = stored_prediction

    def unused(*_):
        pytest.fail("unsupported questions must not call the retriever or local model")

    monkeypatch.setattr(rag_explanation, "load_retriever", unused)
    monkeypatch.setattr(explanation, "ollama_chat", unused)
    for key, question in ((rule_id, "Did the login succeed and whose account was compromised?"), (ml_id, "why_suspicious")):
        response = client.get(f"/detections/{key}/rag-explanation", params={"question": question})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "unsupported"
        assert body["model"] is None
        assert body["evidence_ids"] == body["sources"] == []
        assert question not in body["text"]


def test_rag_reports_unavailable_retrieval(stored_prediction, monkeypatch):
    client, (rule_id, _) = stored_prediction

    def missing():
        raise FileNotFoundError("missing local index")

    monkeypatch.setattr(rag_explanation, "load_retriever", missing)
    assert client.get(f"/detections/{rule_id}/rag-explanation").status_code == 503
    assert client.get(f"/detections/{rule_id}").status_code == 200


def test_rag_rejects_a_model_citation_outside_retrieved_context(stored_prediction, monkeypatch):
    client, (rule_id, _) = stored_prediction
    artifact = Path(__file__).resolve().parents[2] / "data/knowledge/day45/chunks.json"
    chunks = json.loads(artifact.read_text(encoding="utf-8"))["chunks"]

    class Corpus:
        def search(self, *_args, **_kwargs):
            return chunks

    monkeypatch.setattr(rag_explanation, "load_retriever", Corpus)
    monkeypatch.setattr(explanation, "ollama_chat", lambda _: {
        "message": {"content": '{"evidence_ids":["prediction","v1:sql_injection:01"]}'},
    })
    assert client.get(f"/detections/{rule_id}/rag-explanation").status_code == 502


def test_saved_index_to_rag_endpoint(stored_prediction, monkeypatch):
    pytest.importorskip("faiss")
    from app.detection.retrieval import load_encoder

    load_encoder(local_files_only=False)
    client, (rule_id, _) = stored_prediction

    def model(payload):
        prompt = json.loads(payload["messages"][1]["content"])
        return {"message": {"content": json.dumps({"evidence_ids": ["prediction", next(iter(prompt["trusted_context"]))]})}}

    monkeypatch.setattr(explanation, "ollama_chat", model)
    response = client.get(f"/detections/{rule_id}/rag-explanation")
    assert response.status_code == 200, response.text
    source, = response.json()["sources"]
    assert source["chunk_id"].startswith("v1:brute_force:")
    assert any(ref["location"] == "https://attack.mitre.org/techniques/T1110/" for ref in source["references"])
