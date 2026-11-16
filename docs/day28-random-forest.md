# Official Day 28: Random Forest candidate

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Random Forest is added to the official Dataset v1 harness. The existing Day 27
loader, explicit observable-feature frame and preprocessing pipeline are reused
unchanged. Only the classifier is replaced. No API integration, hyperparameter
search, final candidate selection or Day 29 work is included.

## Reproduce

From the repository root, using Python 3.12 and the existing pinned ML overlay:

```
python -m pip install -r backend/requirements.txt -r requirements/day27.txt
python -m pytest -q
python scripts/train_day28.py evidence/day28
python scripts/verify_day28.py evidence/day28
```

The output directory must be new. It includes the fitted pipeline.joblib, reports,
runtime versions and checksums. CI uploads the complete day28-random-forest
artifact. Load only trusted model artifacts. Committed JSON in data/processed/day28
contains reviewed reports; runtime-specific model bytes and checksums stay in the
generated artifact. Verification uses the Day 27 floating-point tolerance 1e-8.

## Comparability and leakage controls

The immutable Dataset v1 archive hash and exact train/validation membership are
unchanged: 18 training runs/18 observations, six validation runs/seven observations.
The extra validation observation is the second window of the same benign auth run.
Run grouping, labels, 17 numeric features, three one-hot source indicators,
training-only scaling, zero fill for inapplicable fields and inverse window count
weights per run all match Day 27. A run alerts if any observation is malicious.
No run metadata, labels, source filenames, IDs or timestamps enter model inputs.

Configuration is fixed before validation: 100 trees, maximum depth four,
minimum leaf size one, sqrt feature subsampling, bootstrap enabled, seed 42,
one worker and the classifier's default decision. There is no tuning. CI checks
split membership and exact transformed-sample/scaler parity with Day 27, repeats
training and reloads the persisted model, mutates metadata to check prediction
invariance, and guards archive member access. The reserved nested final evidence
and historical exploratory test membership are never opened by training.

## Results and error interpretation

Training: 18/18 runs correct. Validation: 5/6 runs correct, accuracy 0.8333,
precision 0.75, recall 1.0, F1 0.8571 and FPR 0.3333. The confusion matrix is
[[2,1],[0,3]] in benign/malicious order. Per-source and observation metrics are
saved using the same definitions as Day 27. The result matches Logistic Regression
on this small sample; it does not establish that Random Forest is superior.

The one false positive is the benign web look-alike run ending web-benign-01.
Its two requests include benign SQL-like text, one suspicious token and one error
response. Those observations overlap malicious injection indicators, while trusted
collection intent remains benign. error_review.json records the full run ID,
row ID, event IDs, raw filename, observable values and archive hash for tracing.
The same events are traced to original lines and benign select text in the frozen
Day 26 error-review.json. No label or threshold was changed to hide the error.
No false negatives occurred in this particular development sample; this does not
prove they cannot occur. Slow authentication abuse, unfamiliar injection syntax
and unobserved scan traffic remain plausible misses. Legitimate retry bursts and
multi-service maintenance remain plausible false positives.

## Feature importance and review limits

feature_importance.json maps training-only mean decrease in impurity to every
transformed feature. Leading inputs include observed port diversity, observed
connection span and failed login count. These are plausible behavioral indicators,
but span and counts can encode scripted timing. Correlated counts/rates share
importance, and zero-filled features/source indicators can capture lab structure.
Importance is descriptive of this fitted forest, not causal evidence or a reliable
ranking for real traffic. No final-test permutation or feature selection occurred.

Security interpretation is attributed to agent review with automated evidence
checks; no independent teammate sign-off is invented. Day 29 adds Gradient Boosting,
Day 30 handles comparison/one bounded improvement, and Day 32 evaluates the sealed
final evidence. Those planned tasks remain outstanding.
