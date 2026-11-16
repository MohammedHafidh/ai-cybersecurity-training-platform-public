# Day 13 — Model Evaluation and Selection

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

> Day 17 supersedes the original fold construction with controlled scenario
> variants and grouped cross-validation. See `day17-robust-ml-evaluation.md`.

Day 13 evaluates the three Day 12 candidates and selects one model for the next integration stage. It does not expose predictions through the API or advance into deployment.

## Evaluation design

The same 30 independent controlled-lab runs are evaluated with deterministic five-fold cross-validation. Folds are stratified by both source type and trusted ground-truth label, so every fold contains one benign and one malicious run from auth, web, and network evidence.

Each candidate receives:

- overall accuracy, precision, recall, F1, false-positive rate, and confusion matrix;
- the same metrics separately for auth, web, and network runs;
- one out-of-fold prediction per run, kept separate from ground truth.

## Selection policy

Candidates are ranked lexicographically by:

1. highest malicious recall;
2. lowest false-positive rate;
3. highest F1;
4. highest accuracy;
5. simplest model only when all measured metrics tie.

The fifth criterion prevents an arbitrary winner on a small, easily separable lab dataset. Logistic regression is considered simpler than a decision tree, which is simpler than a random forest.

After selection, the winning algorithm is refit on all 30 available runs and saved with metadata that records its feature contract, training count, random state, selection report, and controlled-lab-only intended use.

## Limitations

This is a valid controlled-lab comparison, not a production benchmark. The dataset has only 30 runs and five examples in each source-label group. The selected model therefore becomes the current capstone candidate, not a permanently proven detector, and must be re-evaluated as new data is collected.
