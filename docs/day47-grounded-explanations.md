# Day 47 grounded explanations

Use `GET /detections/{detection_id}/rag-explanation` to request an explanation with source references. The route copies typed facts from a saved detection and derives the retrieval topic from the stored run's source family. It searches the saved FAISS index and passes only the relevant scenario's trusted chunks and allowlisted facts to local Gemma. The typed question accepts `what_happened`, `why_suspicious`, and `what_evidence`, as well as equivalents such as “Why was this suspicious?”

A `grounded` response separates the run-specific `text` and `evidence_ids` from the background `sources`. Each source carries its frozen chunk ID, section, passage, source path, hash, and references. Ollama selects from server-supplied IDs. The server renders the saved facts and attaches trusted passages by those IDs. If the selection omits a source, the response attaches the highest-ranked in-scope passage. The source text provides lab context. Only the stored evidence describes what happened in the selected run.

Other questions return `unsupported` with empty evidence and citations. Questions asking for why an ML model flagged an observation also return `unsupported` when the stored record lacks a rule comparison. Unsupported prompts never reach the retriever or model. A missing detection returns 404, unavailable local dependencies return 503, and invalid model selections return 502.

Use the [Day 44 Ollama setup](day44-local-explanations.md) and the [Day 46 retrieval dependencies and model cache](day46-retrieval.md) in the backend's Python environment. Enable local explanations with `CAPSTONE_OLLAMA_ENABLED=1`. Both the original explanation route and the RAG route are read-only. See the [Day 48 training interface](day48-frontend-rag.md) for dashboard usage.

## Solo evidence review

The local check used the [approved Day 38 authentication capture](day38-integration.md), the saved FAISS index, the pinned Sentence Transformer, and Gemma 3 1B. It verified the private evidence hashes before and after processing.

| Question | Verified response |
| --- | --- |
| Why was this suspicious? | The stored rule counted three failed SSH password events at its threshold of three, linked to three normalized records. The response cited `v1:brute_force:01`, which provides [MITRE ATT&CK T1110](https://attack.mitre.org/techniques/T1110/) context. |
| Which account was compromised? | The route returned `unsupported` with no sources or model output. The capture establishes failed attempts and gives no basis for a compromise claim. |

The stored rule and ML responses were byte-for-byte unchanged. Hosted CI checks the API behavior and persistence, including PostgreSQL, and exercises the saved FAISS index with an Ollama stub. The live Ollama review ran locally.
