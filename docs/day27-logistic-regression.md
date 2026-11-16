# Official Day 27: Logistic Regression on Dataset v1

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Run from the repository root:

```
python -m pip install -r backend/requirements.txt -r requirements/day27.txt
python -m pytest -q
python scripts/train_day27.py evidence/day27
python scripts/verify_day27.py evidence/day27
```

The output directory must be new. CI uses Python 3.12 and pinned ML library
versions. The environment file records the actual runtime. Model bytes and their
hashes are specific to that runtime; CI compares metrics, predictions, configuration
and transformed features semantically (floating-point tolerance 1e-8), then uploads
the fitted pipeline and its checksums. Load only trusted local/CI joblib artifacts.
Committed JSON in data/processed/day27 records the reviewed baseline.

## Data and preprocessing

The harness verifies the frozen Dataset v1 archive SHA before reading exactly five
members: three Day 20 feature tables plus the Day 21 train/validation membership.
It never extracts the nested reserved evidence or reads either test split. The
existing 18 training runs and six validation runs are preserved. Validation has
seven observations because one benign authentication run spans two windows.
Run, row and event overlap checks fail closed. Trusted labels are used for fitting
or evaluation only; predictions are saved separately without truth labels.

The exact 17 numeric fields and source type are recorded in config.json. Counts,
rates, request lengths, response counts and observed port diversity are plausible
observable inputs for the three scenarios. Source type identifies the log family,
not attack intent. Source-inapplicable numeric fields are explicitly zero. Missing
applicable fields, negative or nonfinite values fail. StandardScaler is fitted
on training observations only; source type has a fixed one-hot vocabulary.
No identity, metadata, scenario, filenames, timestamps or label fields enter the
frame. feature_review.json records the exact transformed feature names, one input
sample, transformed values and training scaler means. Metadata mutation tests
verify that labels and IDs cannot alter predictions.

Logistic Regression uses seed 42, C=1, lbfgs, max_iter=1000 and its default decision
threshold. Each training run contributes total weight one, even if it has multiple
windows. No validation tuning or model selection occurs. Any malicious observation
makes a run malicious, matching the frozen rule baseline aggregation.

## Results and security review

Validation: six runs, confusion matrix [[2,1],[0,3]] in benign/malicious order;
accuracy 5/6, precision 3/4, recall 1, F1 6/7, false-positive rate 1/3.
The SQLi benign look-alike remains a false positive. Full training, observation,
run and scenario metrics are saved. These tiny scripted development results do
not establish deployment accuracy or improvement over the frozen rule engine.

Security review is the agent's explicit feature allowlist/leakage audit, supported
by tests; no independent teammate sign-off is claimed. Token-derived inputs inherit
heuristic weaknesses, network inputs observe accepted connections, and scripted
counts/source correlations may fail on realistic traffic. Later planned candidate
comparison and security review remain necessary. Existing historical prototype
training/API code stays separate; this is the official frozen-dataset baseline.
Random Forest is Day 28, Gradient Boosting Day 29, comparison Day 30 and final
evaluation Day 32. None of those tasks is performed here.
