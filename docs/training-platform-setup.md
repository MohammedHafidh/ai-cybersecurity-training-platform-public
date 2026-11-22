# Training platform v2 — operator setup and student use

The operator starts the platform once. Students then use the browser for the entire journey; they do not run commands, find evidence files, or call APIs manually.

## One-time Windows operator preparation

Requirements: Python 3.12, Node.js 22, Docker Desktop's Linux engine, and the approved private lab bundle retained by the project owner. The public repository deliberately does not ship that bundle or private captures. Choose trusted executable paths when multiple Python/Node versions are installed.

```powershell
./setup-platform.ps1 -LabRoot '<approved-private-repository>/lab' -PythonPath '<Python-3.12-executable>' -NodePath '<Node-22-executable>'
ollama pull gemma3:1b
```

Setup installs the existing pinned backend/ML/CPU-retrieval dependencies in `.venv`, verifies the private bundle against `docs/training-lab-manifest.json`, builds the six approved images, and caches the pinned Sentence Transformer. It does not execute an attack. Do not approve a changed bundle by simply regenerating hashes: inspect and test changes first.

Operator configuration, model cache, diagnostics, generated knowledge index and new evidence live under `%LOCALAPPDATA%/CapstoneTraining`, outside the public repository. `CAPSTONE_TRAINING_HOME` can select a dedicated operator data directory before setup/start; students cannot set it through HTTP. Archived private evidence is not used as the output directory.

## Start and stop

```powershell
./start-platform.ps1 -OpenBrowser
./stop-platform.ps1
```

Default URL: `http://localhost:8000`. If occupied, use `./start-platform.ps1 -Port 8035 -OpenBrowser`. Stop reads the recorded instance, so its port does not need to be supplied again. The launcher validates instance identity before stopping a process. It does not stop an unrelated service already using the requested port.

Start prepares the separate PostgreSQL service/schema, builds the frontend, launches loopback FastAPI, serves the frontend from that same origin and checks readiness. It starts Ollama if an installed local executable is available; model absence or generation failure uses the explicitly labeled teaching fallback. Starting the platform never starts an exercise. Initial builds/downloads can take time; failures are reported rather than hidden.

The launcher normally uses `.venv/Scripts/python.exe` and Node from setup. An operator may explicitly use `-PythonPath` and `-NodePath` with an existing correctly provisioned environment. This is an explicit environment choice, not an additional hidden dependency.

Stop requests cancellation, waits for owned exercises to release their active slot, stops only the recorded API instance and takes down the dedicated database container/network. It preserves the PostgreSQL volume, new private evidence, archived evidence, cached images and model weights. Docker Desktop and Ollama remain available as local dependencies. If cancellation cannot finish, stop reports failure and leaves the server available for recovery.

Only one training instance may use the training database at a time. A PostgreSQL advisory lock enforces this. On restart after an interrupted API process, owned stale exercise resources are cleaned up and their records marked failed; no replay replaces them. Do not run multiple Uvicorn workers.

## Student use

1. Open Home and choose one of the three scenarios.
2. Read its objectives and safety boundary.
3. Click **Start Controlled Exercise**. The backend creates a new run and captures new logs.
4. Follow real stages into Analysis; inspect the sanitized logs, normalized events and features.
5. Compare trusted ground truth with both independent predictions. Errors and disagreements remain visible.
6. Ask a bounded natural-language question. Sources and live/fallback status remain visible.
7. Answer four curated questions, read feedback and pass with at least 3/4.
8. Mark the scenario complete, review it, return Home or continue to another lesson.

**Sample / Demonstration Mode** is separate and explicit. It creates harmless synthetic benign records, not a real attack. Those examples can expose detector false positives. An unavailable live exercise is never silently changed into a sample.

## Manual operator fallback

From the repo root, activate the provisioned Python environment and run:

```powershell
docker compose -f compose.training.yml up -d --wait
$env:DATABASE_URL='postgresql+psycopg://capstone_training:local_training_only@127.0.0.1:55435/capstone_training'
$env:PYTHONPATH='backend'
python -m app.persistence.setup_core
$env:CAPSTONE_TRAINING_ENABLED='1'
$env:CAPSTONE_SERVE_FRONTEND='1'
$env:CAPSTONE_OLLAMA_ENABLED='1'
$env:HF_HOME=Join-Path $env:LOCALAPPDATA 'CapstoneTraining/models'
$env:FRONTEND_ORIGIN='http://localhost:8000'
$env:VITE_API_BASE_URL='http://localhost:8000'
Push-Location frontend
npm ci
npm run build
Pop-Location
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Stop a manually started API with Ctrl+C after cancelling/waiting for its exercise in the UI. Then use `docker compose -f compose.training.yml down` without `--volumes`. Restart uses the same recovery logic if the API was interrupted. The automatic stop script is only for instances started by the launcher.

## Verification modes

Ordinary CI retains the original detector/API/browser tests and adds guides plus complete **sample** journeys on PostgreSQL. It cannot claim to execute the private lab.

For real acceptance on the configured machine, start the platform and run the separate browser check:

```powershell
$env:CAPSTONE_PLATFORM_URL='http://localhost:8000'
$env:API_SMOKE_URL=$env:CAPSTONE_PLATFORM_URL
$env:CAPSTONE_LIVE_ACCEPTANCE='1'
# From frontend, with the documented Python/Node environment on PATH:
npx playwright test browser/training.spec.mjs
```

The acceptance test clicks the same student controls; API reads only observe persistence and provenance. It must not substitute an old capture. Keep raw captures private; publish only safe counts, hashes, citations, scores and stage results. No final v2 release tag is authorized yet.

## Limits retained

The frozen model/rules and twelve-run evaluation are unchanged, including their false positives and false negatives. Explanations are bounded/extractive over trusted content; this is not an unrestricted cybersecurity chatbot or causal ML attribution system. Browser cancellation may not cancel an Ollama computation already in progress. The app is designed for a local single-user capstone, not an untrusted public multi-user deployment. Completion is remembered by browser exercise identifiers, not authenticated accounts.
