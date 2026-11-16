# Official Day 22 — EDA and Traceability Review

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Rebuild from repo root: `python scripts/build_day22_report.py OUTPUT_DIRECTORY`.
Read data/processed/day22/report.md for the concise report and the accompanying
JSON for complete counts, missingness, feature distributions and raw trace links.
CI regenerates outputs byte-for-byte. Existing labels, features and split membership
are never modified. No model or rule thresholds are fitted or selected.

Scope: training and validation (24 runs, 25 rows). The 30-run/31-row/90-event full
development corpus is inventoried, with the six older exploratory test runs counted
only in membership. The separate reserved final-test archive is never opened by
this report. All feature summaries use training/validation only.

Quality checks verify frozen raw hashes, Day 20 file hashes, split source hashes,
exact feature regeneration, event conservation and raw file/line provenance.
Representative rows are selected deterministically by row ID, never feature values:
one per source/label in each of training and validation (12 rows). Each contributing
event is traced to metadata and an original raw line/record hash.

Missing web fields remain observable counts rather than filled-in guesses. Service
connection logs cannot describe all closed-port scans; SQL-like benign requests and
authentication retries can overlap attack indicators. Counts are descriptive, not
claims about detector accuracy. No new coverage gap or data bug is identified by
these checks; preserve the frozen inputs. Small scripted corpus limitations remain.

Validation is automated plus agent review; no independent teammate sign-off is claimed.
the project author can inspect the referenced development raw lines to review security meaning.
Day 23 Dataset v1 packaging and Day 32 final performance evaluation remain future work.
