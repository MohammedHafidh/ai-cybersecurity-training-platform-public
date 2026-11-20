# Day 58 issue triage and cleanup

The review starts from the frozen Day 56 evaluation and Day 57 failure behavior. The local backend suite passed 192 tests, with two retrieval tests skipped in the base environment. Hosted retrieval verification installs the embedding dependencies and exercises those paths.

| Priority and kind | Finding | Disposition |
| --- | --- | --- |
| Medium software defect | A successful HTTP explanation response with a null passage or malformed reference could pass the UI's shallow check and crash rendering. | The API client validates consumed passage and reference fields before returning the response. The panel shows its existing retry state. Unit and Chromium tests cover the defect. |
| Medium evidence hygiene | The documented SQLite fallback can create database files in the checkout. | Ignore the demo fallback database and its WAL/SHM files. No such files were tracked during the review. |
| Detector limitation | The held-out results contain false positives and false negatives, and the Day 52 benign phrase triggers both detectors. | Retain the documented findings and trusted labels. See [Day 56](day56-final-evaluation.md). |
| Environment limitation | A browser timeout can leave model work running. CPU inference and cache availability affect local explanations. | Retain the measured Day 57 behavior and its limits. See [failure-path notes](day57-robustness.md). |

## Repository and setup review

The review scanned the 306 files tracked at the start of Day 58 for common private-key and GitHub/AWS token patterns and tracked environment, database and temporary files. No matches were found. Pattern scanning does not prove that all possible secrets are absent. Private captures remain in the external archive. The public evidence records contain hashes and results, while browser output remains ignored under `frontend/test-results/`. The documented synthetic backup is published only by the selected CI artifact paths.

The [demo](day53-demo-rehearsal.md), [clean-start](day54-clean-start.md), and [fallback](day55-integration-fallbacks.md) instructions still describe the supported setup. The current change adds no installation dependency or API schema change. Runtime debug output was absent from the frontend source review. Console output in replay commands and tests provides their intended verification result.

## Deferred work

Broader schema validation beyond fields rendered in the explanation panel, cancellation of work already running inside Ollama, high-concurrency load testing, GPU memory characterization, and detector retraining remain deferred. They need separate evidence and scope. The current acceptance covers the local capstone workflow and existing failure states. No critical or high software issue was identified in this focused review.
