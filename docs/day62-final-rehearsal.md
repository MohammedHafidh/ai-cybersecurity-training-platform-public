# Day 62 clean-checkout verification

## Source and environment

A new clone of the public repository was checked out at Day 61 commit `df30767e4be8b76148a45c67f25c091f150af03a` (tree `e55567df4df5fb5e3cc9a978ffc6ee60c4a69157`). The original `rc1` tag remains at `bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa`. Its original source archive hash and frozen artifact hashes remain in the [RC1 manifest](evidence/day60/rc1-manifest.json).

The clean environment used Python 3.12.16, Node 22.23.5, a new virtual environment, `npm ci`, new Chromium installation and a new embedding-model cache populated from the documented pinned revision. Docker Desktop and the explicitly required local Ollama/Gemma service were available system prerequisites. No previous project virtual environment, ignored model file or private raw capture is necessary for the public synthetic demo. Network downloads and adequate disk space are required on first setup; the public project does not bundle the Ollama or embedding-model weights.

The README, demo runbook and linked retrieval/explanation instructions were followed. The documented dependency installation, CPU retrieval extras, frontend production build and generated API-contract check passed. All 200 backend tests passed with zero skips in 37.77 seconds. `pip check` found no broken dependencies, and the frozen evaluation package check passed.

## Rehearsal and provenance

The solo owner's approved authentication lab was reset and rebuilt using the existing private lab implementation. Its internal network had only the authentication client and target, with no published host ports. Three bounded failed logins were captured with matching trusted metadata; the disposable lab was removed afterward. Raw logs and metadata remain private. The [safe measured record](evidence/day62/rehearsal.json) records the run ID, hashes, source revision and exact stage times.

The timed replay follows the Day 61 recorded-attack application sequence: parse/normalize the approved capture, start a clean PostgreSQL database/API, ingest and process evidence with both frozen detectors, inspect Chromium dashboard evidence, request live grounded explanations with source references, and inspect the frozen evaluation view. Browser assertions check event linkage, detector readback and unchanged predictions after explanation. Synthetic web and network examples complement the private authentication replay.

The separate fallback uses a new SQLite database, synthetic evidence and disabled Ollama. A real 503 preserves stored predictions and the deterministic preview. The generated screenshot/trace identify the same three events; committed offline backup checksums are also verified. This is evidence replay rather than a new live attack during the presentation.

Timing excludes dependency installation, the earlier lab capture and human spoken narration. The lab capture duration is recorded separately from trusted metadata. These measurements establish technical demo execution time; they do not measure the owner's spoken defense. Gemma inference and model loading are the most variable steps. Pre-cache weights and retain the Day 61 fallback choices.

| Measured stage | Seconds |
| --- | ---: |
| Evidence validation/normalization | 0.230 |
| Clean PostgreSQL and API startup | 13.766 |
| Browser evidence, live RAG and evaluation | 32.240 |
| Normal path including database shutdown | 47.570 |
| SQLite/outage/offline fallback | 12.525 |
| Combined rehearsal including cleanup | 60.454 |

The earlier lab capture interval was 3.550 seconds; this is not the lab rebuild time. For repeat verification, follow the Day 53 runbook from a clean clone, run `python -m pytest -q` and `python scripts/package_day56_evaluation.py --check`, then `npm ci`, `npm run build`, `npm run api:check` and `npx playwright install chromium` in `frontend`. With the clean API running and `API_SMOKE_URL` set, the timed normal browser selection is `npx playwright test --grep "learner sees|every displayed evaluation metric"`. Set `CAPSTONE_TEST_LIVE_RAG=1` for real local generation; provide approved private capture references through the existing runbook environment variables only when available. For fallback, restart on a new SQLite database with `CAPSTONE_OLLAMA_ENABLED=0`, unset live-generation/private-capture variables, set `CAPSTONE_DEMO_BACKUP=1`, and run the `learner sees` selection. The default public synthetic path needs no private archive. Reset only the disposable database/lab project.

Two local measurement-helper issues were isolated from project code: a bare child interpreter initially selected the base Python, and Windows held a temporary synthetic SQLite file during cleanup. The helper used the active interpreter explicitly and allowed deferred temporary-file cleanup. Neither issue changed the application, private evidence or frozen predictions. No software defect requiring an application regression test was found.

## Release boundary

Use the [submission checklist](day62-submission-checklist.md) with the [Day 61 presentation notes](day61-defense-demo.md). Required hosted application/Chromium, PostgreSQL and real retrieval verification must pass before this documentation PR merges. Hosted explanations use controlled responses; the live Gemma replay above is local. Preserve the known evaluation errors, separate Day 52 false positive, timeout/cancellation limitation, unmeasured heavy concurrency/GPU pressure and limited secret-scan coverage. Day 63 final packaging/submission remains pending; no final release tag is created here.
