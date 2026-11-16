# AI-Assisted Cybersecurity Training Platform

This public snapshot demonstrates defensive security log analysis across
authentication, web, and network scenarios. It contains the FastAPI backend,
React frontend, PostgreSQL schema, feature processing, rule detectors,
and the frozen Logistic Regression pipeline.

See [architecture](docs/architecture.md) and
[PostgreSQL setup](docs/day33-postgresql.md).

## Run locally

Use Python 3.12 and Node.js 22. From the repository root:

```text
python -m pip install -r backend/requirements.txt -r requirements/day27.txt
python -m pytest -q
python -m uvicorn app.main:app --app-dir backend
```

In a second terminal, run `npm install` and `npm run dev` from `frontend`.
The API liveness check is available at `http://127.0.0.1:8000/health`.
The database readiness endpoint requires a configured database and installed
schema. The legacy comparison endpoints still require their own model configuration.

## Public verification

| Milestone | Public CI coverage |
| --- | --- |
| Day 30 | Recheck the selection ranking and match saved development decisions |
| Day 31 | Load the checksummed frozen model and exercise inference on development observations |
| Day 32 | Recompute metrics from published confusion matrices and cross-check scenario totals |
| Day 33 | Run core schema, readiness, insert/read, and foreign-key checks on PostgreSQL 16 |

The public copy omits raw evidence archives, sealed test inputs, run-level
holdout traces, live attack tooling, and old CI artifacts. It does not retrain
from the full archived dataset or rescore the held-out evidence. Historical
documentation may refer to private artifacts. Public verification checks the
released model and saved results within these limits.
