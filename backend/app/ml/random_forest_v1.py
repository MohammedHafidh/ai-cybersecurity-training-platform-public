"""Day 28 candidate, using the unchanged official Day 27 feature pipeline."""
from collections import Counter

from sklearn.ensemble import RandomForestClassifier

from app.ml.dataset_v1 import SEED, feature_frame, make_pipeline

# Chosen before validation; no search or tuning in Day 28.
PARAMETERS = dict(n_estimators=100, max_depth=4, min_samples_leaf=1,
                  max_features="sqrt", bootstrap=True, n_jobs=1, random_state=SEED)


def fit_random_forest(rows):
    pipeline = make_pipeline().set_params(classifier=RandomForestClassifier(**PARAMETERS))
    counts = Counter(row["run_id"] for row in rows)
    pipeline.fit(feature_frame(rows), [row["attack_label"] for row in rows],
                 classifier__sample_weight=[1 / counts[row["run_id"]] for row in rows])
    return pipeline
