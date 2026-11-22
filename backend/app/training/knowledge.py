"""Versioned teaching corpus and local FAISS retrieval; frozen v1 corpus remains untouched."""

from functools import lru_cache
import hashlib
import json
import threading
from app.training.content import SCENARIOS, VERSION
from app.training.lab import data_root

LOCK = threading.RLock()


def corpus():
    return [
        dict(
            chunk_id=f"{VERSION}:{key}:{section}",
            scenario=key,
            section=section,
            text=text,
            title=f"{value['title']} / {section.replace('_',' ')}",
            references=value["references"],
        )
        for key, value in SCENARIOS.items()
        for section, text in {
            "concept": value["definition"] + " " + value["importance"],
            "evidence": value["observe"] + " " + value["logs"],
            "features": " ".join(f"{k}: {v}" for k, v in value["features"].items()),
            "rule": value["rule"],
            "model": value["ml"],
            "limitations": value["limitations"],
            "mitigation": value["mitigation"],
        }.items()
    ]


@lru_cache(maxsize=1)
def load_index():
    import faiss
    import numpy as np
    from app.detection.retrieval import load_encoder, encode, REVISION

    with LOCK:
        chunks = corpus()
        digest = hashlib.sha256(json.dumps(chunks, sort_keys=True).encode()).hexdigest()
        directory = data_root() / "knowledge" / VERSION
        directory.mkdir(parents=True, exist_ok=True)
        encoder = load_encoder()
        index_path = directory / "index.faiss"
        meta_path = directory / "manifest.json"
        if index_path.exists() and meta_path.exists():
            payload = index_path.read_bytes()
            meta = json.loads(meta_path.read_text())
            if (
                meta.get("corpus_sha256") != digest
                or meta.get("encoder_revision") != REVISION
                or meta.get("index_sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError(
                    "Training knowledge index integrity mismatch; operator must rebuild the cache"
                )
            index = faiss.deserialize_index(np.frombuffer(payload, dtype=np.uint8))
        else:
            index = faiss.IndexFlatIP(384)
            index.add(encode(encoder, [c["title"] + ". " + c["text"] for c in chunks]))
            payload = faiss.serialize_index(index).tobytes()
            index_path.write_bytes(payload)
            meta_path.write_text(
                json.dumps(
                    dict(
                        corpus_sha256=digest,
                        encoder_revision=REVISION,
                        index_sha256=hashlib.sha256(payload).hexdigest(),
                        chunk_ids=[c["chunk_id"] for c in chunks],
                    ),
                    indent=2,
                )
            )
        if (
            index.ntotal != len(chunks)
            or index.d != 384
            or index.metric_type != faiss.METRIC_INNER_PRODUCT
        ):
            raise ValueError("Invalid teaching index")
        return encoder, index, chunks


def retrieve(scenario, question):
    from app.detection.retrieval import encode

    encoder, index, chunks = load_index()
    with LOCK:
        scores, indices = index.search(
            encode(encoder, [SCENARIOS[scenario]["title"] + ". " + question]), len(chunks)
        )
    # Score all vectors but pass only the top three matching scenario passages to generation.
    return [
        {**chunks[i], "score": float(s)}
        for s, i in zip(scores[0], indices[0], strict=True)
        if chunks[i]["scenario"] == scenario
    ][:3]
