# Day 54 clean-start integration

Use a fresh checkout, a new Python virtual environment, and the [Day 53 demo database and startup commands](day53-demo-rehearsal.md). Run the core ingestion, detection API, and benign contract tests, then use the existing browser trace against PostgreSQL. The hosted job installs frontend dependencies with `npm ci`, checks the generated API contract, starts a fresh Compose database, and runs the browser trace against that database. It uses synthetic raw log fixtures. The private replay option remains documented in the [Day 49 trace](day49-brute-force-trace.md).

## Setup fix

A Windows checkout with `core.autocrlf=true` changed the generated TypeScript schema to CRLF, causing the byte-for-byte API check to fail. Git now checks out that generated file with LF. The generated schema contents and the API contract are the same. Existing checkouts can use `npm run api:generate` once from the frontend directory to restore the generated file's line endings.

## Environment and acceptance

GitHub-hosted verification uses Python 3.12, Node.js 22, Chromium, and PostgreSQL 16. The demo database requires Docker Compose and loopback ports 55433, 8000, and 5173. Dependency installs, image pulls, and the optional local Gemma and embedding weights affect first-start time. Once the PostgreSQL image is cached, the local Compose health check becomes ready in seconds. Live RAG needs local Ollama and the pinned Sentence Transformer cache. Hosted Chromium uses a controlled model response, with real FAISS retrieval verified separately.

The clean-start application replay uses existing evidence. A separate clean-lab live attack reproduction remains pending.
