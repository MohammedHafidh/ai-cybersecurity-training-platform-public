import json
import shutil

import pytest

faiss = pytest.importorskip("faiss")
import numpy as np

from app.detection.retrieval import INDEX_DIR, Retriever, build_index, read_corpus


@pytest.fixture(scope="module")
def retriever(tmp_path_factory):
    rebuilt = tmp_path_factory.mktemp("faiss-rebuild")
    build_index(rebuilt)
    saved = Retriever()
    fresh = faiss.read_index(str(rebuilt / "index.faiss"))
    np.testing.assert_allclose(
        saved._index.reconstruct_n(0, saved._index.ntotal),
        fresh.reconstruct_n(0, fresh.ntotal),
        atol=5e-5, rtol=0,
    )
    return saved


@pytest.mark.parametrize(("query", "scenario"), [
    ("Could repeated failed SSH password logins point to brute force?", "brute_force"),
    ("Do SQL injection token matches prove that a database query changed?", "sql_injection"),
    ("What do connections to several destination ports indicate during network service discovery?", "reconnaissance"),
])
def test_relevant_chunks_keep_frozen_citations(retriever, query, scenario):
    chunks, _ = read_corpus()
    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    results = retriever.search(query)
    assert len(results) == 2
    assert all(hit["scenario"] == scenario for hit in results)
    assert results[0]["score"] >= results[1]["score"]
    for hit in results:
        assert {key: value for key, value in hit.items() if key != "score"} == by_id[hit["chunk_id"]]
        assert hit["references"]


def test_bounds_and_full_mapping(retriever):
    with pytest.raises(ValueError, match="nonempty"):
        retriever.search(" ")
    with pytest.raises(ValueError, match="positive integer"):
        retriever.search("authentication", 0)
    assert len(retriever.search("authentication", 1)) == 1
    results = retriever.search("authentication", 100)
    assert {hit["chunk_id"] for hit in results} == {chunk["chunk_id"] for chunk in read_corpus()[0]}


def test_rejects_a_stale_or_corrupted_index(tmp_path):
    root = tmp_path / "index"
    shutil.copytree(INDEX_DIR, root)
    mapping = root / "index.json"
    original = mapping.read_text(encoding="utf-8")
    metadata = json.loads(original)
    metadata["chunk_ids"].reverse()
    mapping.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata does not match"):
        Retriever(root)
    mapping.write_text(original, encoding="utf-8")
    (root / "index.faiss").write_bytes(b"invalid data")
    with pytest.raises(ValueError, match="metadata does not match"):
        Retriever(root)
