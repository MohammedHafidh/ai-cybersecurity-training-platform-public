# Day 15 — Rule and ML Detector Comparison

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 15 runs the transparent rule baseline and the selected ML model against the same unlabeled feature input. It preserves both decisions and reports whether they agree.

## Comparison outcomes

- `consensus_benign`: both detectors predict benign.
- `consensus_malicious`: both detectors predict malicious.
- `detector_disagreement`: the predictions differ and manual review is recommended.

A disagreement is not silently resolved in favor of either detector. The comparison layer is not an ensemble classifier and does not create a new ground-truth label.

## API

`POST /detections/compare` accepts the same bounded, ground-truth-free request as Day 14. Its response contains the complete rule detection, complete ML detection, agreement state, comparison outcome, and review recommendation.

The ML artifact retains the Day 14 checksum and feature-contract verification. Missing or invalid model configuration returns `503`.

## Scope boundary

Day 15 does not add persistence, user-interface changes, model retraining, or LLM/RAG explanations.
