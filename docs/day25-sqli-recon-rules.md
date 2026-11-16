# Official Day 25 — SQLi and Reconnaissance Baselines

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

All three detectors now use a common dispatcher, detect_scenario_rows. Each accepts
only a validated observable input model; unknown fields, labels and trusted scenarios
are rejected. The shared result shape follows Day 24: detection/run/row IDs, rule
version, predicted label/scenario, trigger flag and numeric evidence with event IDs.
Network evidence includes group and 60-second UTC bounds. Web evidence explicitly
identifies run aggregation. Existing authentication behavior remains unchanged.

SQLi baseline web-sql-token-v1 triggers when suspicious_token_count >= 1. The existing
feature extractor recognizes case-insensitive SQL token patterns, not one exact
payload. It preserves the earlier token threshold as a high-sensitivity transparent
starting point. A token is an indicator, not proof. Benign words such as select can
trigger. Encoding and syntax outside the feature regex can evade. Missing/empty input
alone does not trigger. Do not add a status-code exemption that could hide failed
attacks merely to improve development scores.

Network baseline network-multiport-v1 triggers when unique_destination_port_count
>= 2 within a run/source/target 60-second window. This retains the earlier transparent
multi-port heuristic. Distinct ports must not exceed observed connections. Twenty
connections to one service remain below the rule threshold; legitimate multi-service
maintenance can trigger. Slow, distributed and single-port attacks can evade. The
target logs accepted connections only, so this rule does not claim full packet/SYN
or closed-port visibility. No exact scan-command matching is performed.

Threshold review: auth remains Day 24's three failed logins; web remains one token;
network remains two ports. No threshold changes or searches are introduced. Unit
challenges cover varied SQL syntax, normal/missing input, keyword false positives,
single-service bursts and legitimate multi-port behavior. Real frozen training and
validation runs supply development evidence for all three sources. Synthetic cases
are explicitly tests, not new corpus evidence or a replacement for real logs.

Rebuild from repo root:
`python scripts/build_day25_rules.py OUTPUT_DIRECTORY`.
Outputs under data/processed/day25 include observation decisions, run decisions and
development validation metrics. Run decisions use any triggered observation. Each
source has six train and two validation runs; overall 18 train and six validation.
Ground truth is joined only by the harness. Predictions never carry ground truth.
Confusion matrices use [benign, malicious] on both axes. Small-sample results and
errors remain visible; they are not final performance claims.
The saved validation report records one SQLi false positive on its benign
look-alike run. It is retained as an observed limitation rather than removed or
used to tune the threshold. Authentication and network each have only two
validation runs, so their perfect results are not broad reliability evidence.

Historical test.json and the reserved final-test archive are not read by this
harness. Dataset v1 remains immutable. CI regenerates outputs byte-for-byte and runs
the full test suite. Review is automated/agent review without fabricated teammate
sign-off. Day 26 must perform the planned rule-engine evaluation/error review and
freeze. No final-test evaluation occurs before Day 32.
