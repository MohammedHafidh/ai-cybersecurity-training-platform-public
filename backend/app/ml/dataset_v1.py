"""Official Dataset v1 harness. Never open reserved or exploratory test members."""
import hashlib
import json
import tarfile
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ARCHIVE_SHA = "b660122cadb05c6124d03573cebfcf27f07c0520813487960f1b5e7e8bd4b499"
FEATURES = {
    "auth": ["attempt_count", "attempts_per_second", "failed_login_count",
             "successful_login_count", "success_after_failure", "unique_username_count"],
    "web": ["request_count", "max_request_length", "suspicious_token_count",
            "error_response_count", "empty_input_count", "missing_input_count", "residual_encoded_count"],
    "network": ["connection_count", "connections_per_second", "observed_span_seconds",
                "unique_destination_port_count"],
}
NUMERIC = [field for fields in FEATURES.values() for field in fields]
SEED = 42


def load_development(root):
    archive = root / "data/releases/dataset-v1/dataset-v1.tar.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError("Dataset v1 archive checksum mismatch")
    with tarfile.open(archive, "r:gz") as tar:
        def read(path):
            # Exact allowlist: never extract nested evidence or any test split.
            allowed = {f"data/processed/day20/{s}.jsonl" for s in FEATURES}
            allowed.update(f"data/processed/day21/{s}.json" for s in ("train", "validation"))
            if path not in allowed:
                raise ValueError("prohibited dataset member")
            return tar.extractfile("dataset-v1/" + path).read().decode("utf-8")
        tables = {s: {r["row_id"]: r for r in map(json.loads, read(
            f"data/processed/day20/{s}.jsonl").splitlines())} for s in FEATURES}
        result, seen_runs, seen_rows, seen_events = {}, set(), set(), set()
        for split in ("train", "validation"):
            rows = []
            for member in json.loads(read(f"data/processed/day21/{split}.json")):
                run = member["run_id"]
                if run in seen_runs:
                    raise ValueError("overlapping run")
                seen_runs.add(run)
                for row_id in member["row_ids"]:
                    row = tables[member["source_type"]][row_id]
                    if (row["run_id"] != run or row["attack_label"] != member["attack_label"]
                            or row_id in seen_rows or seen_events.intersection(row["event_ids"])):
                        raise ValueError("invalid membership or duplicate observation")
                    seen_rows.add(row_id)
                    seen_events.update(row["event_ids"])
                    rows.append(row)
            result[split] = rows
    return result


def feature_frame(rows):
    records = []
    for row in rows:
        source = row["source_type"]
        record = dict.fromkeys(NUMERIC, 0.0)
        for name in FEATURES[source]:
            value = float(row[name])
            if not np.isfinite(value) or value < 0:
                raise ValueError("nonfinite or negative observation")
            record[name] = value
        record["source_type"] = source
        records.append(record)
    return pd.DataFrame(records, columns=[*NUMERIC, "source_type"])


def make_pipeline():
    return Pipeline([
        ("features", ColumnTransformer([
            ("numeric", StandardScaler(), NUMERIC),
            ("source", OneHotEncoder(categories=[["auth", "network", "web"]],
                                     handle_unknown="error", sparse_output=False), ["source_type"]),
        ], remainder="drop")),
        ("classifier", LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000,
                                          random_state=SEED)),
    ])


def fit_baseline(rows):
    pipeline = make_pipeline()
    counts = Counter(row["run_id"] for row in rows)
    weights = [1 / counts[row["run_id"]] for row in rows]
    pipeline.fit(feature_frame(rows), [r["attack_label"] for r in rows],
                 classifier__sample_weight=weights)
    if pipeline.named_steps["classifier"].n_iter_.max() >= 1000:
        raise ValueError("Logistic Regression did not converge")
    return pipeline
