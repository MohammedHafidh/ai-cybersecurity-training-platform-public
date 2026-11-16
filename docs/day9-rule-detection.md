# Day 9 — Transparent Rule-Based Detection

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 9 adds the first detector: a small, explicit rule baseline for each mandatory attack scenario.

## Rules

| Rule | Observable condition | Prediction |
|---|---|---|
| `AUTH_FAILED_LOGIN_BURST` | failed login count ≥ 2 | brute force |
| `WEB_SQL_TOKEN_PRESENT` | suspicious SQL-token count ≥ 1 | SQL injection |
| `NETWORK_MULTI_PORT_SCAN` | unique destination-port count ≥ 2 | reconnaissance |

These thresholds match the bounded controlled-lab runs. They are intentionally simple and auditable, not claims about universal production thresholds.

## Decision contract

Every run receives one decision containing:

- deterministic detection ID
- source run ID
- detector type
- predicted label and scenario
- triggered rule, when any
- observed feature, comparison operator, and threshold

When a threshold is not reached, the output is a benign prediction that still records what was inspected.

## Trust boundary

The rule engine does not read `attack_label` or `scenario` when deciding. Ground truth stays in the feature dataset for later evaluation, while rule predictions stay in a separate detection artifact. Tests deliberately relabel an unchanged feature row and confirm that its prediction does not change.

ML training, metric calculation, threshold tuning, and application/database integration are outside Day 9.

## Reproduce

```bash
PYTHONPATH=backend python scripts/run_day9_rules.py \
  data/features/day8/run-features.jsonl \
  data/reports/day9-rule-detections.jsonl
```

