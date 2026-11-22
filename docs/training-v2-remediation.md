# Training platform v2 remediation record

Baseline: `9787ec6a3d9c071e17a461add3c1ede41c77a6de`. Work remains on `remediation/training-platform-v2`; no final tag is authorized.

## Phase 1 — contracts and foundation

Three versioned structured lessons and twelve curated quiz questions define the learning content. Public lesson DTOs exclude marking answers. Start requests accept only scenario and explicitly labeled live/sample mode. Targets, ports, payloads, shell input, script paths and arbitrary variants are prohibited.

Learning route: Home → Guide → Controlled Exercise → Evidence Analysis → Ask AI → Quiz → Completion. The current detector and persistence engine is reused. Ground truth remains independent from predictions; detector errors never prevent learning completion.

Design tokens: dominant cream `#F3EEE3`, ink `#111111`, restrained orange `#D9541E`. Orange/cream contrast is insufficient for small normal text, so active indicators retain ink labels.

Safety policy: loopback-only operator service, same-origin local controls, startup-issued request token, strict Host/Origin checks, fixed private bundle hash manifest, structured subprocess arguments, one active exercise, dedicated owned Docker project, verified internal network/no published target ports, time/output limits and scoped cleanup. Live failure must never become silent replay. Private originals remain outside Git; only bounded, typed sanitized projections are returned.

Startup design: one Windows operator command prepares PostgreSQL/schema and serves the production frontend through loopback FastAPI. It performs readiness checks and never starts an attack. Stop is scoped to the recorded platform processes/project, preserves database data and private evidence, and remains distinct from an exercise cancellation. Manual fallback steps will be documented with implementation.

## Phase 2 — learning shell
Home and three guides use the cream/ink/orange design foundation. Existing evaluation is retained as a secondary page. Actual Chromium checks passed for Home, all three guides and a 375px mobile layout. The controlled-exercise button is intentionally disabled until a live runner exists. Frontend production build and seven contract/content tests passed.

## Phase 3 — safe live-runner vertical slice
Pinned private bundle hashes and approved image labels are verified before execution. Each exercise has a unique server ID, two containers on one internal network, no published target ports, bounded subprocesses and ownership-scoped cleanup. Fresh authentication collection reached existing normalization, frozen rules/ML and PostgreSQL; its private original files were retained outside Git. Twenty-two targeted tests passed, including unsafe topology and control-request rejection. Two additive training tables and the shared detector progress hooks are in place; detector algorithms and artifacts are unchanged. Quiz routes are prepared but the student quiz flow is not yet accepted.

## Phase 4 — three live browser exercise paths
Chromium started each approved scenario from Home and Guide, then automatically entered Analysis using actual backend stages. New captures contained 3 authentication failures, 1 web request and 2 target connections. Existing parsers/features/rules/ML and PostgreSQL were used. Sanitized log projections, normalized fields, feature explanations and independent outputs were displayed. A Windows CRLF script execution defect was fixed by using the same manifest-verified script bytes normalized to LF for all three clients. Failed attempts were not replayed or relabeled. The guide/activity boundary and known detector limitations remain explicit.

## Phase 5 — bounded natural-language AI and teaching retrieval
The new exercise-scoped question endpoint uses stored detector facts and sanitized evidence, with a separate 21-chunk teaching corpus and local FAISS cache. Original v1 knowledge/index files are untouched. Known duplicate IDs are safely deduplicated; unknown IDs and malformed selections never become claims. All three browser checks returned live local grounded selections with citations after Ollama startup. A separate stopped-Ollama check showed explicitly labeled deterministic fallbacks. Unrelated questions were rejected and saved detector outputs were unchanged. Twenty-three targeted content/safety/AI tests passed.

## Phase 6 — deterministic quizzes and completion
Each scenario has four curated questions. The browser submits answers for server-side deterministic grading; score, pass/fail and attempt time persist in the additive quiz table. A failed attempt cannot complete a scenario; 3/4 passes and retry is allowed. All three browser paths passed scoring, feedback, completion and Home completion-state checks. Twenty-four targeted training tests passed. No accounts or model-based grading were added.

## Phase 7 — startup, recovery, regression and acceptance

The Windows setup/start/stop entrypoints provision the existing stack, serve one same-origin production application and preserve private data. Start/stop/restart were exercised using the documented existing-environment option. A new PostgreSQL advisory lock prevents competing training workers; interrupted owned jobs are recovered explicitly. Recovery tests cover failed/interrupted work without silently substituting samples. The full one-time installer was inspected and its scripts parsed, but a completely new Python environment installation was not repeated locally.

Local verification passed: 239 backend tests; 8 API-client checks on a clean PostgreSQL fixture; 10 existing/read-only browser checks; 4 dedicated sample checks; and 4 dedicated live checks. Build, generated API contract, responsive guides and keyboard activation also passed. Dedicated modes are deliberately skipped during the ordinary browser suite and executed separately, rather than claiming a hosted private lab.

The final real browser acceptance started fresh approved Docker exercises for all three scenarios, captured 3 authentication events / 1 SQLi event / 2 reconnaissance connections, processed them with the unchanged engine and persisted them in PostgreSQL. Each journey reached evidence, normalized fields, features, independent predictions, a live local grounded answer with citations, deterministic 4/4 grading, explicit completion and Home progress. Stored detector records stayed identical after explanation. Owned exercise resources were removed. The three timed automated journeys took 80.344 seconds in total; this is not a human presentation timing.

See [safe machine-readable acceptance](evidence/training-v2/acceptance.json), [operator instructions](training-platform-setup.md), and [implementation report](training-v2-implementation-report.md). Hosted verification is required on the final PR; its result is recorded by GitHub rather than inferred from local success. No final release tag is created.
