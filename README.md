# AI-Assisted Cybersecurity Training Platform

This public snapshot demonstrates defensive security log analysis across
authentication, web, and network scenarios. It contains the FastAPI backend,
React frontend, PostgreSQL schema, feature processing, rule detectors,
and the frozen Logistic Regression pipeline.

The project helps a student trace a controlled lab observation from raw logs to
detector evidence and a grounded explanation. It evaluates brute force, SQL
injection, and network reconnaissance alongside benign comparison traffic.

The verified technical baseline is [rc1](https://github.com/MohammedHafidh/ai-cybersecurity-training-platform-public/tree/rc1),
commit `bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa`.
Start with the [final technical guide](docs/final-technical-guide.md),
[architecture](docs/architecture.md), [lab reference](docs/final-lab-reference.md),
and [evidence index](docs/evidence/day60/README.md).

The [solo defense/demo notes](docs/day61-defense-demo.md) give the short presentation sequence and failure fallbacks.

The [clean-checkout rehearsal](docs/day62-final-rehearsal.md) and [submission checklist](docs/day62-submission-checklist.md) record final reproducibility and packaging readiness.

For a disposable database and rehearsed replay sequence, see the [demo runbook](docs/day53-demo-rehearsal.md).

## Run locally

Use Python 3.12, Node.js 22, and Docker Compose. From the repository root,
create and activate a virtual environment, then follow the [demo runbook](docs/day53-demo-rehearsal.md)
to start PostgreSQL, initialize the schema, and run the API.

```text
python -m venv .venv
# PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt -r requirements/day27.txt
python -m pytest -q
```

From `frontend`, use `npm ci` and `npm run dev -- --strictPort`.
The API needs the database setup above to serve event and detection views.

See the [training explanation guide](docs/day48-frontend-rag.md) for local Ollama setup, citation display, and the Day 48 feature freeze.
The API liveness check is available at `http://127.0.0.1:8000/health`.
The database readiness endpoint requires a configured database and installed
schema. The legacy comparison endpoints still require their own model configuration.

## Public verification

| Milestone | Public CI coverage |
| --- | --- |
| Day 30 | Repeat the four fixed development fits, check table hashes and split membership, and reproduce comparison metrics and selection |
| Day 31 | Load the checksummed frozen model and exercise inference on development observations |
| Day 32 | Recompute metrics from published confusion matrices and cross-check scenario totals |
| Day 33 | Run core schema, readiness, insert/read, and foreign-key checks on PostgreSQL 16 |
| Days 49–59 | Trace raw-log fixtures through the UI, verify benign comparisons, API contracts, RAG failure behavior, clean reset, backup artifacts and reproducible source packaging |

The [final evaluation package](docs/day56-final-evaluation.md) presents the frozen
twelve-run held-out results and errors. The [issue triage](docs/day59-release-candidate.md)
records the known detector, resource and verification limitations. This is a solo
project, with implementation, validation and evidence review performed under the
project owner's responsibility.

The public copy omits raw evidence archives, sealed test inputs, run-level
holdout traces, live attack tooling, and old CI artifacts. It reproduces the
development fits from the checked-in feature tables. Historical
documentation may refer to private artifacts. Public verification checks the
released model and saved results within these limits. The public snapshot
does not rebuild the raw corpus or rescore the held-out evidence.
