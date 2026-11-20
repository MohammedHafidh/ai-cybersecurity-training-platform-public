# Final technical guide

## Problem and objective

Students need to connect a security alert with the observed behavior that caused it. This capstone provides an inspectable local training pipeline across brute force, SQL injection and network reconnaissance. The dashboard compares a rule baseline and an ML prediction, shows event provenance, and offers a grounded explanation. Accuracy is evaluated on the project's scripted lab data.

## Baseline and setup

The stable technical baseline is `rc1` at `bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa`. Its [manifest](evidence/day60/rc1-manifest.json) records source and frozen-artifact hashes. Day 60 finalizes documentation on top of that baseline.

Use Python 3.12, Node.js 22, Docker Compose and available loopback ports 55433, 8000 and 5173. Follow the [start, process, stop and reset runbook](day53-demo-rehearsal.md). Set `DATABASE_URL` and `PYTHONPATH` in the API terminal, initialize the schema, and start FastAPI. Use `npm ci` in the frontend directory. The default frontend API origin is `http://localhost:8000`; the API permits the explicit frontend origin `http://localhost:5173`. Set `VITE_API_BASE_URL` before building for another local API address.

For local explanations, install the CPU PyTorch and retrieval dependencies in the same backend Python environment, as listed in [Day 46](day46-retrieval.md). The saved FAISS index is already included. Cache the pinned embedding model once with:

```text
python -c "import sys; sys.path.insert(0,'backend'); from app.detection.retrieval import load_encoder; load_encoder(local_files_only=False)"
```

Start Ollama locally, run `ollama pull gemma3:1b`, and set `CAPSTONE_OLLAMA_ENABLED=1` in the API terminal before starting it. See the [explanation setup](day44-local-explanations.md), [RAG API](day47-grounded-explanations.md) and [training panel](day48-frontend-rag.md). The pinned Sentence Transformer is `all-MiniLM-L6-v2` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Its normalized 384-dimensional embeddings populate the six-row FAISS index.

## API and persistence

Interactive OpenAPI documentation is available at `/docs`. The [architecture](architecture.md) shows the complete data flow, and the [database reference](day33-postgresql.md) describes keys and tables.

| Route | Input or result |
| --- | --- |
| `GET /health`, `GET /health/database` | API liveness and core schema readiness. |
| `POST /ingestion/runs` | Validated source family, trusted run metadata, and normalized events. |
| `POST /runs/{run_id}/process` | Reuse frozen feature builders and save both predictions. Reprocessing returns the existing detection identities. |
| `GET /events`, `GET /detections` | Recent records; the UI requests at most 20. |
| `GET /detections/{detection_id}` | Evidence, run context and the corresponding other detector output for the same observation. |
| `GET /evaluation/summary` | Frozen Day 32 aggregate report. |
| `GET /detections/{detection_id}/rag-explanation` | One supported training question, cited background passages and stored facts. |

Run context includes the trusted expected label, scenario, source and target. Predictions occupy detector records. Numeric model scores are labeled as malicious-class scores. The source and target are collection endpoints; a detector result does not establish compromise.

## Dataset, model and evaluation

Trusted labels are assigned by the controlled run protocol before detection. Parsers join that metadata to accepted events; model features exclude trusted labels. Dataset v1 development splits are run-disjoint: 18 training runs, six validation runs and six historical test runs. The validation split has seven feature rows because a run can contribute multiple observation windows. Those historical test templates were explored during development.

The separate final evaluation collection has twelve reserved runs, with two benign and two malicious per scenario. The frozen `capstone-ml-v1` Logistic Regression pipeline and `rule-engine-v1` score the same runs. A run alerts if any observation is predicted malicious. The [Day 56 package](day56-final-evaluation.md) contains exact CSV values, figures and dataset/model provenance.

| Detector | Accuracy | Precision | Recall | F1 | FPR | TN / FP / FN / TP |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Rules | 41.7% | 44.4% | 66.7% | 53.3% | 83.3% | 1 / 5 / 2 / 4 |
| ML | 75.0% | 80.0% | 66.7% | 72.7% | 16.7% | 5 / 1 / 2 / 4 |

Actual labels form matrix rows and predictions form columns, in benign/malicious order. Rates with a zero denominator follow the frozen report's zero convention. The separate Day 52 benign phrase “select a category” falsely alerts in both detectors and remains a regression case.

## Grounding and verification limits

The approved corpus consists of three project-authored scenario notes, attributed to project records, MITRE ATT&CK and OWASP. Retrieval chooses relevant scenario passages. Gemma selects supplied evidence IDs. The server builds the response from stored facts and approved passages, retaining citations. Unsupported questions return an explicit unsupported response. The LLM supplies explanations only.

The evidence package links [verified private captures and a public synthetic screenshot](evidence/day60/README.md). Hosted CI uses synthetic logs and model stubs for browser RAG, while its retrieval job exercises the real index. Live Gemma reviews were performed locally. Database and explanation outages, malformed inputs, slow inference and malformed citations are covered by [Day 57](day57-robustness.md) and [Day 58](day58-issue-triage.md).

The [fallback guide](day55-integration-fallbacks.md) covers SQLite, unavailable local models and offline screenshots. The twelve-run dataset cannot establish production performance. Heavy concurrency and GPU memory pressure are unmeasured. A browser timeout may leave Ollama work running, and credential-pattern scanning has limited coverage. No unresolved release-blocking software issue was identified in the RC1 review. See the [release checklist](day59-release-candidate.md) for the operational assumptions.
