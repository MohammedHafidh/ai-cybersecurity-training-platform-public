# Official Day 23 — Dataset v1 Freeze

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Release: data/releases/dataset-v1. Includes a versioned manifest, deterministic tar.gz
and SHA256 checksums. The archive contains development raw evidence, normalized
events (inside raw corpus freeze), feature tables/dictionary, split manifests, EDA,
traceability reports, pipeline sources and a separately sealed final-test archive.
Only lab-generated data is included. No models or predictions are part of this release.

Rebuild: `python scripts/package_dataset_v1.py OUTPUT_DIRECTORY`.
Verify: `python scripts/package_dataset_v1.py data/releases/dataset-v1 --verify`.
Install backend/requirements.txt first. Verification replays archived sources,
regenerates Days 20–22 and
compares every byte. Reserved archive access is limited to hashing its compressed
bytes; it is never extracted for analysis. Exact hashes bind all source versions.
The nested final-test archive must remain sealed until the Day 32 evaluation.
Text sources are canonicalized to LF; archive bytes remain unchanged. Tar headers
and gzip time/name are fixed. Gzip uses stored blocks for cross-runtime reproducibility.
Later source additions do not invalidate v1: verification uses its archived pipeline
version and compares the reproduced archive byte-for-byte.

Development: 30 runs, 31 feature rows, 90 accepted events. Training has 18 runs;
validation six; six historical exploratory runs are excluded from the final
benchmark. One authentication run contributes two windows and remains in one split.
The separate final evidence has 12 prospectively reserved runs (two per source/label).
Its features and detector metrics have not been generated. Dataset v1 is a package
of distinct tables and evidence roles, not a merged training CSV.

Security validation uses the existing raw/metadata audit, event conservation,
12 representative development traces, and prospective reservation integrity checks.
No independent teammate sign-off is claimed. Actual human review remains attributable
to the project author. Small scripted samples, service-only network visibility, benign token
overlap and the same synthetic targets limit generalization. This milestone freezes
inputs; it does not assert detector quality.

Do not overwrite v1 or tune test labels/features. New data fixes require a new
version with a recorded reason. After verified merge, CI creates annotated tag
dataset-v1. Official Day 24 rule work and Day 32 final evaluation remain future work.
