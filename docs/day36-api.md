# Day 36 API contract

Install the backend and pinned ML dependencies as described in the README.
Configure PostgreSQL and install the core tables using the [Day 33 guide](day33-postgresql.md).
FastAPI publishes interactive documentation at `/docs` and the schema at
`/openapi.json`.

| Method | Path | Response |
| --- | --- | --- |
| GET | `/health` | API liveness |
| GET | `/health/database` | Core database readiness |
| POST | `/ingestion/runs` | Ingest normalized metadata and events, returning the run ID and event count |
| POST | `/runs/{run_id}/process` | Score the ingested run with both frozen detectors and return the combined result and stored detection IDs |
| GET | `/events?limit=20` | Latest normalized event summaries and raw filename references |
| GET | `/detections?limit=20` | Latest stored prediction summaries |
| GET | `/detections/{detection_id}` | One stored prediction with its observation evidence |

Ingest first, then process using the returned `run_id`. Processing writes both
detectors' outputs in one transaction. Repeating the same run and detector
versions returns the same IDs without duplicate rows. If an observation covers
multiple events, its single `event_id` is null and its full event references
appear in `evidence.event_ids`. Ground truth appears separately in the combined
processing response. Stored rule evidence records the observed count and
threshold. ML evidence records the model score. Neither is a ground-truth label.

Lists return newest first, with a limit of 1 to 100. Unknown runs or predictions
return `404`. Invalid input or unscorable observations return `422`.
Database and model availability failures return `503`. Use the API in a
trusted environment.

The legacy comparison endpoints remain available. Hosted CI checks this API
against PostgreSQL 16 with synthetic normalized fixtures. Day 35's tests
continue to check the detectors against frozen development decisions.
Independent teammate verification using original lab samples was unavailable.
