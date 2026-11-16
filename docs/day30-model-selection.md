# Official Day 30: bounded improvement and practical model selection

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

The three original candidates are rebuilt and checked against Days 27-29 before
comparison. All use the immutable Dataset v1 archive, the same 18 training runs,
six validation runs/seven observations, observable allowlist, train-only scaler,
source encoding, inverse observations-per-run weights and any-alert aggregation.
No historical exploratory or reserved final-test member is read.

The predeclared protocol in day30-protocol.json permits exactly one experiment:
reduce Logistic Regression C from 1 to 0.1. Stronger regularization is a plausible
small-sample correction with 18 training observations and 20 transformed inputs.
There is no search, payload-specific feature, label change or threshold adjustment.
Before/after results, including scenario breakdowns, are saved in improvement.json.
The experiment reduced validation accuracy to 4/6 and F1 to 0.75; FPR increased
from 1/3 to 2/3 with recall unchanged. It added a false alert on the benign
single-connection, single-port network validation run. Its run/event IDs are
recorded in improvement.json. Stronger regularization removed useful separation
on this sample rather than providing supported security value, so it was rejected.
No second attempt was made. Unsuccessful improvements are evidence, not grounds
to keep searching.

comparison.md and comparison.json record accuracy, precision, recall, F1, FPR and
confusion matrices. Original candidates each score 5/6 validation runs correct,
precision 0.75, recall 1, F1 0.8571 and FPR 1/3. These tiny scripted samples do not
establish real-world accuracy. High recall here coexists with one false positive;
precision/FPR expose the cost of alerting on benign SQL-like content. No false
negative in six runs proves neither coverage nor robust attack recognition.

Selection follows the declared order: validation run F1, recall, lowest FPR, then
simplicity. Original Logistic Regression wins the metric tie and stays unchanged.
It avoids the complexity of 100-tree ensembles without sacrificing observed
validation behavior. The regularized experiment adds no supported benefit.
selection.json records the choice; the CI artifact includes its trained pipeline.
It remains fitted only to training data, with no train/validation combined refit.
Later packaging and final evaluation remain their planned tasks.

Security review preserves the known benign SQLi false positive, its trusted label
and event IDs. The Day 26 error review traces those events to the actual benign
select request. Counts, tokens, timing and source structure can encode lab habits;
none of this round's results justifies claiming a security improvement. Realistic
benign retries/multi-service traffic can overlap abuse, and unseen syntax or scan
traffic can evade. Review is attributed to the agent and tests, not an invented
independent teammate sign-off. No new leakage-bearing input was introduced.

Reproduce from repo root with the existing pinned ML overlay:

```
python -m pip install -r backend/requirements.txt -r requirements/day27.txt
python -m pytest -q
python scripts/select_day30.py evidence/day30
python scripts/verify_day30.py evidence/day30
```

Use a fresh output directory. The existing ML verification workflow now also runs
a separate Day 30 job and uploads day30-selected-candidate. Runtime-specific model
hashes are verified against the generated manifest; source and dataset hashes and
reviewed results are checked against committed references. Model bytes are not
compared across platforms. Load only trusted artifacts. Day 31 has not started;
independent final performance evaluation remains Day 32.
