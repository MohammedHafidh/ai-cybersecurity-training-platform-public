# Day 17 — Robust Controlled-Variant Evaluation

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Day 17 corrects the main methodological risk identified after Day 16: the original
dataset repeated fixed lab activity. A high score on repeated templates is not
evidence that a detector generalizes.

## Controlled variants

The dataset remains bounded to the three agreed lab scenarios and contains 30 runs.
Each source/label stratum now has five explicit variants:

- authentication varies the number of normal logins or failed attempts;
- web activity varies normal record lookups and SQL-injection expressions;
- network activity varies normal health probes and bounded Nmap port/repeat sets.

Targets remain hard-coded Docker service names on the internal lab network. This is
controlled variation, not unrestricted fuzzing or external attack traffic.

## Grouped evaluation

Variant 01 from all six source/label strata forms one evaluation group, and likewise
for variants 02–05. Five-fold `StratifiedGroupKFold` keeps an entire controlled
variant out of training in each fold. This prevents executions of the same template
family from appearing in both training and validation.

The selected model remains a controlled-lab candidate. Day 17 improves the evidence;
it does not claim production performance or expand the mandatory attack scope.

## Definition of Done

- 30 new real Docker-lab runs with trusted metadata.
- Five variants for each source/label stratum.
- At least three distinct numeric feature profiles per stratum.
- Grouped five-fold predictions with no variant split across folds.
- Required accuracy, precision, recall, F1, false-positive rate and confusion matrix.
- Backend tests, lab collection and evaluation pass in GitHub Actions.
