"""Local explanation over saved detector outputs and allowlisted evidence."""
from enum import StrEnum
from http.client import HTTPConnection, HTTPException
import json
import os

from pydantic import BaseModel


MODEL = "gemma3:1b"
REQUEST_TIMEOUT = 45
MAX_RESPONSE_BYTES = 65536
RULE_FEATURES = {
    "failed_login_count": "failed SSH password events",
    "suspicious_token_count": "SQL-like token matches",
    "unique_destination_port_count": "distinct observed destination ports",
}


class Question(StrEnum):
    summary = "what_happened"
    reason = "why_suspicious"
    evidence = "what_evidence"


QUESTIONS = {
    Question.summary: "What happened? Lead with the stored prediction.",
    Question.reason: "Why was this suspicious, or why did it not trigger? Lead with the rule comparison if present.",
    Question.evidence: "What evidence is available? Lead with the linked event count.",
}


class Explanation(BaseModel):
    detection_id: str
    question: Question
    model: str
    text: str
    evidence_ids: list[str]


class ExplanationUnavailable(RuntimeError):
    pass


class InvalidExplanation(RuntimeError):
    pass


def evidence_sentences(detector: str, label: str, evidence: dict) -> dict[str, str]:
    """Render fixed project terminology and bounded typed values, omitting raw text."""
    detector_name = {"rule": "rule engine", "ml": "ML model"}[detector]
    facts = {"prediction": f"The stored {detector_name} predicted {label}."}
    event_ids = evidence.get("event_ids")
    if isinstance(event_ids, list):
        count = len(event_ids)
        noun = "record" if count == 1 else "records"
        facts["events"] = f"The stored observation links to {count} normalized event {noun}."
    rule = evidence.get("rule")
    if detector == "rule" and isinstance(rule, dict):
        key, observed, threshold = (rule.get(field) for field in ("feature", "observed", "threshold"))
        if (isinstance(key, str) and key in RULE_FEATURES and type(observed) is int
                and type(threshold) is int and 0 <= observed <= 10**9
                and 0 < threshold <= 10**9 and rule.get("operator") == ">="):
            relation = "met" if observed >= threshold else "fell below"
            facts["threshold"] = (
                f"The observed count for {RULE_FEATURES[key]} was {observed}. "
                f"The count {relation} its threshold of {threshold}."
            )
    if detector == "ml":
        probability = evidence.get("malicious_probability")
        if type(probability) in (int, float) and 0 <= probability <= 1:
            facts["probability"] = f"The stored model score for the malicious class was {probability:.1%}."
    return facts


def ollama_chat(payload: dict) -> dict:
    connection = HTTPConnection("127.0.0.1", 11434, timeout=REQUEST_TIMEOUT)
    try:
        connection.request("POST", "/api/chat", json.dumps(payload), {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ExplanationUnavailable("local Ollama model unavailable")
        body = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, HTTPException) as exc:
        raise ExplanationUnavailable("local Ollama model unavailable") from exc
    finally:
        connection.close()
    if len(body) > MAX_RESPONSE_BYTES:
        raise InvalidExplanation("invalid local explanation response")
    try:
        result = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise InvalidExplanation("invalid local explanation response") from exc
    if not isinstance(result, dict):
        raise InvalidExplanation("invalid local explanation response")
    return result


def select_evidence(question: Question, facts: dict[str, str], context: dict[str, str] | None = None) -> list[str]:
    if os.getenv("CAPSTONE_OLLAMA_ENABLED") != "1":
        raise ExplanationUnavailable("local explanations are disabled")
    candidates = {**facts, **(context or {})}
    prompt = {"question": QUESTIONS[question], "facts": facts}
    instruction = "Select and order evidence IDs for a brief security training explanation. "
    if context:
        prompt["trusted_context"] = context
        instruction += "Select evidence about the run and at least one trusted background passage. "
    payload = {
        "model": MODEL,
        "stream": False,
        "keep_alive": "2m",
        "options": {"num_ctx": 2048, "num_predict": 96, "temperature": 0, "seed": 44},
        "format": {
            "type": "object",
            "properties": {"evidence_ids": {
                "type": "array", "minItems": 1, "maxItems": len(candidates),
                "items": {"type": "string", "enum": list(candidates)},
            }},
            "required": ["evidence_ids"],
            "additionalProperties": False,
        },
        "messages": [{
            "role": "system",
            "content": instruction + "Use only provided IDs, once each. Return JSON only.",
        }, {
            "role": "user",
            "content": json.dumps(prompt),
        }],
    }
    try:
        selection = json.loads(ollama_chat(payload)["message"]["content"])
        ids = selection["evidence_ids"]
        if (set(selection) != {"evidence_ids"} or not isinstance(ids, list)
                or not 1 <= len(ids) <= len(candidates)
                or any(not isinstance(key, str) or key not in candidates for key in ids)
                or len(set(ids)) != len(ids)):
            raise ValueError("invalid evidence selection")
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidExplanation("invalid local explanation response") from exc
    anchor = {
        Question.summary: "prediction",
        Question.reason: "threshold",
        Question.evidence: "events",
    }[question]
    if anchor in facts:
        return [anchor, *(key for key in ids if key != anchor)]
    return ids


def explain(detection_id: str, question: Question, facts: dict[str, str]) -> Explanation:
    ids = select_evidence(question, facts)
    return Explanation(detection_id=detection_id, question=question, model=MODEL,
                       text=" ".join(facts[key] for key in ids), evidence_ids=ids)
