# Official Day 24 — Brute-force Rule Baseline v1

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Rule contract: AuthWindowInput contains observable counts, identity/provenance and
a fixed epoch-aligned 60-second source/target/run window. Extra fields, including
ground-truth labels and scenarios, are rejected. Counts reconcile to unique event
IDs. Results include a stable detection ID, rule version, row/run IDs, prediction,
trigger flag, numeric threshold evidence, group/window and contributing event IDs.
No ground truth is stored in detector outputs. Run decisions use any triggered
window, never a majority vote that could hide a short attack burst.

Baseline auth-failed-burst-v1: failed_login_count >= 3 in one existing 60-second
window. This is an explicit small-lab baseline, not a universal SSH security policy.
Rationale: allow an isolated typo/retry while flagging repeated failures. Three
failures is a fixed transparent starting point; no threshold sweep, final-test
inspection or performance-driven parameter search was performed. Successes do not
erase preceding failures. The earlier run-level two-failure prototype is preserved
for historical API compatibility; it is not this versioned window baseline. Later
planned API integration must explicitly select the new contract rather than
silently mixing run aggregates with windows.

Rebuild: `python scripts/build_day24_auth_baseline.py OUTPUT_DIRECTORY`.
Reports under data/processed/day24 include separate window and run predictions,
train/validation metrics and input hashes. Only the six auth training runs and two
auth validation runs are consumed; the validation benign run has two window rows.
Ground truth is joined by the evaluation harness only. Accuracy, precision, recall,
F1, FPR and a confusion matrix use label order [benign, malicious]. No-support
denominators return zero and sample counts are recorded. Required metrics are
descriptive on a very small known development corpus, not a final benchmark.

Challenge cases: one or two failures followed by success remain below threshold;
exactly three failures trigger; successes do not suppress a burst. A legitimate
three-typo window is a possible false positive. Slow attempts spanning windows,
distributed sources, different targets or low-and-slow attacks may evade. Synthetic
unit challenges document these limitations, and real frozen benign retry/attack
runs supply the development validation. No reserved case is analyzed to change the
rule. The final-test archive stays sealed until Day 32.

CI checks full tests and byte-identical regeneration. Security interpretation is
automated/agent review with actual development evidence; no teammate sign-off is
invented. Day 25 SQLi/recon rules and Day 26 measured rule-engine freeze remain
future work. Dataset v1 remains immutable; its archived pipeline replays independently
of this new detector implementation.
