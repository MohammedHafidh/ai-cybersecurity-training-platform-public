# Day 51 reconnaissance trace

The browser regression now exercises raw connection log parsing for the third scenario. Its synthetic fixture contains three logged TCP connections across two distinct destination ports in one fixed 60-second window. It checks the distinct port count, connection count, rate of 0.05 connections per second, and four-second observed span. The rate uses the fixed window duration, while the span uses the first and last logged timestamps.

The test uses the [Day 49 checklist](day49-brute-force-trace.md) to verify run and event linkage, separate frozen predictions, stored feature values, the dashboard, and trusted MITRE references. It re-reads both detections after explanation and verifies they are unchanged. The fixture contains only synthetic log records. Hosted Chromium uses a controlled RAG response alongside the existing PostgreSQL and real FAISS API checks.

For a local replay of an existing approved private capture, the browser test accepts `CAPSTONE_NETWORK_LOG`, `CAPSTONE_NETWORK_METADATA`, `CAPSTONE_NETWORK_LOG_SHA256`, and `CAPSTONE_NETWORK_METADATA_SHA256`. Use a disposable database and set `CAPSTONE_TEST_LIVE_RAG=1` for live explanations. Keep raw files and browser artifacts private. This acceptance test expects one source/target TCP observation window.

Fresh Day 51 capture acceptance remains open. The synthetic regression checks the software path. The fresh acceptance review must compare the dashboard's aggregates with the captured connections and verify live citations.
