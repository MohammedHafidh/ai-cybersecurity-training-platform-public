# Carryover completion before official Day 20

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Historical commit day labels do not replace official roadmap acceptance criteria.
This cleanup finishes observation features and the raw corpus gate; it does not
create the Day 20 modeling table or freeze Dataset v1.

## Features

Authentication groups by run, canonical source IP, metadata target, and epoch-aligned
60-second UTC windows [start,end), matching Day 19. Counts include attempts,
failures, successes, unique users, attempts/60 seconds and success after a strictly
earlier failure. Same-time events do not establish order. Distinct event IDs count
separately. The corpus stage removes exact duplicate observations first.
Live collection includes one incorrect password then successful normal logins;
this intentional typo/retry remains benign ground truth. CI verifies a window with
both failure and subsequent success. If a retry crosses a boundary it occupies
separate windows, as documented; do not expand windows to force a preferred result.

Web parsing preserves server-decoded id_input, including empty strings. Only when
absent does it decode raw_query once. Missing input is None. Double encoding stays
visible as residual percent escapes. The web table records request counts, missing
and empty inputs, maximum length, suspicious tokens, residual encoding and errors.
Real benign cases include invalid SQL-like text, missing/empty input and double
encoding. An HTTP 400 or a suspicious token does not make a request malicious.
These separate feature outputs preserve existing model contracts for later Day 20
integration. Current target supports GET query evidence, not POST body SQLi.

## Corpus policy and reproduction

Metadata requires aware timestamps, ordered windows, nonempty identity/source/target/
method, safe unique relative source paths and explicit reasons for excluded/review
runs. Corpus ingestion rejects duplicate run IDs and missing source files. Every
run remains in provenance. Excluded/review runs remain in an exclusion ledger and
are never relabeled. Exact parsed observations within one run are deduplicated;
different timestamps remain distinct. This conservative rule can conflate genuinely
identical observations with identical timestamps; retained raw logs permit review.
Background/non-event lines, other-run observations, out-of-window events, invalid
records and parse failures are counted and logged. Unresolved candidate parse or
required-field failures block the freeze. Missing optional web input is counted,
not guessed. Quality report includes coverage, accepted counts and exclusion counts.

From repo root: `python -m pytest -q`. From backend: the same command works.
On a Docker host, use the environment settings in carryover-verify.yml and run
`PYTHONPATH=backend python scripts/collect_day11_dataset.py`, then
`PYTHONPATH=backend python scripts/freeze_raw_corpus.py evidence/raw-corpus-v0.1/manifest.json evidence/raw-corpus-v0.1/freeze`.
The `--verify` mode rebuilds the manifest and checks every raw/metadata checksum.
Recollection generates new evidence; reproducibility of the frozen corpus means
rebuilding from the same archived bytes, not expecting identical new attack logs.

The CI archive contains original logs, metadata, responses, manifest, exclusion
ledger, quality report, normalized events and feature previews. The archive SHA256
identifies exact bytes. Freeze refuses to overwrite an existing output directory.
Raw corpus v0.1 must be retained with its verified CI artifact ID and checksum;
the small verified snapshot is retained under data/raw-corpus-v0.1 with its checksum,
source commit and artifact ID. Run `python scripts/verify_frozen_corpus.py` to replay
its quality and provenance checks without Docker. It is not Dataset v1 or a final test set.

## Ownership and next gates

Automated validation is recorded as automated; no teammate sign-off is claimed.
the project author should review representative raw counts and security meanings. Official
Days 20–23 still require modeling table/data dictionary, independent split manifests,
EDA and Dataset v1 release. Final ML evaluation remains Days 27–32. Variant 05 was
previously explored and cannot be described as untouched. Existing legacy artifact
and function names remain for compatibility, with explicit report limitations.
