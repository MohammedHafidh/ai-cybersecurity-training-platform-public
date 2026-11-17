# Day 55 integration closeout

The compact regression combines the three raw-log browser smoke paths from Days 49–51, the benign comparisons and contract checks from Day 52, and the clean PostgreSQL replay and reset from Days 53–54. The frozen detectors, evaluation, and evidence contracts remain the reference outputs.

| Demo problem | Fallback |
| --- | --- |
| Live lab evidence is unavailable | Use the [disposable demo replay](day53-demo-rehearsal.md). It creates a new synthetic run and prints the run ID for finding both predictions in the dashboard. Identify it as a synthetic replay during the demo. |
| PostgreSQL is unavailable | In the API terminal, use a new disposable SQLite file with `DATABASE_URL=sqlite:///./demo-fallback.db`. In PowerShell use `$env:DATABASE_URL = 'sqlite:///./demo-fallback.db'`. Then set `PYTHONPATH`, initialize the schema, and start FastAPI as in the runbook. Run the same synthetic replay. Start with an unused filename to avoid carrying over demo data. |
| Ollama or retrieval is unavailable | Open the detection evidence page and use its stored rule and ML outputs and the deterministic explanation preview. The grounded panel reports the service error. |
| The application cannot be started | Download the `day55-demo-fallback` artifact from a successful verification run ahead of time. Open its screenshot alongside the JSON trace. The screenshot shows the synthetic run ID and stored evidence with a real explanation-service 503. The JSON links that screenshot to the same run, event IDs, threshold, and detector results. |

## Traceable evidence

The backup artifact contains a screenshot and JSON generated from the same synthetic run on SQLite. Chromium verifies the run and observation linkage and compares both saved predictions before and after the error response. The real private captures stay in their archive. Their public provenance and acceptance results are recorded in the [authentication](day49-brute-force-trace.md), [web](day50-sql-injection-trace.md), [network](day51-reconnaissance-trace.md), and [clean-start](day54-clean-start.md) records.

The [benign web false alert](day52-integration-regression.md) remains visible in the regression. SQLite covers the disposable demo fallback. PostgreSQL remains the standard integration database. Live explanations still require the local model and retrieval cache. The `integrated-system` milestone is published after the merged commit passes hosted verification.
