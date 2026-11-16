# Day 33 PostgreSQL foundation

Set `DATABASE_URL` to a PostgreSQL URL using the `postgresql+psycopg` scheme.
From `backend`, run `python -m app.persistence.setup_core` before serving requests.
The setup is additive and safe to repeat sequentially. It creates the three v1
tables in one transaction. Future column changes require an explicit migration.
Run schema setup with the schema owner and use a restricted role for serving.
The `GET /health/database` route verifies that the configured connection can
query the core tables. The existing `GET /health` route remains a liveness check.

| Table | Traceability |
| --- | --- |
| runs | Run ID, source family, scenario, trusted expected label, source/target identifiers, collection window |
| events | Event ID, parent run/source, timestamp, raw filename, event type and attributes |
| detections | Detection ID, parent run, optional event from that same run, detector/version, prediction and evidence |

An event must match its parent's source family. A detection can represent a
whole run, or reference an event within that run. Trusted expected labels and
detector predictions occupy separate tables. Existing comparison tables are
retained. Independent teammate review was unavailable.

Run `python -m pytest -q backend/tests/test_core_persistence.py` from the root
for the schema smoke tests. Set `CAPSTONE_TEST_DATABASE_URL` to a **fresh,
disposable** PostgreSQL database for the integration version of the round trip.
