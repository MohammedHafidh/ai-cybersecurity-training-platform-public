"""Reproducible run-grouped experimental splits, never a claim of unseen families."""
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


SEED = 42


def split_tables(tables, seed=SEED):
    runs = {}
    row_ids, event_ids = set(), set()
    for source, rows in sorted(tables.items()):
        for row in rows:
            if row["source_type"] != source:
                raise ValueError("source mismatch")
            if row["row_id"] in row_ids:
                raise ValueError("duplicate row ID")
            row_ids.add(row["row_id"])
            if not row["event_ids"] or set(row["event_ids"]) & event_ids or len(row["event_ids"]) != len(set(row["event_ids"])):
                raise ValueError("empty or duplicate event provenance")
            event_ids.update(row["event_ids"])
            context = (source, row["attack_label"], row["scenario"])
            run = runs.setdefault(row["run_id"], dict(context=context, rows=[], events=[]))
            if run["context"] != context:
                raise ValueError("inconsistent run context")
            run["rows"].append(row["row_id"])
            run["events"].extend(row["event_ids"])
    strata = defaultdict(list)
    for run_id, run in runs.items():
        strata[run["context"][:2]].append(run_id)
    expected = {(s,l) for s in ("auth", "web", "network") for l in ("benign", "malicious")}
    if set(strata) != expected or any(len(ids) != 5 for ids in strata.values()):
        raise ValueError("five runs in each of six source-label strata required")
    rng = random.Random(seed)
    assignments = []
    for stratum, ids in sorted(strata.items()):
        ordered = sorted(ids)
        rng.shuffle(ordered)
        for index, run_id in enumerate(ordered):
            split = "train" if index < 3 else "validation" if index == 3 else "test"
            run = runs[run_id]
            assignments.append(dict(run_id=run_id, split=split, source_type=stratum[0],
                attack_label=stratum[1], scenario=run["context"][2],
                row_ids=sorted(run["rows"]), event_ids=sorted(run["events"])))
    assignments.sort(key=lambda row: row["run_id"])
    report = dict(seed=seed, grouping="run_id", run_counts=dict(Counter(row["split"] for row in assignments)),
        row_counts={split:sum(len(row["row_ids"]) for row in assignments if row["split"] == split) for split in ("train", "validation", "test")},
        leakage_checks=dict(unique_run_membership=True, unique_row_membership=True, unique_event_membership=True),
        independence_review=dict(run_disjoint=True, unseen_scenario_families=False,
            untouched_final_benchmark=False,
            limitation="All frozen templates were explored in earlier experiments. Run-disjoint splits do not establish family independence. These are experimental splits only; final ML claims require a separately reserved independent collection."))
    return assignments, report


def write_splits(assignments, report, output: Path, inputs):
    output.mkdir(parents=True, exist_ok=False)
    for split in ("train", "validation", "test"):
        (output / f"{split}.json").write_text(json.dumps([r for r in assignments if r["split"] == split], indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    report["input_sha256"] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)}
    (output / "split-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
