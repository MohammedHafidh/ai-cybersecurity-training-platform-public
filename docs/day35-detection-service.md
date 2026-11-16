# Day 35 combined detection service

Instantiate `DetectionService` with a trusted checkout's
`data/releases/capstone-ml-v1` bundle. Reuse that instance to call
`detect(session, run_id)` for runs stored by Day 34. The bundle loader checks
the model version, checksum, and installed dependencies before inference.

The service reconstructs the normalized observations from PostgreSQL and uses
the same feature builders as development and held-out evaluation. Authentication
and network observations use fixed 60-second UTC windows. Web observations use
the complete run. Each detector's run label is malicious if any of its
observations is malicious.

The response separates the stored ground truth, observed features and event
references, rule prediction and threshold evidence, and ML prediction and score.
Only the designated observable fields go into either detector. The service
reads the stored run and does not persist detection results.

An unknown run raises `RunNotFound`. Missing observations, invalid stored
evidence, and missing or invalid model bundles produce `DetectionServiceError`.
Database errors propagate to the caller.

Known-run tests compare all 24 published development runs with the frozen rule
evidence and model decisions. Integration tests use synthetic examples for all
three sources. Independent teammate review was unavailable. The service does
not require the private held-out inputs.
