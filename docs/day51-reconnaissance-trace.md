# Day 51 reconnaissance trace

The browser regression now exercises raw connection log parsing for the third scenario. Its synthetic fixture contains three logged TCP connections across two distinct destination ports in one fixed 60-second window. It checks the distinct port count, connection count, rate of 0.05 connections per second, and 4.002468-second observed span. The rate uses the fixed window duration, while the span uses the first and last logged timestamps.

The test uses the [Day 49 checklist](day49-brute-force-trace.md) to verify run and event linkage, separate frozen predictions, stored feature values, the dashboard, and trusted MITRE references. It re-reads both detections after explanation and verifies they are unchanged. The fixture contains only synthetic log records. Hosted Chromium uses a controlled RAG response alongside the existing PostgreSQL and real FAISS API checks.

For a local replay of an existing approved private capture, the browser test accepts `CAPSTONE_NETWORK_LOG`, `CAPSTONE_NETWORK_METADATA`, `CAPSTONE_NETWORK_LOG_SHA256`, and `CAPSTONE_NETWORK_METADATA_SHA256`. Use a disposable database and set `CAPSTONE_TEST_LIVE_RAG=1` for live explanations. Keep raw files and browser artifacts private. This acceptance test expects one source/target TCP observation window.

## Fresh Day 51 acceptance

The approved scan report showed two open TCP ports. Timestamped target-side acceptance logs corroborated one connection to each port from the recorded lab client within the metadata window. The scan report establishes the port observations. The target log supplies connection counts and timestamps. Its original records had the explicit `unassigned` run marker. After verifying endpoint identity, source, ports and capture window, the replay used a private projection without that marker and a derived copy of metadata referencing the projection. The supplied files and the saved target log were preserved.

| Private evidence | SHA-256 |
| --- | --- |
| Scan text | `00a0e1a9bed05f5a987f62200c344ee76f93cf2570131955d1c56620a30cc942` |
| Scan XML | `305f65028f6f99aa01d2172ea46e7c4225b13909ea764b2bc1602d5ddf1d62ad` |
| Original metadata | `0fd8ebb07bd8dcfc456ad5ff8f433f6a877cb159f7fe3b9a3ddb3fdf2348f450` |
| Corroborating target log | `845c2979e97a47b5ef025e2a1e05d9ebb716d0ad56b9c2633941ddb750d4cf72` |

PostgreSQL 16 and Chromium matched two connections, two distinct ports, 2/60 connections per second, and a 0.002468-second observed span. The frozen rule and ML model both predicted malicious. The ML malicious-class score was 0.7511. Live FAISS and Gemma produced the expected threshold explanation and MITRE citations. Both stored detections remained unchanged. All three supplied hashes and the corroborating log digest were verified after replay.
