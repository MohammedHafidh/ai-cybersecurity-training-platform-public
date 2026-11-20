# Frozen held-out evaluation

| Detector | Scope | Runs | Accuracy | Precision | Recall | F1 | FPR | TN | FP | FN | TP |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rule | overall | 12 | 41.7% | 44.4% | 66.7% | 53.3% | 83.3% | 1 | 5 | 2 | 4 |
| rule | auth | 4 | 75.0% | 66.7% | 100.0% | 80.0% | 50.0% | 1 | 1 | 0 | 2 |
| rule | web | 4 | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 0 | 2 | 2 | 0 |
| rule | network | 4 | 50.0% | 50.0% | 100.0% | 66.7% | 100.0% | 0 | 2 | 0 | 2 |
| ml | overall | 12 | 75.0% | 80.0% | 66.7% | 72.7% | 16.7% | 5 | 1 | 2 | 4 |
| ml | auth | 4 | 75.0% | 66.7% | 100.0% | 80.0% | 50.0% | 1 | 1 | 0 | 2 |
| ml | web | 4 | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% | 2 | 0 | 0 | 2 |
| ml | network | 4 | 50.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2 | 0 | 2 | 0 |

Rows in confusion matrices are actual labels; columns are predictions.
Both axes use benign, malicious order. The positive class is malicious.
Results aggregate by run using any malicious observation.
Zero-denominator rates use the frozen report's zero convention.
