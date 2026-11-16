# Day 30 development model comparison

| Candidate | Accuracy | Precision | Recall | F1 | FPR | Confusion matrix |
|---|---:|---:|---:|---:|---:|---|
| logistic_regression | 0.8333 | 0.7500 | 1.0000 | 0.8571 | 0.3333 | [[2, 1], [0, 3]] |
| random_forest | 0.8333 | 0.7500 | 1.0000 | 0.8571 | 0.3333 | [[2, 1], [0, 3]] |
| gradient_boosting | 0.8333 | 0.7500 | 1.0000 | 0.8571 | 0.3333 | [[2, 1], [0, 3]] |
| logistic_regression_C_0.1 | 0.6667 | 0.6000 | 1.0000 | 0.7500 | 0.6667 | [[1, 2], [0, 3]] |

Selected: logistic_regression. Matrices use benign/malicious order; six validation runs only.

One predeclared C=0.1 experiment only. Final-test evidence remains sealed until Day 32.
