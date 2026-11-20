# Day 59 Release Candidate 1

RC1 packages the checked-out commit as a reproducible Git archive with a manifest. The manifest records the commit, archive SHA-256 and hashes of the frozen model, evaluation, provenance, corpus and index. The hosted `release-candidate-1` artifact contains `rc1-source.zip` and `manifest.json`. Only tracked source files enter the archive. The manifest identifies the exact commit to use with the matching successful workflow run.

To reproduce the source package, check out that manifest's commit with Git and run `python scripts/package_rc1.py`. The output goes to `build/release-candidate/`. It is ignored by Git. The command rejects tracked changes, so the archive and the working tree agree. A candidate is verified only after the application, PostgreSQL and retrieval jobs all pass.

## Release checklist

- Run the complete backend, data and inference suite from a fresh checkout.
- Install frontend dependencies with `npm ci`, build, and verify the generated OpenAPI contract.
- Run Chromium across attack, benign, metric comparison, timeout and malformed-citation cases.
- Rehearse the clean PostgreSQL demo, reset, and second replay.
- Verify the synthetic fallback screenshot and trace refer to the same run.
- Confirm a selected approved capture still reaches the dashboard and grounded explanation locally.
- Rehearse the private lab reset and chosen demo scenario as the sole owner and record any blockers.
- Match the release manifest's commit to all successful hosted jobs before final acceptance.

## Final issue review

| Finding | Classification and final-submission disposition |
| --- | --- |
| Rule and ML false positives/negatives | Acceptable as disclosed experimental results. The twelve-run held-out report has rules FP=5/FN=2 and ML FP=1/FN=2. The separate benign web false alert remains visible. Broad detection accuracy claims would be unsupported. |
| Ollama continues after browser timeout | Acceptable for the bounded local demo with the documented retry and deterministic evidence fallback. Total inference cancellation is deferred. |
| Heavy concurrency and GPU memory pressure untested | Acceptable within the single-user local scope. No capacity or GPU performance claim is made. |
| Secret pattern scanning has limited coverage | Acceptable as a stated audit limit. Raw evidence remains private. The source review found no common credential patterns or tracked temporary files. This is not an assurance that every possible secret was detected. |
| Malformed retrieval/citation failures | Fixed in Days 57–58 with API and browser regression coverage. |

## Rehearsal and acceptance record

The local backend run passed 192 tests, with two retrieval cases skipped in the base environment. Hosted retrieval installs the required embedding dependencies. The frontend production build, generated API check and frozen metric-package check passed locally.

The private rehearsal used the existing three-attempt authentication variant in a dedicated Compose project with an internal network and no published service ports. The project was reset and rebuilt, generated three failed SSH events, saved the raw log and metadata privately, then removed its containers and network. Windows text-mode piping initially changed script line endings. Sending the existing script as UTF-8 bytes fixed the rehearsal command.

The fresh capture then passed the existing browser trace against a clean PostgreSQL 16 database with live FAISS and Gemma. The trace checked event and run linkage, both stored predictions, the dashboard and trusted citations, and confirmed that explanations left stored predictions identical. The raw log and metadata are identified by the safe hashes below.

| Private evidence reference | SHA-256 |
| --- | --- |
| RC1 authentication log | `7cbaafa154a7ba2c06ba83ac827338a4816c3f186225253e48d73a68e8de553f` |
| Matching metadata | `9bdd1bc77473a33d5030afa105880a70ee771ec26ad88a0ae71ad2f0f0eb24bd` |

The backup path remains the verified `day55-demo-fallback` screenshot and matching JSON trace. Hosted regression regenerates and publishes these synthetic artifacts and checks the SQLite, unavailable-LLM and reset paths. The release manifest and backup artifacts are available from the successful workflow for the candidate commit.

No unresolved critical or high software blocker was identified in this focused release review. Failed required checks remain a release blocker. After merge, the `rc1` tag is published only when the application, PostgreSQL and retrieval jobs succeed for the merged commit. Only blockers and serious defects may change the candidate after this phase.
