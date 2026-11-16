# Day 44 local explanation service

Day 44 adds an optional Ollama explanation service over a stored detection. The service reads the record, closes the database session, and sends allowlisted facts to Ollama on `127.0.0.1:11434`. It cannot rescore observations or update predictions. The frontend continues to show the deterministic evidence preview.

## Run locally

Install Ollama for your operating system and start its local server. Pull the [Gemma 3 1B model](https://ollama.com/library/gemma3:1b) with `ollama pull gemma3:1b`. On Windows PowerShell set `$env:CAPSTONE_OLLAMA_ENABLED = '1'` before starting FastAPI in the same terminal.

Use the existing ingestion and processing flow to create stored predictions. In FastAPI's `/docs`, call `GET /detections/{detection_id}/explanation` with one of the questions below. The route is read-only and uses the saved rule or ML prediction identified by the ID.

| Question | API value | Acceptance check on a real run |
| --- | --- | --- |
| What happened? | `what_happened` | The Day 38 approved authentication rule predicted malicious. A fresh benign loopback rule predicted benign. Neither result establishes attack success. |
| Why suspicious, or why did the rule stay below threshold? | `why_suspicious` | The authentication rule counted three failures at its threshold of three. The loopback rule counted one observed destination port, below two. |
| What evidence is available? | `what_evidence` | The authentication observation linked three normalized events. The benign loopback observation links one. Event and log references remain in detection detail. |

The question set draws on the [Day 38 acceptance record](day38-integration.md) and the real benign capture used for [frontend acceptance](day43-frontend-acceptance.md). Review each result against the matching stored record. Any claim about compromise, payload success, or why a specific feature caused the ML prediction would be unsupported.

## Grounding and resources

The model picks and orders only known fact IDs. The server builds the final text from those approved facts and leads with the question's primary fact when present. Raw logs, usernames, addresses, and free-form prompts stay outside the model request. No web or corpus retrieval runs in this increment.

Gemma 3 1B is roughly a 0.8 GB model download. The service uses a 2,048-token context, at most 96 output tokens, temperature zero, seed 44, a 45-second HTTP socket timeout, and a two-minute keep-alive. The small quantized model leaves room for the rest of the application on an RTX 2070 Super-class system. Use `ollama ps` to check actual CPU/GPU placement. Hardware and cold-start time vary.

The route returns 503 when disabled or unavailable and 502 when the model returns invalid or unsupported output. GitHub-hosted CI verifies the request boundary, evidence handling, and unchanged database records using a model stub. Local acceptance also requires a successful live call.

## Local validation

The live FastAPI check used Ollama 0.40.16 and `gemma3:1b` model ID `97558784bdc9`. Ollama reported 881 MB loaded, 100% CPU and 2,048 context tokens on the validation host. A fresh benign loopback run passed all three question checks. The rule stayed below its threshold of two with one distinct observed destination port, and the saved detection was byte-for-byte identical after the explanations. GPU placement on the target RTX 2070 Super was not measured.
