# Day 32 held-out evaluation

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

The frozen rule engine and Day 31 Logistic Regression pipeline each scored the
same 12 reserved lab runs. Each source has two benign and two malicious runs.
A run alerts if any of its observations alerts. The evaluator verifies frozen
source hashes, model bytes, and reservation integrity before scoring. It uses
the existing parser, feature builders, and inference functions with fixed
parameters. Detection and metric calculation have no LLM dependency.

| Detector | Accuracy | Precision | Recall | F1 | False positive rate | Confusion matrix |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Rules | 41.7% | 44.4% | 66.7% | 53.3% | 83.3% | [[1,5],[2,4]] |
| ML | 75.0% | 80.0% | 66.7% | 72.7% | 16.7% | [[5,1],[2,4]] |

Matrices use actual labels as rows and predicted labels as columns, in benign,
malicious order. Both detectors caught four malicious runs. Their misses differed.

| Source | Rules correct | ML correct | Main difference |
| --- | ---: | ---: | --- |
| Authentication | 3/4 | 3/4 | Each flagged a different benign retry run |
| Web | 0/4 | 4/4 | The token rule flagged both benign runs and missed both malicious runs |
| Network | 2/4 | 2/4 | Rules flagged all four runs and ML flagged none |

The public report contains scenario and overall metrics. The private academic record
retains the run decisions and original evidence references.

The 12 scripted runs support a comparison within the three lab scenarios.
They cannot establish production performance. No parameters were tuned on these
results. The error review was performed by the agent using the raw evidence
references. Independent teammate sign-off was unavailable.

CI runs the existing development inference smoke tests and validates the saved
report's metrics and error coverage from its recorded decisions. The Day 32
evaluator is intentionally outside routine CI to avoid rescoring the holdout.
