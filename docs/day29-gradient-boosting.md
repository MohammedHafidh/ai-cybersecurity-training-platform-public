# Official Day 29: Gradient Boosting, third and final candidate

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

GradientBoostingClassifier uses the unchanged official Dataset v1 loader and Day 27
preprocessing pipeline. The exact 18 training runs and six validation runs are
preserved, with seven validation observations because one benign authentication
run spans two windows. Training weights, observable features, source encoding,
training-only scaling and any-malicious-observation run aggregation match Days
27 and 28. Historical exploratory and reserved final-test data are not consumed.

## Reproduce

Run from the repository root with Python 3.12 and the existing pinned ML overlay:

```
python -m pip install -r backend/requirements.txt -r requirements/day27.txt
python -m pytest -q
python scripts/train_day29.py evidence/day29
python scripts/verify_day29.py evidence/day29
```

Use a new output directory. Committed JSON in data/processed/day29 contains the
reviewed results. The generated output includes the persisted pipeline.joblib,
runtime versions and checksums; CI uploads the complete day29-gradient-boosting
artifact. Load only trusted model artifacts. Verification uses the existing 1e-8
numeric tolerance, checks runtime-specific artifact hashes, and enforces Day 27
split and transformed-feature parity. Earlier candidates and their reports remain
unchanged. Source and immutable dataset hashes are recorded in config.json.

## Fixed training configuration and behavior

Configuration was fixed before validation: 100 boosting stages, learning rate 0.1,
maximum tree depth two, minimum leaf size one, full sampling, log loss and seed 42.
There is no internal validation split, early stopping, search or validation-driven
tuning. Each training run contributes total sample weight one. Metadata/labels
are excluded from model inputs by the existing explicit observable allowlist.

training_behavior.json records all 100 weighted training-loss values and the fitted
stage count. Training loss decreases on this small scripted corpus; that describes
fit, not generalization. All three candidates are evaluated on the same validation
membership with the same metric definitions, including per-source and observation
breakdowns. Repeat-fit, persisted reload, metadata mutation, restricted archive
access and training-only fit checks are included in the tests.

## Development results and security interpretation

Training: 18/18 runs correct. Validation: 5/6 correct, accuracy 0.8333, precision
0.75, recall 1.0, F1 0.8571 and FPR 0.3333. The confusion matrix in
benign/malicious order is [[2,1],[0,3]]. The validation predictions match the two
existing candidates on these six runs; this sample demonstrates no new useful
classification behavior from the extra sequential-tree complexity. Final model
comparison, the bounded improvement round and selection remain Day 30.

The sole observed error is the same benign SQL-like web look-alike. Its suspicious
token and error response overlap injection indicators while trusted run intent is
benign. error_review.json records the run/row/event IDs, observable values, raw
source filename and archive hash. These events have original raw-line traces in
the Day 26 error review. Keep the benign label and the false positive. No false
negative occurred in this sample; unfamiliar injection syntax, slow authentication
abuse and scans invisible to service logs can still evade. Legitimate retries and
multi-service activity can still trigger. Security interpretation is attributed to
agent review and tests; no independent teammate sign-off is claimed.

Training-only impurity feature importance is saved as a descriptive artifact.
Correlated counters, zero-filled source-specific fields and scripted timing can
reflect lab structure. Importance is not causal evidence or a deployment ranking.

## Why the candidate set ends here

Logistic Regression supplies a simple linear baseline, Random Forest supplies
bagged nonlinear trees, and Gradient Boosting supplies sequential error-correcting
trees. These three cover the planned practical comparisons for the project's
small tabular authentication, web and network features. More model families would
increase validation choices and complexity without new independent evidence.
Neural models, extra ensembles and model searches are outside this agreed scope.
Day 30 will assess practical trade-offs and one justified bounded improvement.
The independent final evidence remains sealed until Day 32; Day 30 has not started.
