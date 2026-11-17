# Day 49 brute-force trace

The browser regression starts with raw SSH log text and trusted metadata. It normalizes the capture, submits it to FastAPI, processes the run, and compares both stored predictions with the result of processing. The browser checks recent events, opens the matching detection, verifies the event IDs and log reference, and checks the grounded explanation and its citations. The stored predictions are read again after the explanation and must match the earlier reads.

GitHub-hosted CI uses a synthetic raw log and a controlled RAG browser response. The existing retrieval job checks the saved FAISS index through the API, and the PostgreSQL job checks database behavior. For local replay with live FAISS and Ollama, start the application against a disposable database and set `CAPSTONE_TEST_LIVE_RAG=1`. The targeted test is `npx playwright test browser/rag.spec.mjs --grep "learner sees"` from the frontend folder. To replay already-approved evidence, point `CAPSTONE_AUTH_LOG` and `CAPSTONE_AUTH_METADATA` at the existing private files and set `CAPSTONE_AUTH_LOG_SHA256` and `CAPSTONE_AUTH_METADATA_SHA256` to their approved digests. The test checks the digests during ingestion preparation. Keep private inputs and test output local.

## Reusable integration checklist

| Stage | Check |
| --- | --- |
| Evidence | Record the source, trusted label, collection window and hashes for one run. Keep raw files in the private archive. |
| Parsing and ingestion | Match the metadata run ID, event count, timestamps, and declared log reference. |
| Features and detection | Compare observed features to the normalized events. Check the frozen rule threshold and the separate frozen ML output. |
| Persistence and API | Read back both predictions and confirm the run and event IDs agree with the processing response. |
| Dashboard | Find the same run in recent events and choose the saved prediction. Confirm the UI shows its event IDs, log reference, and both detector outputs. |
| RAG | Compare the explanation with stored facts and verify the scenario citations. Re-read both predictions and confirm they are unchanged. |
| Acceptance | Record the evidence source, what passed, and any gaps. Use fresh approved evidence when the roadmap requires it. |

## Local replay result

The previously approved capture from the [Day 38 backend integration record](day38-integration.md) passed the local browser replay with live FAISS and Ollama. The parser produced three linked failed-password events for the same run. The rule counted three failures at its threshold of three. The saved rule and ML predictions matched the processing output, and the dashboard showed the corresponding run, event identifiers, and log reference. The grounded answer matched the rule threshold and cited the approved brute-force material. Both saved predictions remained identical after the explanation.

The fresh Day 49 capture acceptance item remains open. This validation used historical approved evidence and a disposable local SQLite database.
