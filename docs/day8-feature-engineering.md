# Day 8 — Deterministic Run Features

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 8 converts the Day 7 normalized events into a small, auditable feature table for later rule-based and machine-learning detection.

## Scope

- Read and validate normalized JSON Lines records.
- Aggregate exactly one feature row per controlled run.
- Produce deterministic feature IDs and stable output ordering.
- Preserve the trusted scenario and label without deriving either from features.
- Export both JSON Lines for the application and CSV for later analysis.

Detector thresholds, rule decisions, model training, and evaluation are outside Day 8.

## Feature groups

Authentication features:

- authentication attempts
- failed and successful login counts
- unique username count

Web features:

- web request count
- maximum request-data length
- count of observable SQL-oriented tokens

Network features:

- connection count
- unique destination-port count

All feature rows also retain the run ID, event window, source type, trusted scenario, and trusted label. A run containing inconsistent source or ground-truth context is rejected instead of silently combined.

## Reproduce

```bash
PYTHONPATH=backend python scripts/build_day8_features.py \
  data/processed/day7-normalized-events.jsonl \
  data/features/day8
```

The command produces `run-features.jsonl` and `run-features.csv`. Reprocessing the same normalized events produces the same rows and identifiers.

