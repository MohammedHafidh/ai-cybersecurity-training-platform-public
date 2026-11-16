# Historical Day 18 Implementation — Reserved-Variant Evaluation

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Correction: Variant 05 already participated in the historical Day 17 experiment.
Fresh executions of its known templates are not an untouched final benchmark.
This implementation reserves it only within one evaluation invocation. Artifact
names retain historical wording for compatibility; they do not establish independence.
The official Day 18 task is SQLi feature engineering and remains subject to its own
acceptance checks. Final split integrity belongs to official Day 21 and final ML
evaluation to Days 27–32.

## Evaluation protocol

- Variant 05 is reserved before candidate selection within this invocation only.
- Variants 01–04 provide 24 development runs.
- The three existing candidates are compared with four-fold grouped cross-validation.
- The selected algorithm is trained on the 24 development runs.
- It is evaluated exactly once on the six Variant 05 runs: one benign and one
  malicious run for authentication, web, and network evidence.
- Holdout predictions stay separate from trusted ground truth.

The saved Day 18 model is the model that was actually evaluated: it is trained on
the 24-run development set, not silently refitted on the holdout afterward.

## Definition of Done

- A fresh 30-run varied Docker-lab dataset is collected.
- The development and final-test run IDs are disjoint.
- This invocation's model selection excludes Variant 05; earlier experiments did not.
- The final report contains accuracy, precision, recall, F1, false-positive rate,
  confusion matrix, and per-source metrics.
- Six provenance-preserving holdout predictions and model checksum metadata exist.
- Backend tests and the Day 18 GitHub Actions workflow pass.

## Limitation

Six holdout cases remain a small controlled-lab test. The result is more defensible
than evaluating on repeated templates, but it is not a production benchmark.
