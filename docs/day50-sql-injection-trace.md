# Day 50 SQL injection trace

The browser regression now starts the web scenario from a raw, structured HTTP log and matching run metadata. The public fixture uses the harmless phrase “select a category” to exercise query decoding and the existing token-count heuristic. It sends no web request to a lab target. An alert on the fixture demonstrates the trace and the rule's limits.

The regression reuses the [Day 49 checklist](day49-brute-force-trace.md). It verifies that parsed request IDs and counts reach the frozen rule and ML pipeline, that both persisted predictions match processing, and that the dashboard shows the same run, event IDs, log reference and measured rule count. The RAG panel must show the corresponding threshold and approved OWASP references. The check reads the saved records again after explanation and compares them with the earlier reads.

Hosted Chromium uses a controlled RAG response. The existing hosted PostgreSQL and real FAISS retrieval checks still run. A local replay can use live FAISS and Ollama by setting `CAPSTONE_TEST_LIVE_RAG=1` as in Day 49. For an existing approved private web capture, the same test reads the log and metadata from `CAPSTONE_WEB_LOG` and `CAPSTONE_WEB_METADATA` and verifies their SHA-256 values from `CAPSTONE_WEB_LOG_SHA256` and `CAPSTONE_WEB_METADATA_SHA256`. Keep the input files and browser artifacts private.

## Fresh Day 50 acceptance

The project owner supplied the approved fresh capture from the isolated private lab. Both hashes matched before and after replay. The raw files remained private.

| Evidence | SHA-256 |
| --- | --- |
| HTTP log | `d139a4e5c6c3c056b138daca285283eef349bd0ee08de1d47b49ea3ea568452e` |
| Run metadata | `914035d529f698fd31b105e9f1460d68d4e9b8e7ae5d4a950c36ea72a180df19` |

The parser produced one linked HTTP request. PostgreSQL 16 preserved its method, path, response status and normalized input. Chromium showed the same run, event ID, log reference and rule count. The frozen rule counted one SQL-like token match at its threshold of one and predicted malicious. The frozen ML model separately predicted malicious with a malicious-class score of 0.9111. Live FAISS and Gemma returned the matching rule explanation with the approved OWASP references. Both stored predictions were identical before and after explanation. The token match supports the detector's reason for flagging the request. It cannot establish that the injection succeeded.
