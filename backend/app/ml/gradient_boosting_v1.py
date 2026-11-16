"""Official third and final candidate, with unchanged Dataset v1 preprocessing."""
from collections import Counter

from sklearn.ensemble import GradientBoostingClassifier

from app.ml.dataset_v1 import SEED, feature_frame, make_pipeline

# Fixed before validation; improvement/model selection is reserved for Day 30.
PARAMETERS = dict(n_estimators=100, learning_rate=0.1, max_depth=2,
                  min_samples_leaf=1, subsample=1.0, loss="log_loss",
                  random_state=SEED, n_iter_no_change=None)


def fit_gradient_boosting(rows):
    model = make_pipeline().set_params(classifier=GradientBoostingClassifier(**PARAMETERS))
    counts = Counter(row["run_id"] for row in rows)
    model.fit(feature_frame(rows), [row["attack_label"] for row in rows],
              classifier__sample_weight=[1 / counts[row["run_id"]] for row in rows])
    return model
