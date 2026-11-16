# Rule engine v1 — frozen development evaluation

Training and validation only. Final-test evidence remains sealed until Day 32.

| Split / source | Runs | Accuracy | Precision | Recall | F1 | FPR | Confusion matrix [benign, malicious] |
|---|---:|---:|---:|---:|---:|---:|---|
| train/overall | 18 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | [[9, 0], [0, 9]] |
| train/auth | 6 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | [[3, 0], [0, 3]] |
| train/network | 6 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | [[3, 0], [0, 3]] |
| train/web | 6 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | [[3, 0], [0, 3]] |
| validation/overall | 6 | 0.8333 | 0.7500 | 1.0000 | 0.8571 | 0.3333 | [[2, 1], [0, 3]] |
| validation/auth | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | [[1, 0], [0, 1]] |
| validation/network | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | [[1, 0], [0, 1]] |
| validation/web | 2 | 0.5000 | 0.5000 | 1.0000 | 0.6667 | 1.0000 | [[0, 1], [0, 1]] |

## Error review

1 development run error(s), all preserved with metadata and raw line hashes in error-review.json.
The SQLi keyword heuristic flags benign look-alike text. Ground truth comes from the prescribed run, not the rule. No threshold change was made.

## Interpretation

Small scripted samples do not establish general accuracy. Window and run metrics are separate in metrics.json. Run aggregation is any triggered observation.
Legitimate retries and multi-service activity may trigger; slow/distributed activity and unrecognized SQL syntax may evade.
No ML comparison or reserved final-test evaluation was performed. Frozen results are suitable for later UI/report integration with these limitations.
