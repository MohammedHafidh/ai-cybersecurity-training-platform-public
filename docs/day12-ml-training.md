# Day 12 — Classical ML Candidate Training

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 12 trains the first machine-learning candidates using a fresh balanced collection from the controlled Docker lab.

## Data gate

Training runs only after the Day 10 readiness audit passes. The workflow uses 30 independent runs with balanced labels and balanced source coverage, then applies a fixed stratified run-level split:

- 21 training runs
- 9 validation runs
- random state `42`
- no run ID appears in both sets

## Candidate models

Three small classical classifiers are trained:

1. Logistic regression with scaled numeric features.
2. A depth-limited decision tree.
3. A depth-limited random forest with 100 trees.

All candidates use the same numeric feature columns and one-hot encoded source type. Identity fields, timestamps, scenario, and ground-truth label are excluded from the model inputs.

## Outputs

- one serialized `joblib` artifact per candidate
- a deterministic training report containing split provenance and comparison metrics
- separate validation predictions containing run ID, predicted label, and malicious probability
- accuracy, precision, recall, F1, false-positive rate, and confusion matrix for each candidate

Ground truth remains only in the feature table. Prediction records do not embed labels or scenarios.

## Deliberate boundary

Day 12 trains and compares candidates but does not declare a winner. Final selection requires a dedicated evaluation step that reviews per-scenario behavior, false positives, the small-dataset limitation, and stability—not headline accuracy alone.

