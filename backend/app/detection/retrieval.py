"""Read-only semantic retrieval over the frozen Day 45 explanation corpus."""
import hashlib
import json
from pathlib import Path

import faiss
import numpy as np


ROOT = Path(__file__).resolve().parents[3] / "data/knowledge"
CORPUS_PATH = ROOT / "day45/chunks.json"
INDEX_DIR = ROOT / "day46"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DIMENSION = 384


def read_corpus():
    contents = CORPUS_PATH.read_text(encoding="utf-8")
    corpus = json.loads(contents)
    if corpus["version"] != "v1":
        raise ValueError("expected explanation corpus v1")
    return corpus["chunks"], hashlib.sha256(contents.encode("utf-8")).hexdigest()


def load_encoder(*, local_files_only=True):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        MODEL, revision=REVISION, device="cpu", local_files_only=local_files_only,
        trust_remote_code=False, model_kwargs={"use_safetensors": True},
    )


def encode(encoder, texts):
    return np.ascontiguousarray(
        encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32,
    )


def index_metadata(chunks, corpus_digest, index_bytes):
    return {
        "corpus_sha256": corpus_digest,
        "model": MODEL,
        "revision": REVISION,
        "dimension": DIMENSION,
        "metric": "cosine",
        "chunk_ids": [chunk["chunk_id"] for chunk in chunks],
        "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
    }


def build_index(output=INDEX_DIR):
    chunks, corpus_digest = read_corpus()
    encoder = load_encoder(local_files_only=False)
    texts = [
        f"{chunk['source_title']}. {chunk['section']}. {chunk['text']}"
        for chunk in chunks
    ]
    index = faiss.IndexFlatIP(DIMENSION)
    index.add(encode(encoder, texts))
    index_bytes = faiss.serialize_index(index).tobytes()
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.faiss").write_bytes(index_bytes)
    metadata = index_metadata(chunks, corpus_digest, index_bytes)
    (output / "index.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )


class Retriever:
    def __init__(self, directory=INDEX_DIR):
        self._chunks, corpus_digest = read_corpus()
        index_bytes = (directory / "index.faiss").read_bytes()
        metadata = json.loads((directory / "index.json").read_text(encoding="utf-8"))
        if metadata != index_metadata(self._chunks, corpus_digest, index_bytes):
            raise ValueError("retrieval index metadata does not match the frozen corpus or index")
        self._index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype=np.uint8))
        if (self._index.metric_type != faiss.METRIC_INNER_PRODUCT
                or self._index.d != DIMENSION or self._index.ntotal != len(self._chunks)):
            raise ValueError("retrieval index has an invalid metric, dimension, or row count")
        self._encoder = load_encoder()

    def search(self, query: str, top_k: int = 2) -> list[dict]:
        query = query.strip()
        if not query:
            raise ValueError("retrieval query must be nonempty")
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        scores, indices = self._index.search(encode(self._encoder, [query]), min(top_k, len(self._chunks)))
        return [
            {**self._chunks[index], "score": float(score)}
            for score, index in zip(scores[0], indices[0], strict=True)
        ]
