# Day 34 normalized ingestion

Set up the core tables using the [Day 33 instructions](day33-postgresql.md).
Send one JSON request to `POST /ingestion/runs` with a `source_type`, a `run`
object containing the run metadata JSON, and a non-empty `events` array
containing normalized event objects. Convert normalized JSONL to an array
before sending it. The OpenAPI schema at `/docs` lists the fields.

FastAPI validates the JSON before opening a database connection. The request
checks the run and event IDs, source family, label, scenario, timestamps, and
declared log references. The service inserts the run and its events in one
transaction. Label and scenario come from the run record. The event stores
its original filename as a reference and keeps observable fields in JSON.
Collection notes and the full metadata file remain with the source record.
The API accepts normalized JSON only. It never opens or modifies raw files.

The endpoint returns `201` with the run ID and event count, `422` for invalid
requests, `409` for an existing run or event ID, and `503` when persistence is
unavailable. A conflict rolls back the whole submitted run. Keep this endpoint
within a trusted environment. Labels describe caller-supplied ground truth.

Tests use synthetic samples for all three sources, malformed input, and a
database conflict. Hosted CI runs the persistence tests on PostgreSQL 16.
Independent teammate sample review was unavailable.
