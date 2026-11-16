# Day 10 — ML Dataset Readiness Gate

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 10 starts the machine-learning stage with a mandatory evidence gate. It does not train a model on the current four-row feature extract because that would produce misleading results.

## Why training is blocked

The current representative dataset contains:

- 4 controlled runs
- 1 benign row and 3 malicious rows
- all three required attack scenarios
- benign and malicious web coverage
- no benign authentication feature row
- no benign network feature row

Training now would let a model confuse source type with maliciousness and would not support a defensible stratified train/test split.

## Readiness checks

The audit verifies:

- non-empty input
- unique run and feature identifiers
- both trusted labels
- at least five independent runs per label
- all mandatory attack scenarios
- benign and malicious coverage for authentication, web, and network sources
- no identical observable feature vectors carrying conflicting labels

The five-per-label threshold is a minimum engineering gate, not a claim that ten samples are sufficient for a final capstone model. More controlled lab runs remain preferable.

## Current result

The dataset is correctly marked `ready_for_training: false` with two blockers:

1. `minimum_samples_per_label`
2. `source_label_coverage`

This result protects the architecture rule that ML must use a usable lab-generated dataset. It does not fabricate, duplicate, or synthetically relabel evidence to make the gate pass.

## Reproduce

```bash
PYTHONPATH=backend python scripts/audit_day10_ml_readiness.py \
  data/features/day8/run-features.jsonl \
  data/reports/day10-ml-readiness.json
```

Use `--require-ready` in a future training workflow so that model fitting fails closed until genuine controlled-run coverage satisfies every check.

