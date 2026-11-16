# Day 43 frontend acceptance

The non-LLM dashboard reads real FastAPI responses for its core views.

| View | Endpoint |
| --- | --- |
| API connection | `GET /health` |
| Recent events | `GET /events` |
| Detection evidence | `GET /detections` and `GET /detections/{detection_id}` |
| Held-out evaluation | `GET /evaluation/summary` |

The evaluation view uses the generated API contract and shows a retry when the summary is unavailable. The explanation preview uses the selected detection's stored evidence.

## Solo acceptance check

The Chromium smoke test exercises a production frontend build against a running FastAPI server. It opens a real benign loopback TCP connection, records and normalizes the accepted connection using the existing Day 38 capture, then ingests and processes it over HTTP. It follows the dashboard navigation and verifies the same run across recent events and detection detail. The event ID and log reference let a learner trace the result back to its observation. The rule displays one observed destination port below its threshold of two. The stored ML output and the deterministic explanation remain distinct. The test also switches evaluation scopes and checks recovery after a 503 response.

GitHub-hosted CI uses a disposable database for the Chromium run and separately executes the existing PostgreSQL verification. No private evidence or raw capture is published.

## Remaining limitations

- The dashboard limits recent events and predictions to 20 records. Older records are outside the current browser list.
- The acceptance run covers one benign loopback observation in Chromium. Scenario-specific API tests cover the three lab scenarios, and the held-out metrics remain scoped to the frozen lab dataset.
