# Day 62 submission checklist

This is the solo owner's submission inventory. Day 63 final packaging is pending; this checklist does not claim the project has already been submitted.

| Area | Required contents and verified reference |
| --- | --- |
| Repository | Public source, tracked dependency files, GitHub-hosted verification, and the Day 62 PR/check results. Preserve the original private repository as the evidence archive. |
| Stable baseline | `rc1`, commit `bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa`; retain the [RC1 manifest](evidence/day60/rc1-manifest.json) and its original hashes. |
| Objective and architecture | [Final technical guide](final-technical-guide.md), [architecture](architecture.md), three mandatory scenarios and the complete evidence-to-explanation pipeline. |
| Setup | README, [demo runbook](day53-demo-rehearsal.md), Python 3.12/Node 22, disposable PostgreSQL, embedding-model cache and explicit Ollama prerequisites. See the [clean-checkout record](day62-final-rehearsal.md). |
| Frozen evaluation | [Day 56 package](day56-final-evaluation.md), committed aggregate tables/figures and frozen provenance. Ground truth remains separate from predictions. |
| Detector artifacts | Tracked frozen Logistic Regression pipeline, rule contracts and feature schema; no retuning for presentation. |
| RAG artifacts | Approved corpus, source references, saved FAISS index and pinned embedding revision. Ollama is an explanation service, never a detector. |
| Demo and presentation | [Day 61 sequence, seven-section outline and speaking notes](day61-defense-demo.md), measured technical replay, fallback instructions and offline screenshot/trace. |
| Known limitations | Small scripted population; rules FP 5/FN 2 and ML FP 1/FN 2 in the reserved evaluation; separate Day 52 benign web false positive; timeout/cancellation and unmeasured heavy concurrency/GPU pressure; limited credential-pattern scan coverage. |
| Privacy and safety | Private raw captures stay outside this repository. Only safe hashes, run references, aggregates and synthetic screenshots are public. Lab clients target only the approved isolated disposable network. |
| Required deliverables | Source and dependency files; setup/architecture guide; evaluation package; demo outline/notes; offline backup and checksums; provenance manifests; limitations and final verification record. |
| Verification | Local clean-checkout tests and measured replay recorded in Day 62; merge only after required hosted application, PostgreSQL and retrieval jobs pass. |

## Day 63 handover

Review the final submission contents and institution-specific upload format, prepare the final source/release archive and matching checksums at the final verified commit, check readability and access to the submitted links/files, and perform the final submission/release checklist with a time buffer. Retain RC1 separately. Do not invent a submission receipt or institutional approval. No new detector features or fresh private attack collection are needed for packaging.
