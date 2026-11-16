# Day 16 — Detection Persistence

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 16 adds PostgreSQL-backed persistence for the detection pipeline.

## Stored records

Four linked tables keep responsibilities separate:

1. `feature_runs` stores the run identifier, source type, and observable feature snapshot.
2. `rule_detections` stores the rule decision and evidence.
3. `ml_detections` stores the ML decision, confidence, threshold, and model provenance.
4. `detector_comparisons` links the two decisions and stores agreement or disagreement.

Ground-truth labels and scenarios are deliberately absent from the feature snapshot and prediction tables. This prevents a detector output from overwriting or masquerading as trusted experimental context.

## API

- `POST /detections/compare/store` creates both detections and transactionally stores all four linked records.
- `GET /detections/comparisons/{run_id}` reconstructs the complete comparison.

Saving the exact same deterministic comparison twice is idempotent. Reusing a run ID for a different result is rejected with `409`.

## Scope boundary

Day 16 creates the initial schema directly for this controlled capstone environment. Production migration tooling, normalized event persistence, authentication, frontend work, and LLM/RAG remain later work.
