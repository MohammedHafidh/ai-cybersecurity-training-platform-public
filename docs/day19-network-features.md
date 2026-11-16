# Official Day 19 — Reconnaissance Features

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Roadmap: October 22, 2026, reconnaissance feature engineering. Historical day
numbers in older commits do not certify the corresponding official plan milestones.

## Contract

`app.processing.network_features.build_network_windows` consumes normalized network
events plus validated run metadata. Each row groups by run ID, canonical source IP,
metadata target and protocol within a fixed UTC window. Default: 60 seconds,
aligned to Unix epoch; intervals are half-open [start, end). A boundary event belongs
to the next window. Empty windows are omitted. Partial windows still use the full
configured duration for rate calculation. This is a connection density, not an
estimate of traffic during unobserved time. Window size is a fixed configuration,
never selected using labels. Targets come from metadata because current logs do
not record destination IP; each run must have one declared target.

Fields: connection_count (integer observed service connections),
unique_destination_port_count (integer distinct observed ports),
connections_per_second (count/window seconds), observed_span_seconds (last minus
first observation, zero for a singleton). UTC bounds and group keys identify the
row. Sorted event IDs and raw filenames preserve provenance. Labels are not numeric
features and do not determine any count. The existing run-level feature/API/model
contract remains available unchanged; this separate window table is the official
Day 19 output for later Day 20 integration, not a silently substituted ML input.

## Quality and evidence

Reject missing metadata, invalid/excluded runs, missing source/port/protocol,
naive event timestamps, inconsistent labels, undeclared raw files, duplicate event
IDs and observations outside run boundaries. Distinct IDs with identical timestamp
and fields remain distinct connections; heuristic deduplication could lose real
bursts. Inputs are never edited. Normalization filters startup/readiness traffic
using the recorded action interval; Day 19 collection never expands that interval
to include earlier health checks.

Run `PYTHONPATH=backend python scripts/verify_day19_network.py` on a Docker host.
It records a two-port scan, four legitimate health requests, and four health requests
plus one legitimate connection to the second service. All target names are fixed
inside the internal Docker network. Expected counts are 2, 4 and 5, respectively.
Raw logs, metadata, normalized events, window tables and a count reconciliation
report are uploaded by Day 19 CI. Per-window memberships are independently checked
against normalized observations, and raw counts are checked against executed actions.

## Interpretation and limitations

A high connection count can be a benign burst. Multiple observed ports can be
legitimate service checks. Neither feature proves malicious intent. The target logs
only connections accepted by its listening services: closed-port scan attempts,
SYN-only scans and packet-level rates are not measured. Fixed windows can split a
burst at a boundary; tests explicitly cover this behavior. No new rule thresholds
or ML tuning are part of Day 19. Validation is automated lab evidence; do not claim
teammate independently reviewed it. A human reviewer can reproduce the raw-count check
using the uploaded logs and recorded action counts.

## Carryover before Dataset v1

- Official Day 17: authentication grouped-window features, benign retries and a
  documented raw-count review.
- Official Day 18: SQLi encoded/missing-field handling, benign look-alikes and
  documented feature semantics/false-positive risks.
- Verify official Days 15–16 corpus freeze, exclusions, cleaning counts and policy.
- Official Days 20–23 remain modeling table, independent split manifests, quality
  report and Dataset v1 freeze. Preserve Days 24–32 rules and final ML evaluation.

Day 19 acceptance: unit tests pass, scan/burst/multi-port live evidence reconciles,
window semantics are verified and documented, CI passes. No Day 20 implementation.
