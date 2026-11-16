# Day 14 — Verified ML Inference

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 14 connects the selected Day 13 model to the backend detection layer. It adds inference only; persistence, frontend work, and LLM/RAG remain outside this increment.

## Trust boundary

The API accepts only observable model features and a run identifier. Ground-truth labels, scenarios, timestamps, and identity fields used by the dataset are not accepted as model inputs.

Before deserialization, the loader verifies:

- the model and metadata both exist;
- the SHA-256 checksum matches;
- the feature contract exactly matches the training contract;
- the selected model name and inference operations are supported.

The serialized model is a trusted local CI artifact. A `joblib` file from an untrusted source must never be loaded.

## Detection output

`POST /detections/ml` returns a binary prediction, malicious probability, the fixed `0.5` decision threshold, model name, and model SHA-256 provenance. It does not return or copy ground truth.

If the model paths are not configured or verification fails, the endpoint returns `503` instead of silently falling back to an unverified detector.
