# Day 38 backend integration

The public integration check captures one ordinary TCP connection to a listener
on loopback. It records the accepted connection and matching run metadata in
temporary files, then runs the existing parser, ingestion API, and combined
detection service. It reads the two saved predictions back after restarting the
application and checks that both reference the captured event. The raw log hash
is checked before and after processing.

The observed port count is one. The frozen rule returns benign, and the ML
prediction is stored and retrieved separately from the trusted label. This
checks system behavior on fresh benign evidence. Attack-evidence validation
is a separate acceptance check.

From the repository root, with the pinned backend dependencies installed:

```text
python -m pytest -q backend/tests/test_day38_integration.py
```

The local default is a temporary SQLite database. Hosted CI also runs the test
with a disposable PostgreSQL 16 database.

The capstone is now a solo project. The project owner is responsible for
validation, evidence review, and the final verification record. The public
benign test is automated. The owner’s attack-evidence verification is pending
a fresh approved sample with matching run metadata. Keep the original log
and run metadata in the private academic record, and publish only a
non-sensitive reference, hashes, and verification results. The backend
milestone tag follows that verification.
