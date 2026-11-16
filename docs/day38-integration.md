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

## Private attack evidence verification

The sole project owner supplied the approved capture and its metadata. The
automated verification for the owner's validation record used PostgreSQL 16.
The original files remain in the private academic record.

| Evidence reference | SHA-256 |
| --- | --- |
| Authentication log | `5336c410badcb93d997e8fd71e9fd5b5076a32d63ce7c16157d1136e37d372d9` |
| Run metadata | `cbf63b3f5553389b0201d8000e4422a5a576f6f604f00fe8889e93fd154a2d14` |

The parser accepted three failed login events in one 60-second window. Trusted
metadata labeled the run malicious. The frozen authentication rule counted
three failures at its threshold of three and predicted malicious. The frozen
Logistic Regression model independently predicted malicious with a score of
0.8013. Both persisted decisions matched their processing responses and linked
to all three accepted events after application restart. Reprocessing returned
the same IDs. Both original hashes matched again after verification.

The metadata reader now accepts a UTF-8 byte-order mark. The normalizer can
resolve a declared log reference relative to an explicit evidence root, without
editing the original metadata or opening a file outside that root.

This verifies one backend integration case. The official held-out metrics
remain those from Day 32.
