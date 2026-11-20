# Day 57 failure-path review

Day 57 exercises database unavailability, malformed ingestion, empty retrieval, malformed retrieval metadata, Ollama connection failure and timeout, and delayed browser inference. The tests keep the Day 56 results and frozen detector behavior as their reference.

| Failure | Verified behavior |
| --- | --- |
| Database connection fails | Event, detection and explanation reads return a generic 503. The dashboard shows retry controls. Frozen evaluation remains available. |
| Malformed ingestion | The API returns 422 before storing the request. |
| No relevant retrieved chunks | The RAG route returns 503 before calling the model. Stored predictions remain readable and reprocessing still works. |
| Malformed retrieved metadata | A missing field, invalid source, or malformed record now returns 503. Previously this could escape the error handler and produce an unhandled server error. |
| Ollama refuses a connection or exceeds its socket timeout | The service closes the connection and returns 503. Prediction readback still works. |
| A local explanation is waiting | A concurrent read returns the saved prediction. The explanation session has already released its database connection. |
| The browser waits too long | At 50 seconds it shows the error and retry control. The stored results and deterministic explanation remain visible. |

Hosted CI runs the backend failure regressions on SQLite and PostgreSQL and runs the browser cases in Chromium. Existing sanity checks continue to cover the three scenario smoke paths, benign comparisons and grounded citations. The only runtime fix catches invalid retrieval data at the existing service boundary.

## Detector limitations and resources

The [Day 56 report](day56-final-evaluation.md) still records five false positives and two false negatives for rules and one false positive and two false negatives for ML on twelve held-out lab runs. The [Day 52 benign web case](day52-integration-regression.md) remains a false alert from both detectors. These are detector limitations, with the trusted labels visible alongside predictions.

The browser deadline cancels its request. Work already running in Ollama may continue until the service finishes or the HTTP socket times out. The 45-second socket timeout measures idle network waits, and does not guarantee a total wall-clock deadline for all retrieval and inference work. Large request concurrency and GPU memory pressure are outside these compact failure checks. Local explanations depend on the model and embedding cache. The deterministic evidence view remains available when the database is reachable.
