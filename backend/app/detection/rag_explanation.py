"""Ground a read-only explanation in stored facts and frozen corpus passages."""
from functools import lru_cache
import os
from typing import Literal

from pydantic import BaseModel

from app.detection.explanation import MODEL, ExplanationUnavailable, Question, select_evidence


SCENARIOS = {
    "auth": ("brute_force", "SSH failed password attempts and brute force"),
    "web": ("sql_injection", "SQL injection and SQL-like token matches"),
    "network": ("reconnaissance", "network service discovery and destination ports"),
}
QUERY_FOCUS = {
    Question.summary: "What happened in this type of observation?",
    Question.reason: "How should a learner interpret the lab rule and its threshold?",
    Question.evidence: "What is recorded in the lab and what does the evidence establish?",
}
ALIASES = {
    "what happened": Question.summary,
    "why suspicious": Question.reason,
    "why was this suspicious": Question.reason,
    "what evidence": Question.evidence,
    "what evidence is available": Question.evidence,
}


class Reference(BaseModel):
    title: str
    location: str


class GroundingSource(BaseModel):
    chunk_id: str
    source_title: str
    source_path: str
    source_sha256: str
    section: str
    text: str
    references: list[Reference]


class RagExplanation(BaseModel):
    detection_id: str
    status: Literal["grounded", "unsupported"]
    text: str
    question: Question | None = None
    model: str | None = None
    evidence_ids: list[str]
    sources: list[GroundingSource]


@lru_cache(maxsize=1)
def load_retriever():
    from app.detection.retrieval import Retriever

    return Retriever()


def parse_question(value: str) -> Question | None:
    key = " ".join(value.casefold().split()).rstrip("?")
    try:
        return Question(key)
    except ValueError:
        return ALIASES.get(key)


def explain_with_context(detection_id: str, source_type: str, value: str, facts: dict[str, str]) -> RagExplanation:
    question = parse_question(value)
    if question is None or (question == Question.reason and "threshold" not in facts):
        return RagExplanation(
            detection_id=detection_id, status="unsupported", evidence_ids=[], sources=[],
            question=question,
            text="The stored evidence and approved notes do not support that question. "
                 "Ask what happened, why the rule flagged the observation, or what evidence is available.",
        )
    if os.getenv("CAPSTONE_OLLAMA_ENABLED") != "1":
        raise ExplanationUnavailable("local explanations are disabled")
    scenario, topic = SCENARIOS[source_type]
    try:
        ranked = load_retriever().search(f"{topic}. {QUERY_FOCUS[question]}", top_k=6)
        sources = {
            hit["chunk_id"]: GroundingSource.model_validate(hit)
            for hit in ranked if hit["scenario"] == scenario
        }
    except (ImportError, OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        raise ExplanationUnavailable("local retrieval is unavailable") from exc
    if not sources:
        raise ExplanationUnavailable("trusted context is unavailable for this scenario")
    passages = {key: source.text for key, source in sources.items()}
    ids = select_evidence(question, facts, passages)
    evidence = [key for key in ids if key in facts] or ["prediction"]
    citations = [sources[key] for key in ids if key in sources]
    return RagExplanation(
        detection_id=detection_id, status="grounded", question=question, model=MODEL,
        text=" ".join(facts[key] for key in evidence), evidence_ids=evidence,
        sources=citations or [next(iter(sources.values()))],
    )
