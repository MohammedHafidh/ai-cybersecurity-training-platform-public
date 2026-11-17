# Day 53 demo rehearsal

The demo replays one synthetic authentication capture through the frozen detectors and persists both outputs in a disposable PostgreSQL 16 database. The browser can display the run, event references, rule result, and ML prediction. The optional local RAG step verifies citations and confirms that explanation leaves the saved outputs unchanged.

## Start

Use Python 3.12, Node.js 22, and a running Docker engine with Compose. Ports 55433, 8000, and 5173 must be free. From the repository root, install dependencies and start the database.

```text
python -m pip install -r backend/requirements.txt -r requirements/day27.txt
docker compose version
docker compose -f compose.demo.yml up -d --wait
```

In the same terminal, set the environment and start the API. These are PowerShell commands. In Bash, use `export DATABASE_URL='…'` and `export PYTHONPATH=backend` for the same values.

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://capstone_demo:demo_fixture_only@127.0.0.1:55433/capstone_demo'
$env:PYTHONPATH = 'backend'
python -m app.persistence.setup_core
python -m uvicorn app.main:app --app-dir backend
```

In a second terminal, start the dashboard.

```text
cd frontend
npm ci
npm run dev -- --strictPort
```

## Replay and inspect

In a third terminal at the repository root, run `python scripts/demo_replay.py`. The command checks database readiness, ingests the capture, processes it, reads both stored predictions, and prints the run ID and labels. Open `http://localhost:5173`, then select that run under **Detection evidence**.

For live grounded explanations, complete the [Ollama setup](day44-local-explanations.md) and [retrieval setup](day46-retrieval.md) in the API Python environment first. Set `CAPSTONE_OLLAMA_ENABLED=1` in the API terminal before starting it. Run `python scripts/demo_replay.py --rag` to check a fresh synthetic replay with citations, or use **Grounded explanation** for the displayed run.

## Stop and reset

Press Ctrl+C in the dashboard and API terminals. From the repository root run `docker compose -f compose.demo.yml down --volumes`. This removes the disposable demo database and its stored runs. The command operates on the dedicated Compose project. Start again using the same sequence. To confirm a clean reset, check that `/events` and `/detections` return empty arrays before replay.

Hosted CI runs the documented database lifecycle and replay twice and checks that each start has empty events and detections. The existing Chromium and retrieval checks cover the UI and retrieval separately. The default replay uses a synthetic capture. Previously approved private evidence stays in its archive.

The solo local rehearsal passed startup, replay with a live grounded citation, shutdown, reset, and a second replay. Both starts had empty events and detections before replay. No blocking issue was observed. Live explanations require a working local Ollama service and cached embedding weights. The documented baseline replay runs without them.
