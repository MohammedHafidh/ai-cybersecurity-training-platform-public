# Day 22 — Development EDA and Quality Review

Training and validation descriptive analysis only

Reserved final-test observations were not opened. No detector metrics were computed.

## Counts

| Source | Runs | Rows | Benign / malicious runs |
|---|---:|---:|---|
| auth | 8 | 9 | 4 / 4 |
| network | 8 | 8 | 4 / 4 |
| web | 8 | 8 | 4 / 4 |

## Selected feature distributions

| Source / feature | Min | Median | Max | Mean |
|---|---:|---:|---:|---:|
| auth / attempt_count | 3 | 4 | 5 | 3.66666667 |
| auth / failed_login_count | 0 | 1 | 4 | 2.11111111 |
| auth / successful_login_count | 0 | 2 | 4 | 1.55555556 |
| auth / unique_username_count | 1 | 1 | 4 | 1.66666667 |
| auth / attempts_per_second | 0.05 | 0.06666666666666667 | 0.08333333333333333 | 0.06111111 |
| auth / success_after_failure | 0 | 0 | 1 | 0.44444444 |
| network / connection_count | 1 | 3.5 | 6 | 3.25 |
| network / unique_destination_port_count | 1 | 1.5 | 2 | 1.5 |
| network / connections_per_second | 0.016666666666666666 | 0.058333333333333334 | 0.1 | 0.05416667 |
| network / observed_span_seconds | 0.0 | 0.178572 | 0.575993 | 0.23410662 |
| web / request_count | 1 | 1.5 | 3 | 1.75 |
| web / missing_input_count | 0 | 0.0 | 1 | 0.125 |
| web / empty_input_count | 0 | 0.0 | 1 | 0.125 |
| web / max_request_length | 2 | 7.0 | 34 | 9.125 |
| web / suspicious_token_count | 0 | 1.0 | 2 | 0.75 |
| web / residual_encoded_count | 0 | 0.0 | 1 | 0.125 |
| web / error_response_count | 0 | 0.5 | 1 | 0.5 |

## Quality and traceability

All accepted events reconcile to raw file/line hashes. Twelve representative train/validation rows cover both labels in each source. See traceability-checks.json.

Full corpus exclusion counts are preserved in eda-quality-report.json. Missing feature cells and raw web missing-input counts are reported separately.

## Limitations and review

- Small scripted controlled-lab corpus; distributions do not establish detector performance.
- Window rows are not independent runs; authentication has one extra boundary window.
- Zero null feature cells coexist with explicitly counted missing/empty raw web inputs.
- SQL token matches can occur in benign look-alikes; labels remain trusted metadata.
- Network logs observe accepted service connections, not all packets or closed-port attempts.
- No data changes, model tuning, threshold selection or reserved final-test analysis performed.

Review conclusion: no new data bug or collection gap was identified by these checks. Preserve current labels/features and splits. Automated review is not independent teammate sign-off.
