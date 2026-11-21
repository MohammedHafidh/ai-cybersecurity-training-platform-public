# Day 61 solo defense and demo

Use the verified `rc1` technical baseline at `bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa` with the [final technical guide](final-technical-guide.md). The project owner presents all sections. Plan for roughly seven minutes of explanation plus questions; this is a presentation budget, not a measured end-to-end setup time.

## Prepare before the defense

Follow the [database/API startup runbook](day53-demo-rehearsal.md) and [local RAG setup](final-technical-guide.md). Use a fresh disposable demo database and pre-load Ollama and the pinned embedding model. Keep the [evidence index](evidence/day60/README.md), [metric tables](../data/processed/day56/tables.md), and [fallback screenshot and trace](evidence/day60/fallback-trace.json) available offline.

The selected recorded attack is the RC1 authentication rehearsal, run `day59-auth-20261120T123332Z`. Its three failed attempts were generated in the isolated private lab and the project was cleaned up. The evidence index preserves its hashes and [rehearsal provenance](day59-release-candidate.md). When presenting that capture, say explicitly that the attack was recorded earlier and the application replay is live.

For pre-staging the existing raw-capture browser replay, start the API at port 8000 with explanations enabled. In the frontend terminal, set `VITE_API_BASE_URL=http://127.0.0.1:8000`, run `npm ci` and `npm run build`, then set:

- `API_SMOKE_URL=http://127.0.0.1:8000`
- `CAPSTONE_TEST_LIVE_RAG=1`
- `CAPSTONE_AUTH_LOG` and `CAPSTONE_AUTH_METADATA` to the selected existing private files
- `CAPSTONE_AUTH_LOG_SHA256=7cbaafa154a7ba2c06ba83ac827338a4816c3f186225253e48d73a68e8de553f`
- `CAPSTONE_AUTH_METADATA_SHA256=9bdd1bc77473a33d5030afa105880a70ee771ec26ad88a0ae71ad2f0f0eb24bd`

Use PowerShell `$env:NAME='value'` or Bash `export NAME='value'`. Keep port 5173 free while running `npx playwright test browser/rag.spec.mjs --grep "learner sees"`. This existing acceptance trace ingests the approved authentication capture, processes it, and checks the full UI/RAG path. It also runs synthetic web and network comparisons. After it exits, run `npm run dev -- --strictPort` to inspect the retained database records manually. Stop any existing dashboard process before changing between preview automation and the development server.

For the synthetic backup, clear private capture variables, then run `python scripts/demo_replay.py` from the root and identify the printed run as synthetic. Avoid ingesting the same private run twice into one database. Reset the disposable project before replaying an identical evidence run.

## Final demo sequence and short speaking notes

| Step | Show | Say |
| --- | --- | --- |
| 1. Controlled attack | The private lab topology and the approved rehearsal record | “This isolated lab generated three bounded failed SSH attempts. The attack ran earlier; I am replaying its evidence through the application now.” |
| 2. Real logs | Locally inspected, redacted failure lines and matching metadata/hash reference | “The original log is private. These references identify the captured events and trusted collection context.” |
| 3. Normalization and features | Run ID, event IDs, three failures, 60-second rule window in detection detail | “The parser links events to this run. The metadata supplies the expected label before either detector runs.” |
| 4. Rule detection | Rule panel with observed three and threshold three | “The transparent rule fires because three failures meet the threshold in this window.” |
| 5. ML prediction | Separate ML panel and malicious-class probability | “The frozen Logistic Regression pipeline independently predicts malicious. The score describes this model output.” |
| 6. Persistence/API | Read the saved detail in `/docs`; point to the same run and event IDs | “PostgreSQL stores the run, observations and both predictions. The API reads the saved results.” |
| 7. Dashboard evidence | Recent events, expected label, source/target and event/log references | “These identifiers connect the displayed result back to the observation. Other cases can disagree with the expected label.” |
| 8. Grounded explanation | Choose the stored rule, ask why suspicious, open a trusted citation | “The explanation uses stored facts and retrieved approved notes. It explains the result and cannot update the detector records.” |
| 9. Evaluation | Overall and scenario tables, then the benign web false-alert case | “On twelve reserved lab runs, ML accuracy was 75% and rules accuracy was 41.7%. Both missed two malicious runs. The benign web regression also flags incorrectly. These results do not establish production performance.” |

Keep original raw captures and endpoint details off the public screen. Use the existing safe screenshot for an unredacted public backup. A private raw-log excerpt should be reviewed and redacted locally before projecting it.

## Concise presentation outline

| Section | Speaking cue |
| --- | --- |
| Problem and objective | Students need an evidence trail from security observations to an alert and explanation. |
| Scope and safe lab | Three scenarios, benign comparisons, internal Docker network, controlled metadata and private original logs. |
| Architecture/backend | Trace raw logs through normalization, features, detector records, PostgreSQL, FastAPI and React. Use the [architecture diagram](architecture.md). |
| Rules and ML | Explain observable feature inputs, run-disjoint development data, frozen selection and independent predictions. |
| Local LLM/RAG | Explain six approved chunks, the saved FAISS index, model-selected fact/passage IDs and cited output. |
| Demo and results | Follow the sequence above, then compare the frozen confusion matrices and scenario errors. |
| Limitations and conclusion | State the small lab population, false alerts/misses, local resource assumptions and verified fallback paths. |

## Fallback decisions and speaking cues

| Failure | Action and wording |
| --- | --- |
| Live lab cannot run | Replay the approved earlier private capture, or use the synthetic demo command. “This is a recorded-evidence replay” or “This is the synthetic application fallback,” as appropriate. |
| Ollama, FAISS or model cache unavailable | Show the saved rule/ML outputs and deterministic preview. “Grounded generation is unavailable; the stored detector evidence is still readable.” |
| PostgreSQL unavailable | Start with an unused SQLite demo file using the [fallback guide](day55-integration-fallbacks.md), initialize the schema, and replay the synthetic example. Identify SQLite on screen. |
| Docker unavailable | Use SQLite if the local API can run. Otherwise use the committed screenshot and trace. |
| Browser automation fails | Open the dashboard and `/docs` manually if the API is healthy. If replay has not populated data, use the existing synthetic replay command. |
| Frontend or API cannot start | Open the [offline screenshot](evidence/day60/fallback-evidence.png), its matching trace and frozen tables. “These are saved verification artifacts, not a current live result.” |

The fallback screenshot shows the same synthetic run ID as its JSON trace and a real recorded explanation-service 503. No teammate handoff is needed. Move from the owner's lab/evidence section to the application section using the same run ID. Stop/reset only the selected disposable demo project when finished.

## Rehearsal record

The normal technical rehearsal replayed the approved RC1 authentication capture through a clean PostgreSQL 16 demo database, the production frontend in Chromium, and live FAISS/Gemma. The same existing browser trace also checked synthetic web and network examples. Run/event linkage, rule and ML readback, source citations and unchanged predictions passed. Both private authentication file hashes matched after rehearsal.

The fallback rehearsal used a new disposable SQLite database and synthetic fixtures with local explanations disabled. The real 503 left the saved detector outputs and deterministic preview visible. The generated screenshot and JSON were checked for the same synthetic run and three event IDs. The committed offline screenshot and trace passed their checksum/identity checks. The PostgreSQL demo project was cleaned up afterward. No new private capture was needed.

The frontend production build, documentation links and frozen evaluation check passed. These are technical rehearsals. The timed delivery, final clean-clone run and submission-content review belong to Day 62, followed by final release verification and archiving on Day 63.
