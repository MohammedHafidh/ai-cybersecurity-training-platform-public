# Day 54 clean-start integration

Use a fresh checkout, a new Python virtual environment, and the [Day 53 demo database and startup commands](day53-demo-rehearsal.md). Run the core ingestion, detection API, and benign contract tests, then use the existing browser trace against PostgreSQL. The hosted job installs frontend dependencies with `npm ci`, checks the generated API contract, starts a fresh Compose database, and runs the browser trace against that database. It uses synthetic raw log fixtures. The private replay option remains documented in the [Day 49 trace](day49-brute-force-trace.md).

## Setup fix

A Windows checkout with `core.autocrlf=true` changed the generated TypeScript schema to CRLF, causing the byte-for-byte API check to fail. Git now checks out that generated file with LF. The generated schema contents and the API contract are the same. Existing checkouts can use `npm run api:generate` once from the frontend directory to restore the generated file's line endings.

## Environment and acceptance

GitHub-hosted verification uses Python 3.12, Node.js 22, Chromium, and PostgreSQL 16. The demo database requires Docker Compose and loopback ports 55433, 8000, and 5173. Dependency installs, image pulls, and the optional local Gemma and embedding weights affect first-start time. Once the PostgreSQL image is cached, the local Compose health check becomes ready in seconds. Live RAG needs local Ollama and the pinned Sentence Transformer cache. Hosted Chromium uses a controlled model response, with real FAISS retrieval verified separately.

## Fresh clean-lab acceptance

The project owner reported removing the old lab containers and network and rebuilding the isolated authentication lab before collecting the fresh capture. The supplied metadata identified the approved Day 54 authentication reproduction. The parser verified three failed SSH password events for the same run.

| Private evidence | Measured SHA-256 |
| --- | --- |
| Authentication log | `6cc6f143d32bd4dc191238ca14bc7630085d6fbf770559a097b0ada00efca1a1` |
| Matching metadata | `c1b4196c58450b01d94bd9a2fd2d43786db2621f761a607fec5a6bf2151711d7` |

The reported metadata digest transposed two adjacent characters. The measured file digest above was identical before and after replay, as was the supplied authentication log digest. The raw files stayed private.

The local clean checkout passed 14 core tests and the generated API contract check. A fresh PostgreSQL 16 database started with empty event and detection lists. Chromium traced the new capture through the dashboard to both saved predictions. The rule counted three failures at its threshold of three. Both frozen detectors predicted malicious, with a malicious-class ML score of 0.8013. Live FAISS and Gemma returned the expected threshold explanation and trusted references. Both saved predictions were identical before and after explanation.
