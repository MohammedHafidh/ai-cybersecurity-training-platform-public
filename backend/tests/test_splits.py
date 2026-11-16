from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.processing.splits import split_tables


def tables():
    base = Path(__file__).parents[2] / "data/processed/day20"
    return {s:[json.loads(line) for line in (base / f"{s}.jsonl").read_text().splitlines()] for s in ("auth", "web", "network")}


def test_reproducible_and_run_row_event_disjoint():
    data = tables()
    assignments, report = split_tables(data)
    assert (assignments, report) == split_tables({s:list(reversed(rows)) for s,rows in reversed(list(data.items()))})
    assert report["run_counts"] == {"train":18,"validation":6,"test":6}
    for key in ("run_id", "row_ids", "event_ids"):
        values = [value for row in assignments for value in ([row[key]] if key == "run_id" else row[key])]
        assert len(values) == len(set(values))
    assert sum(len(row["row_ids"]) for row in assignments) == 31
    assert sum(len(row["event_ids"]) for row in assignments) == 90
    for split in ("train", "validation", "test"):
        assert {(row["source_type"],row["attack_label"]) for row in assignments if row["split"] == split} == {(s,l) for s in data for l in ("benign","malicious")}
    assert not report["independence_review"]["untouched_final_benchmark"]


def test_feature_values_cannot_influence_membership():
    data = tables()
    changed = deepcopy(data)
    for rows in changed.values():
        for row in rows:
            for name,value in row.items():
                if isinstance(value, (int,float,bool)):
                    row[name] = 999
    assert split_tables(data) == split_tables(changed)


def test_duplicate_provenance_and_missing_stratum_rejected():
    data = tables()
    changed = deepcopy(data)
    changed["auth"].append(changed["auth"][0])
    with pytest.raises(ValueError, match="duplicate"):
        split_tables(changed)
    changed = deepcopy(data)
    changed["web"][1]["event_ids"] = changed["web"][0]["event_ids"]
    with pytest.raises(ValueError, match="provenance"):
        split_tables(changed)
    del data["network"]
    with pytest.raises(ValueError, match="six"):
        split_tables(data)
