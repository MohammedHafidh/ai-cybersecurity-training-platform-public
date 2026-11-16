# Days 1–33 implementation audit

This checklist follows the official 63-day roadmap. Early PR day labels used a
different sequence, so the status below follows deliverables rather than PR titles.
The private academic record owns the live lab, archived evidence, and milestone
tags. The public repository is the continuation branch of the codebase with fresh
Git history.

| Day | Audited status and evidence |
| --- | --- |
| 1 | Repository, architecture, data contract and run metadata are present. Historical teammate access was not independently verified. |
| 2 | API health and frontend build pass in public CI. The historical Docker lab configuration belongs to the private record. |
| 3 | Event and run schemas and ingestion smoke tests are public. Benign authentication evidence is in the private record. |
| 4 | Auth parser and label handling are tested. Captured authentication failure logs and metadata remain private. |
| 5 | The later frozen corpus and auth windows supply the planned varied authentication coverage and feature preview. |
| 6 | The web parser and request fields are covered by fixtures. The live target and benign web evidence are private. |
| 7 | SQL injection normalization is covered by defensive tests. The original captured evidence remains private. |
| 8 | The varied web runs, exclusions and feature preview are supplied by the later corpus and feature carryover. |
| 9 | Network parser and observed fields are present. The benign live baseline remains private. |
| 10 | Network aggregation and metadata are verified by feature tests and the private corpus. Live reproduction remains private. |
| 11 | The later frozen corpus supplies varied network coverage. Features are limited to observable traffic in the service logs. |
| 12 | Unified normalization and validation are covered by fixtures. Lab reset and export belong to the private lab. |
| 13 | Private batch audit reproduces the quality report and duplicate and exclusion results. Public tests cover rejection paths with fixtures. |
| 14 | The frozen corpus has all six source/label strata. Lab diversity remains limited. |
| 15 | The tagged private raw corpus rebuilds with 30 runs and 90 observations, with hashes, provenance and exclusions. |
| 16 | Cleaning derives labels from run metadata. Private rebuild reproduces normalized events and audit counts. |
| 17 | Auth window tests cover retry counts and boundaries. Independent manual review is unverified. |
| 18 | Web feature tests cover encoded, missing and benign look-alike inputs. The older variant experiment is not the final test. |
| 19 | Network window tests cover benign bursts and grouping. Historical live verification remains private. |
| 20 | Public modeling tables have 31 rows, a dictionary and coverage counts. Checksums are verified. |
| 21 | Public development splits reconstruct with 18 training, six validation and six exploratory runs. The separate private final archive has 12 runs and verifies independently. |
| 22 | Private rebuild reproduces the EDA and 12 development trace checks. Public EDA summaries remain available. |
| 23 | Dataset v1 and its tag are private. The packaged development build reproduced using the archived pipeline. |
| 24 | Frozen authentication rule contract, threshold and evidence are covered by public tests. |
| 25 | Three rule detectors and benign look-alike coverage are retained. |
| 26 | The private rule baseline tag, metric reports and error review are verified. The public copy omits raw error content. |
| 27 | Logistic Regression fits and replays metrics on the retained development tables. |
| 28 | Random Forest fits the same training membership and reproduces comparable metrics. |
| 29 | Gradient Boosting fits the same training membership and reproduces comparable metrics. |
| 30 | The original comparison and one fixed regularization experiment reproduce. Logistic Regression remains selected. |
| 31 | The pinned model loads and reproduces saved development decisions. Invalid inputs and tampering are rejected. |
| 32 | The private detection tag and raw error references verify. Public metrics match the private report and recompute from the confusion matrices. The holdout was not rescored. |
| 33 | PostgreSQL schema, readiness and traceability tests are in hosted CI. Core setup is separate from legacy comparison table setup. |

Public CI verifies the application, defensive fixtures, published tables,
development model replay, aggregate final results, and a disposable PostgreSQL
database. It cannot recreate the private Docker lab or its raw evidence. The
historical tags are references in the private academic history and do not carry
over into the fresh public history. Neither lab validation results nor the
small final benchmark describe production performance.

The existing comparison routes remain a legacy inference interface. The
Day 31 frozen API-independent predictor and the new core schema are separate
components. Ingestion into the core database and further API integration
belong to subsequent roadmap tasks.
