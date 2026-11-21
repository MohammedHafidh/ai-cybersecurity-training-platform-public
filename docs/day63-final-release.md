# Final capstone release — Day 63

## Release identity and acceptance

The final release is `v1.0.0`. Its exact source commit and tree, archive SHA-256, per-file hashes and frozen-artifact hashes are recorded in the downloadable `manifest.json`. The release tag must resolve to that same commit. `SHA256SUMS` covers the source ZIP and manifest without a circular self-hash. The source archive contains this guide, the setup instructions, configuration examples, dependency locks, source, tests, evaluation package, safe artifacts and demo notes.

The final release job runs only for the Day 63 closeout merge and only after GitHub-hosted `verify`, `postgres` and `retrieval` succeed for that exact merged commit. It checks the preserved RC1 tag, creates an annotated final tag without overwriting an existing tag, and publishes the three submission files. The [workflow](../.github/workflows/verify.yml) is the authoritative final verification record. A failed required job blocks publication. Release assets and their manifest record the resulting commit; the documentation does not guess its future SHA.

Download the explicitly verified [submission archive and checksums](https://github.com/MohammedHafidh/ai-cybersecurity-training-platform-public/releases/tag/v1.0.0). GitHub's automatically generated source archives are separate downloads; their compressed-byte hashes are not the checksum of `capstone-v1.0.0-source.zip`.

```text
python scripts/package_final_release.py --output build/final-release
# Linux: from build/final-release
sha256sum --check SHA256SUMS
# PowerShell: compare with SHA256SUMS
Get-FileHash capstone-v1.0.0-source.zip -Algorithm SHA256
Get-FileHash manifest.json -Algorithm SHA256
```

Run packaging from the clean verified Git checkout. Packaging reads committed blobs with `git archive`, checks every member's SHA-256 against Git, verifies ZIP CRCs, and confirms required deliverables. It does not copy ignored files, the Git credential store, virtual environments, model caches, private logs or local databases. The archive itself has no `.git`; after extracting it, use the manifest and documented setup rather than attempting to regenerate a Git archive there. Keep the source ZIP, manifest and checksums together.

## Final owner checklist

| Item | Verification and release condition |
| --- | --- |
| Source | Fresh public checkout from completed Day 62; clean tree before closeout edits. Final manifest pins the release commit. |
| Blockers/access | No open repository issue or PR at the initial closeout check. Required local links and public source access reviewed; required CI failures remain blockers. |
| Documentation | [Technical guide](final-technical-guide.md), [architecture](architecture.md), [setup/demo runbook](day53-demo-rehearsal.md), [submission inventory](day62-submission-checklist.md), [presentation and fallback notes](day61-defense-demo.md). |
| Evaluation | RC1 and frozen rule/ML artifacts unchanged; held-out tables/provenance remain reproducible. Ground truth stays separate from predictions. |
| Tests | Full local regression in the documented retrieval-capable environment; hosted application/Chromium, clean PostgreSQL reset and real retrieval checks required on the final commit. |
| Package | Expected tracked source only, ZIP readability/CRC, exact member hashes, required artifacts and reproducible checksums checked before publication. |
| Lab | Existing disposable authentication containers and their isolated network removed at final closeout. Private evidence, lab source and cached images retained; no new attack run required. |
| Demo machine | Documented Python/Node environment, Docker, local Gemma and pinned embedding cache available; Day 61 notes and Day 62 measured replay retained. Start the disposable database/API/frontend with the existing runbook; the machine is intentionally left with lab services stopped. |
| Backups | Committed synthetic screenshot/trace and their hashes verified. SQLite and unavailable-Ollama fallbacks remain documented and tested. |
| Privacy | Public tracked-tree review plus common credential-pattern checks; no private evidence folder, actual `.env`, local database, key file or dependency directory packaged. Pattern scanning cannot prove absence of every secret. |
| Release | Publish `v1.0.0` only after exact-commit checks pass. Preserve `rc1` at `bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa`. |

The solo project owner is responsible for implementation, evidence review and final validation. No teammate approval is required. This is technical release/submission readiness, not a claim that an institution has received or accepted an upload. Upload the verified files through the institution's required channel when applicable.

## Scope and remaining limitations

The completed pipeline covers controlled brute force, SQL injection, reconnaissance and benign cases, through normalization/features, rules/ML, PostgreSQL/FastAPI, dashboard evidence and cited local RAG explanations. The LLM is the explanation layer only. The [Day 62 record](day62-final-rehearsal.md) measured the normal technical replay at 47.570 seconds and the combined fallback/cleanup rehearsal at 60.454 seconds; installation, prior lab execution and spoken delivery were excluded.

The twelve-run reserved evaluation still contains rules FP 5/FN 2 and ML FP 1/FN 2. The separate Day 52 benign web false positive remains visible. These are experimental detector limitations, not hidden release blockers. Local/browser timeouts can leave Ollama computation running. Heavy concurrency, GPU memory pressure and production generalization are unmeasured. First setup requires network downloads, disk space and the explicitly documented local services. Credential-pattern review has limited coverage. Private original captures intentionally are not reproducible from the public archive alone; synthetic application replay and safe provenance are provided.

No new feature work, detector retuning or final evaluation changes belong to closeout. Preserve the verified release and its evidence.
