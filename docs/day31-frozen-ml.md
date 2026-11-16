# Day 31 frozen ML pipeline

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

`data/releases/capstone-ml-v1` contains the exact fitted Logistic Regression
pipeline from the passing Day 30 run and its version, dependency, and provenance
metadata. The pipeline includes the fitted preprocessing. Load it with
`app.ml.frozen_v1.load_pipeline` and pass observable feature records to
`predict_observations`. It returns an observation label and malicious probability.
For run-level decisions, Day 30 used any malicious observation as the run alert.
Load joblib bundles only from a trusted repository checkout or release.

Original Logistic Regression won the Day 30 tie on simplicity. It correctly
classified five of six development validation runs, with one benign web
false alert. Stronger regularization added a benign network false alert and was
rejected. The evidence covers controlled authentication, web and network lab
scenarios only. The scores do not establish production performance or probability
calibration. This written review has no independent teammate sign-off.

Install the pinned dependencies from `requirements/day27.txt` alongside the
backend requirements and run `python -m pytest -q backend/tests/test_public_milestones.py`.
The smoke tests reproduce the saved development decisions and reject metadata
inputs and corrupted model bytes. Day 32 records the completed held-out evaluation.
