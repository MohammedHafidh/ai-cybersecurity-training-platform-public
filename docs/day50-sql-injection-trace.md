# Day 50 SQL injection trace

The browser regression now starts the web scenario from a raw, structured HTTP log and matching run metadata. The public fixture uses the harmless phrase “select a category” to exercise query decoding and the existing token-count heuristic. It sends no web request to a lab target. An alert on the fixture demonstrates the trace and the rule's limits.

The regression reuses the [Day 49 checklist](day49-brute-force-trace.md). It verifies that parsed request IDs and counts reach the frozen rule and ML pipeline, that both persisted predictions match processing, and that the dashboard shows the same run, event IDs, log reference and measured rule count. The RAG panel must show the corresponding threshold and approved OWASP references. The check reads the saved records again after explanation and compares them with the earlier reads.

Hosted Chromium uses a controlled RAG response. The existing hosted PostgreSQL and real FAISS retrieval checks still run. A local replay can use live FAISS and Ollama by setting `CAPSTONE_TEST_LIVE_RAG=1` as in Day 49. For an existing approved private web capture, the same test reads the log and metadata from `CAPSTONE_WEB_LOG` and `CAPSTONE_WEB_METADATA` and verifies their SHA-256 values from `CAPSTONE_WEB_LOG_SHA256` and `CAPSTONE_WEB_METADATA_SHA256`. Keep the input files and browser artifacts private.

## Acceptance status

Fresh Day 50 evidence has yet to be supplied. The synthetic regression establishes the software path. Acceptance still requires matching the displayed evidence to the fresh approved capture through PostgreSQL, the dashboard, and live RAG.
