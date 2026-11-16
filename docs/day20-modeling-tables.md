# Official Day 20 — Modeling Tables and Data Dictionary

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Input is the verified, immutable raw corpus v0.1 archive. Rebuild from repo root:
`python scripts/build_day20_tables.py OUTPUT_DIRECTORY`. The output directory must
not exist. Committed reference outputs are under data/processed/day20; CI rebuilds
and compares every byte. The archive checksum and all raw provenance are verified
before table construction. No new lab collection is needed for this gate.

## Table units and types

Three scenario tables avoid filler columns or silently mixing run and window units.
Authentication and network rows group by run/source/target in fixed UTC 60-second
half-open windows. Web rows aggregate one run. Multiple rows from one run must remain
together in future splits. CSV and JSONL carry equivalent fields; CSV array fields
contain JSON arrays. Numeric features are nonnegative, booleans encode as 0/1 in a
future model pipeline. UTC window bounds are ISO strings. Each column's type,
role, meaning and encoding plan are in data-dictionary.json.

Only each table's explicit feature_columns whitelist may enter a model. run_id,
row_id, event_ids, raw_source_files, source_ip, target, windows, scenario and
attack_label are never predictors. Label encoding is benign=0, malicious=1,
derived from trusted metadata. Any scaler/encoder must be fitted on training data
only during the planned model phase. No transforms are fitted by Day 20.

## Missingness and coverage review

coverage-report.json distinguishes run counts from row counts: each scenario has
five benign and five malicious runs. Window counts may differ by class because
activity crosses fixed boundaries. This is not extra independent data. Required
feature values are complete. Missing web input remains observable through
missing_input_count; zero null feature cells does not imply no raw missing inputs.
All 90 normalized observations must appear in exactly one corresponding table row.
Each row retains event IDs and raw filenames for traceability.

The corpus covers all three attacks, normal activity, auth retries, web look-alikes
and network bursts. It is adequate for constructing these tables. No extra runs
are required for Day 20. Thirty scripted runs remain a small corpus; behavioral
similarity, only five runs per source/label and service-only network visibility limit
future conclusions. Day 21 must examine independent holdout families before freezing
splits. Do not silently treat historical Variant 05 as an untouched test set.

## Acceptance and ownership

Tests cover event conservation, complete run coverage, deterministic rebuilds,
label-feature separation, duplicate/context rejection, dictionary completeness and
output overwrite protection. CI verifies exact regeneration from frozen raw bytes.
Coverage review here is software/automated evidence; no independent teammate sign-off
is claimed. the project author retains human security review responsibility while working solo.

Day 20 does not create split manifests, EDA, Dataset v1 or retrain existing models.
Those remain official Days 21–23 and the later ML phase.
