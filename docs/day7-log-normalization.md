# Day 7 — Trusted Log Normalization

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 7 begins the data-processing stage after the controlled brute-force, SQL-injection, and reconnaissance evidence runs.

## Scope

- Parse the real log shapes established during Days 4–6.
- Normalize authentication, web, and network records into `NormalizedEvent`.
- Correlate structured records to the correct run and discard records outside the run window.
- Join `scenario` and `attack_label` exclusively from validated run metadata.
- Produce deterministic JSON Lines output without modifying raw evidence.

Feature engineering, detection rules, model training, and evaluation are intentionally outside Day 7.

## Trust boundary

Raw log content is evidence, not ground truth. The parsers may extract observable fields, but they never infer whether an event is benign or malicious. A run is accepted only when its metadata is internally valid and has `status: valid`.

Structured web and network logs must carry the metadata run ID. Authentication logs without an embedded run ID are correlated by the captured source file and the trusted run time window.

## Reproduce

From the repository root after installing the backend requirements:

```bash
PYTHONPATH=backend python scripts/normalize_day7.py \
  backend/tests/fixtures/day7/manifest.json \
  data/processed/day7-normalized-events.jsonl
```

The committed fixtures are small, representative extracts of the three lab formats. CI validates the resulting record count, source coverage, label coverage, unique deterministic IDs, and source provenance.

