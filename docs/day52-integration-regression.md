# Day 52 integration regression

The existing raw-log browser smoke test covers brute force, SQL injection and reconnaissance. It verifies event linkage, persisted rule and ML results, dashboard evidence and scenario citations. Day 52 adds benign regression cases and checks the normalized event, database, and API boundaries with the same frozen detectors.

| Benign fixture | Frozen rule | Frozen ML | Review |
| --- | --- | --- | --- |
| SSH failure followed by success | Benign | Benign | The single failed retry stays below the rule threshold. |
| Web request with the ordinary phrase “select a category” | Malicious | Malicious | Both detectors falsely alert on this fixture. The trusted expected label stays benign, and Chromium shows it separately from both predictions. |
| Repeated connections to one destination port | Benign | Benign | Repetition does not meet the distinct-port threshold. |

The fixtures are synthetic normalized examples. The verified real attack captures remain documented in Days 49–51. No private captures enter hosted CI.

The contract audit checks run and event identity, timestamp, source family, source and target meaning, log reference, nullable event linkage, prediction values, and separation of trusted metadata from evidence fields. PostgreSQL runs the same regression as SQLite. The generated OpenAPI TypeScript check and Chromium test cover the frontend boundary. No schema migration or detector changes were needed. The observed false alert remains a limitation of the frozen detectors.
