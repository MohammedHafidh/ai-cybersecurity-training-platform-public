from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

import pytest
from sqlalchemy.exc import OperationalError

from app.detection import explanation, rag_explanation, routes
from test_day47_rag import stored_prediction
from test_ingestion_api import database


@pytest.mark.parametrize("hits", [
    [],
    [{"scenario": "web", "chunk_id": "irrelevant"}],
    [{"scenario": "brute_force", "chunk_id": "incomplete"}],
    [None],
])
def test_empty_or_invalid_retrieval_has_a_graceful_response(stored_prediction, monkeypatch, hits):
    client, ids = stored_prediction

    class Retriever:
        def search(self, *_args, **_kwargs):
            return hits

    monkeypatch.setattr(rag_explanation, "load_retriever", Retriever)
    monkeypatch.setattr(explanation, "ollama_chat", lambda _: pytest.fail("no valid context for the model"))
    url = f"/detections/{ids[0]}"
    before = client.get(url).json()
    response = client.get(url + "/rag-explanation")
    assert response.status_code == 503
    assert client.get(url).json() == before
    assert client.post(f"/runs/{before['run_id']}/process").status_code == 200


@pytest.mark.parametrize("failure", [ConnectionRefusedError, TimeoutError])
def test_transport_outage_and_timeout_leave_detection_usable(stored_prediction, monkeypatch, failure):
    client, ids = stored_prediction
    closed = []

    class Unavailable:
        def __init__(self, host, port, timeout):
            assert timeout == 45

        def request(self, *_args):
            raise failure("local failure")

        def close(self):
            closed.append(True)

    monkeypatch.setattr(explanation, "HTTPConnection", Unavailable)
    url = f"/detections/{ids[0]}"
    before = client.get(url).content
    response = client.get(url + "/explanation")
    assert response.status_code == 503
    assert response.json() == {"detail": "local Ollama model unavailable"}
    assert closed == [True]
    assert client.get(url).content == before


def test_detection_readback_works_while_explanation_waits(stored_prediction, monkeypatch):
    client, ids = stored_prediction
    started, release = Event(), Event()

    def waiting(_):
        started.set()
        assert release.wait(5)
        raise explanation.ExplanationUnavailable("local Ollama model unavailable")

    monkeypatch.setattr(explanation, "ollama_chat", waiting)
    url = f"/detections/{ids[0]}"
    before = client.get(url).content
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.get, url + "/explanation")
        try:
            assert started.wait(3)
            assert client.get(url).content == before
        finally:
            release.set()
        assert future.result().status_code == 503
    assert client.get(url).content == before


def test_database_outage_and_malformed_ingestion_are_graceful(stored_prediction, monkeypatch):
    client, ids = stored_prediction
    assert client.post("/ingestion/runs", json={"events": "invalid"}).status_code == 422

    @contextmanager
    def unavailable(_):
        raise OperationalError("connect", {}, Exception("private database failure"))
        yield

    with monkeypatch.context() as patch:
        patch.setattr(routes, "request_engine", unavailable)
        for path in ("/events", "/detections", f"/detections/{ids[0]}", f"/detections/{ids[0]}/rag-explanation"):
            response = client.get(path)
            assert response.status_code == 503
            assert "private" not in response.text
    assert client.get(f"/detections/{ids[0]}").status_code == 200
