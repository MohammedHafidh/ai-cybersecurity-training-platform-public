# Official Day 21 — Grouped Split Manifests

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Completion addendum: the previously open independent-evidence gate is now resolved
by the separate prospective reservation described in day21-final-test-protocol.md
and data/reserved-final-test-v1/reservation-lock.json. Existing experimental split
files remain unchanged. Their test.json is historical exploration, not the final
test. The approved final evidence is the sealed 12-run archive; verify integrity
using scripts/verify_reserved_final.py and reserve performance evaluation for Day 32.

Rebuild: `python scripts/build_day21_splits.py OUTPUT_DIRECTORY` from repo root.
Day 20 source checksums are verified first. Seed 42, sorted source/label strata,
then deterministic shuffling assign three train, one validation and one test run per
stratum: 18/6/6 runs. Every row/window from a run inherits one assignment. Each
manifest lists row IDs and event IDs. Input feature values never affect membership.
Label stratification is solely for coverage; no model or threshold is fitted.

Reject duplicate row/event provenance, inconsistent run context, source mismatch
and incomplete coverage. Tests check conservation of all 31 rows and 90 events,
all six source/label strata in each split, input-order stability and invariance to
feature values. CI regenerates manifests byte-for-byte.

## Independence gate and temporary freeze

These are reproducible run-disjoint experimental splits. They are NOT an untouched
final benchmark. All raw-corpus-v0.1 templates were explored in earlier experiments;
similar SQL/auth/network templates can cross partitions despite distinct run IDs.
The split report explicitly records unseen_scenario_families=false and
untouched_final_benchmark=false. No independent teammate validation is claimed.

Freeze the committed memberships and input checksums for exploratory work. Do not
change labels/features or reshuffle test membership to improve performance. A new
corpus version and separate reservation protocol are required for an independent
final benchmark; never silently promote these test runs to that role.

At the first split commit, the official independence gate remained open. The
completion addendum above closes it with new prospective evidence; the old test
partition does not gain independence retroactively. No Day 22 EDA or model training
is included. Dataset v1 packaging must preserve this development/reserved boundary.
