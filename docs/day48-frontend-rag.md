# Day 48 training explanations

Open **Detection evidence**, select a stored prediction, and use **Grounded explanation**. Choose a training question, then select **Get explanation**. The panel loads on request from the Day 47 RAG endpoint. The stored rule and ML outputs, event references, and deterministic rule summary remain visible even when local inference is unavailable.

The panel shows the answer and trusted passages separately. Each passage displays its section and references to the project documentation or the cited MITRE or OWASP page. Loading, retry, empty responses and unsupported questions have distinct messages. The interface offers three fixed questions. For example, asking why a stored ML prediction was suspicious is unsupported when it lacks a rule comparison.

Set up the [local Ollama model](day44-local-explanations.md) and the [retrieval dependencies](day46-retrieval.md) in the FastAPI environment, then enable explanations with `CAPSTONE_OLLAMA_ENABLED=1`. Cold starts depend on local resources. The frontend waits up to 50 seconds. The corpus contains six English lab-specific passages, and the explanations do not establish real-world compromise or generalization.

## Solo scenario review

The browser review uses controlled normalized fixtures with the real FastAPI detector outputs. The live acceptance path uses the frozen FAISS index and local Gemma 3 1B. Hosted Chromium covers the same interface with controlled RAG responses and tests unsupported behavior against the live API. The hosted backend retrieval job verifies the saved index integration.

| Scenario | Evidence and citation checked |
| --- | --- |
| Brute force | Three failed SSH password events met the threshold of three. The MITRE reference explains online guessing. The count does not establish successful access. |
| SQL injection | One SQL-like token match met the threshold of one. The OWASP references give context for query manipulation and prevention. The synthetic token match does not establish a successful injection. |
| Network reconnaissance | Two distinct observed destination ports met the threshold of two. The MITRE reference provides service discovery context. The observation covers logged connections only. |

## Feature freeze

Day 48 closes feature development for the capstone. Remaining work is limited to integration, testing, evaluation, documentation and bug fixes. The AI scope is limited to explaining saved detections using the approved corpus. Rule and ML detectors remain responsible for detection.
