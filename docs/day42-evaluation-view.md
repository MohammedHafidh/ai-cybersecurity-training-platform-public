# Day 42 evaluation and explanation preview

Open **Evaluation** in the dashboard to compare the frozen Day 32 rule and ML results. The frontend imports the public [aggregate report](../data/processed/day32/evaluation.json) at build time. It displays accuracy, precision, recall, F1, false positive rate, and confusion matrices overall and by scenario. Rows are actual labels and columns are predicted labels. Each cell counts runs. The malicious class is positive, and any malicious observation flags its run.

The comparison covers 12 scripted held-out lab runs, four per scenario. It describes performance on this lab dataset. The report records zero for rates with zero denominators, including precision if no runs were flagged. Day 42 reads the frozen results without rescoring the holdout.

In **Detection evidence**, the observed features and source references appear before the **Explanation preview**. The preview reads the stored rule feature, value, operator, and threshold to say whether the measured value met the threshold. It reports when a supported threshold is unavailable. The ML prediction stays in the ML panel. The preview uses no LLM and makes no claim about which features drove the model's prediction.

GitHub-hosted verification checks the rendered matrix orientation and values, metric labels, lab limitations, and deterministic explanation wording, alongside the existing FastAPI integration and PostgreSQL tests.
