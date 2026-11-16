# Official Day 26 — Rule Engine v1 Evaluation and Freeze

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Frozen results: data/processed/day26. Rebuild with
`python scripts/freeze_day26_rules.py OUTPUT_DIRECTORY` from repo root. The output
must not exist. CI compares the rebuilt directory byte-for-byte. Source, input and
output hashes are pinned in freeze-manifest.json. After verified merge, CI creates
the annotated rule-engine-v1 milestone tag. Future changes require an explicit new
version or a documented implementation-bug correction, not silent retuning.

## Scope and metrics

Training: 18 development runs; validation: six. All three scenarios and both labels
are represented. Results include accuracy, precision, recall, F1, confusion matrix,
FPR, sample counts and scenario breakdown at run and observation level. Matrices
use [benign, malicious] on both axes. Any triggered observation makes the run alert.
Predictions stay separate from ground truth; the error-review file joins them only
for evaluation. The historical exploratory test and reserved final archive are not
consumed. Final performance evaluation remains Day 32.

Thresholds are unchanged: auth three failed logins per 60-second group; SQLi one
suspicious token per web run; network two observed ports per 60-second group.
Training results match the small known sample. Validation has five correct runs
and one SQLi false positive: matrix [[2,1],[0,3]], accuracy 5/6, precision 3/4,
recall 1, F1 6/7 and FPR 1/3. These are tiny development results, not general
accuracy estimates. Exact values and per-scenario results are in metrics.json.

## Error interpretation and traceability

The benign web look-alike contains the word select. The existing token regex fires,
but the trusted collection metadata records benign user intent. The detector is
wrong on that run; the label must not be changed to agree with it. error-review.json
preserves the decision evidence, metadata filename, original request values, raw
file/line locations and line hashes. All contributing events are rejoined to the
immutable development raw corpus. No threshold was changed to erase the error.

Authentication can flag legitimate repeated mistakes and miss slow/distributed
attempts. Network multi-port maintenance can trigger, while single-service scans,
window-boundary bursts and unseen packet activity may evade. The logs observe
accepted service connections rather than all probes. SQL tokens can occur in
benign text or be absent from alternative attack syntax. These are baseline
limitations, not defects hidden by the freeze.

Review consists of automated raw tracing plus agent interpretation. the project author can
inspect the referenced development evidence; no independent teammate sign-off is
invented. Existing unit challenges document additional potential false positives
and negatives; no false negative occurred in this particular development run set.

The frozen artifact supplies later UI/report numbers. Dataset v1 and its sealed
final evidence remain unchanged. Day 27 ML development has not started.
