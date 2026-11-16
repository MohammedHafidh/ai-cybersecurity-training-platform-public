# Day 38 backend integration

The public integration check captures one ordinary TCP connection to a listener
on loopback. It records the accepted connection and matching run metadata in
temporary files, then runs the existing parser, ingestion API, and combined
detection service. It reads the two saved predictions back after restarting the
application and checks that both reference the captured event. The raw log hash
is checked before and after processing.

The observed port count is one. The frozen rule returns benign, and the ML
prediction is stored and retrieved separately from the trusted label. This
checks system behavior on fresh benign evidence. It does not validate a
malicious scenario or independent teammate review.

From the repository root, with the pinned backend dependencies installed:

```text
python -m pytest -q backend/tests/test_day38_integration.py
```

The local default is a temporary SQLite database. Hosted CI also runs the test
with a disposable PostgreSQL 16 database.

The official milestone still requires a fresh approved attack-generated sample
and independent evidence review. Those have not been supplied. The backend
milestone tag remains pending. Keep any original lab evidence in the private
academic record.
