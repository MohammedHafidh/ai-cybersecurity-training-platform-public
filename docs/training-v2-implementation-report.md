# Training platform v2 implementation report

This remediation keeps the original project as the technical engine and adds the approved student learning workflow. Work is isolated to `remediation/training-platform-v2`; historical releases and evaluation artifacts remain unchanged. No new final release tag is authorized or created.

## Student experience

Home presents three scenarios with browser-local Not Started / In Progress / Completed states. Each guide includes definition, significance, objectives, safety, exercise overview, expected evidence, log concepts, feature explanations, rules/ML interpretation, limitations, mitigations and references. The student then starts an approved live exercise, follows real backend transitions into Evidence Analysis, compares truth and predictions, asks an evidence-scoped question, answers four curated questions and completes the scenario. Completion offers evidence/AI review, retry, Home and another scenario. Existing technical evidence and evaluation views remain available as secondary views.

The cream/ink/orange design uses responsive layouts, native links/buttons, visible focus, a skip link, labeled controls and live status/error announcements. Small orange step text was changed to ink with an orange marker for contrast. Displayed observation features identify their contributing record numbers. Sample mode excludes activity stages that it never executes.

## Reuse and architecture

Fresh private logs → existing parsers/normalization → existing feature extraction → frozen rules and scikit-learn pipeline → existing PostgreSQL detection records/API → student evidence view → separate trusted retrieval/local Ollama explanation. Ground truth comes from the approved collection protocol, independently of both predictions. The LLM never produces or changes a detector label. Frozen model, feature/rule logic, final evaluation, original RAG artifacts, `rc1` and `v1.0.0` are preserved.

## Main source changes

- `backend/app/training/content.py`, `contracts.py`: three versioned guides, twelve questions, strict request schemas and public lesson DTOs excluding marking keys.
- `lab.py`, `worker.py`, `evidence.py`: hash-allowlisted lab adapter, bounded fresh collection, actual stage history, existing engine invocation and sanitized educational projections.
- `storage.py`, `routes.py`: additive exercise/quiz persistence and local student APIs.
- `knowledge.py`, `explanations.py`: separate 21-chunk trusted teaching corpus, pinned local embeddings/FAISS, exercise-scoped free text, validated source selection and deterministic fallback.
- Existing detection service/routes: shared existing persistence entrypoint and optional progress callbacks; algorithms unchanged.
- Existing persistence runtime: training schema, exclusive PostgreSQL instance lock and interrupted-job recovery.
- Existing main application: training router and optional same-origin production frontend serving.
- `frontend/src/App.tsx`, `ExercisePage.tsx`, `AskAI.tsx`, `Quiz.tsx`, `training.ts`, `index.css`: learning navigation, live analysis, AI questions, quizzes and progress. Existing evidence/evaluation components are reused.
- `setup-platform.ps1`, `start-platform.ps1`, `stop-platform.ps1`, `scripts/platform_control.py`, `compose.training.yml`: operator preparation and owned service lifecycle.
- Training tests, browser acceptance, generated API schema, verification workflow and safe preview packaging extend the original regression checks.

## API and database additions

Read-only catalog: `GET /training/scenarios`, `GET /training/scenarios/{scenario}`. Local operational reads: `/training/session`, `/training/readiness`, `/training/active`. Exercise creation: `POST /training/exercises`; reads: `GET /training/exercises/{id}`. Controlled mutations append `/cancel`, `/question`, `/quiz-attempts`, `/complete`; operator cancellation uses `POST /training/cancel-all`.

`training_exercises` stores ID, scenario, mode, status, stage/history, safe result, failure, linked core run and completion. Its unique active slot limits execution to one exercise. `training_quiz_attempts` stores the submitted answers, content version, deterministic score, pass/fail and attempt time. Existing core runs/events/features/detections remain authoritative. No accounts, roles or cloud services are added.

## Safety and privacy

Students submit only an approved scenario and explicit live/sample choice. Targets, ports, variants, payloads, commands and paths are not request fields. The operator supplies a private bundle whose fourteen approved files are hash-checked. Approved images, exact two-container topology, internal network, ownership labels and absence of published target ports are verified before activity. Commands use structured arguments, bounded time/output and cancellation. Each server-generated ID owns its private capture and disposable Docker project. Cleanup only removes that owned project.

Controls require loopback Host/client, exact browser Origin, a startup token and JSON. The app is a local single-user capstone, not an internet-hosted multi-user service. A live failure remains visible and never becomes replay. Raw logs, run metadata, runtime configuration, diagnostics and generated indexes remain outside Git. Public acceptance contains only safe IDs, hashes, counts, stages and results. Archived private evidence is not rewritten.

## AI and assessment

Questions are bounded to 300 characters and the current scenario/evidence. Trusted lesson knowledge is retrieved through a separate runtime FAISS index. Ollama selects validated known passages; duplicated known IDs are deduplicated and invented/malformed sources fall back safely. The interface distinguishes local grounded selection, deterministic fallback and unsupported questions. Citations are visible. This is bounded extractive teaching, not unrestricted chat or causal model attribution.

Each scenario has four curated deterministic questions. Server grading stores every submitted attempt and explains the correct answers. At least 3/4 permits explicit completion; failed attempts can retry. Detector disagreement never prevents a student completing the lesson.

## Actual verification

| Check | Observed result |
|---|---|
| Backend suite | 239 passed |
| API client on clean PostgreSQL | 8 passed |
| Existing/read-only browser regression | 10 passed |
| Explicit sample browser acceptance | 4 passed |
| Explicit real private-lab browser acceptance | 4 passed |
| Build and generated OpenAPI contract | Passed |
| Responsive guides and keyboard activation | Passed |
| Operator stop/start with preserved data | Passed |

| Fresh browser journey | Real events | AI result | Quiz / completion |
|---|---:|---|---|
| Brute force | 3 | Local grounded selection with citation | 4/4, completed |
| SQL injection | 1 | Local grounded selection with citation | 4/4, completed |
| Reconnaissance | 2 | Local grounded selection with citation | 4/4, completed |

All three journeys clicked student controls, generated new private captures and automatically entered Analysis. Explanations left persisted detector outputs unchanged. Separate stopped-Ollama checks passed labeled fallbacks; unrelated questions were rejected. Hashes and actual stage timestamps are in [acceptance.json](evidence/training-v2/acceptance.json). Hosted CI runs explicitly synthetic sample journeys because the approved private bundle is intentionally absent from public runners.

## Remaining limitations

Frozen false positives/false negatives remain visible; this remediation does not improve or re-estimate final model accuracy. Browser progress is not authenticated identity or cross-browser synchronization. One exercise runs at a time. Live activity needs the operator-configured private bundle and Docker Linux engine; public-only users can use clearly labeled samples. Full fresh dependency installation was not repeated locally; the documented existing provisioned environment and operator lifecycle were tested. Local Ollama can be slow/unavailable, with labeled fallback; client cancellation may not stop already-running generation. Heavy concurrency, adversarial multi-user exposure and GPU pressure are outside this local capstone acceptance. Automated journey duration excludes human reading/narration. No raw private evidence or additional attack tools are published.
