"""Descriptive development-data quality checks; no detector or reserved inputs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import mean, median

from app.ingestion.parsers import parsed_lines
from app.ingestion.pipeline import _event_id
from app.processing.modeling import FEATURES


def summarize(values):
    if not values:
        raise ValueError("cannot summarize an empty feature")
    numeric = [int(value) if isinstance(value, bool) else value for value in values]
    return dict(count=len(numeric), minimum=min(numeric), median=median(numeric),
        maximum=max(numeric), mean=round(mean(numeric), 8),
        zero_count=numeric.count(0), distinct_count=len(set(numeric)))


def build_eda(tables, splits, events, corpus_manifest, raw_base, quality):
    assignments = {}
    for split in ("train", "validation", "test"):
        for assignment in splits[split]:
            if assignment["run_id"] in assignments:
                raise ValueError("duplicate split membership")
            assignments[assignment["run_id"]] = split
    rows = [row for table in tables.values() for row in table]
    if {row["run_id"] for row in rows} != set(assignments):
        raise ValueError("split/table run membership mismatch")
    for split, members in splits.items():
        declared = {rid for member in members for rid in member["row_ids"]}
        observed = {row["row_id"] for row in rows if assignments[row["run_id"]] == split}
        if declared != observed:
            raise ValueError("split/table row membership mismatch")
    event_by_id = {event.event_id:event for event in events}
    if len(event_by_id) != len(events):
        raise ValueError("duplicate normalized evidence")
    consumed = [eid for row in rows for eid in row["event_ids"]]
    if Counter(consumed) != Counter(event_by_id.keys()):
        raise ValueError("table/raw evidence coverage mismatch")
    evidence_locations = {}
    for entry in corpus_manifest["runs"]:
        metadata = json.loads((raw_base / entry["metadata"]).read_text())
        raw = (raw_base / entry["log"]).read_text(encoding="utf-8")
        for line_number, record_number, line, _ in parsed_lines(raw.splitlines(), entry["source_type"]):
            identity = _event_id(metadata["run_id"],entry["log"],line_number,record_number,line)
            if identity in event_by_id:
                evidence_locations[identity] = dict(raw_file=entry["log"],line_number=line_number,
                    record_number=record_number, raw_line_sha256=hashlib.sha256(line.encode()).hexdigest(),
                    metadata_file=entry["metadata"])
    if set(evidence_locations) != set(event_by_id):
        raise ValueError("normalized event cannot be traced to raw record")
    sources, traces = {}, []
    for source, table in sorted(tables.items()):
        selected = [row for row in table if assignments[row["run_id"]] in ("train","validation")]
        if not selected:
            raise ValueError("missing development observations")
        run_labels = {row["run_id"]:row["attack_label"] for row in selected}
        sources[source] = dict(row_count=len(selected), run_count=len(run_labels),
            run_label_counts=dict(sorted(Counter(run_labels.values()).items())),
            row_label_counts=dict(sorted(Counter(row["attack_label"] for row in selected).items())),
            scenario_row_counts=dict(sorted(Counter(row["scenario"] for row in selected).items())),
            missing_cells={name:sum(row.get(name) is None for row in selected) for name in selected[0]},
            features={name:summarize([row[name] for row in selected]) for name in FEATURES[source]})
        for split in ("train","validation"):
            for label in ("benign","malicious"):
                candidates = [row for row in selected if assignments[row["run_id"]] == split and row["attack_label"] == label]
                if not candidates:
                    raise ValueError("source/label split coverage gap")
                row = min(candidates,key=lambda row:row["row_id"])
                evidence = []
                for eid in row["event_ids"]:
                    event = event_by_id[eid]
                    if (event.run_id,event.source_type,event.attack_label,event.scenario) != (row["run_id"],source,label,row["scenario"]):
                        raise ValueError("row/event trusted context mismatch")
                    evidence.append(dict(event_id=eid,**evidence_locations[eid]))
                traces.append(dict(source_type=source,split=split,attack_label=label,
                    row_id=row["row_id"],run_id=row["run_id"],scenario=row["scenario"],
                    contributing_event_count=len(evidence),evidence=evidence))
    return dict(scope="Training and validation descriptive analysis only",
        inventory=dict(total_runs=len(assignments),total_rows=len(rows),total_events=len(events),
            split_run_counts=dict(sorted(Counter(assignments.values()).items())),
            exploratory_test_role="Inventory only; no feature distributions. Not the final benchmark.",
            reserved_final_test_accessed=False), sources=sources,
        corpus_quality=quality, traceability_checks=dict(all_events_traced=True,representative_rows=len(traces)),
        limitations=[
            "Small scripted controlled-lab corpus; distributions do not establish detector performance.",
            "Window rows are not independent runs; authentication has one extra boundary window.",
            "Zero null feature cells coexist with explicitly counted missing/empty raw web inputs.",
            "SQL token matches can occur in benign look-alikes; labels remain trusted metadata.",
            "Network logs observe accepted service connections, not all packets or closed-port attempts.",
            "No data changes, model tuning, threshold selection or reserved final-test analysis performed.",
        ]), traces


def write_eda(report, traces, output: Path):
    output.mkdir(parents=True,exist_ok=False)
    for name,value in (("eda-quality-report.json",report),("traceability-checks.json",traces)):
        (output/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    lines = ["# Day 22 — Development EDA and Quality Review", "", report["scope"], "",
        "Reserved final-test observations were not opened. No detector metrics were computed.", "",
        "## Counts", "", "| Source | Runs | Rows | Benign / malicious runs |", "|---|---:|---:|---|"]
    for source, data in report["sources"].items():
        counts=data["run_label_counts"]
        lines.append(f"| {source} | {data['run_count']} | {data['row_count']} | {counts.get('benign',0)} / {counts.get('malicious',0)} |")
    lines += ["", "## Selected feature distributions", "", "| Source / feature | Min | Median | Max | Mean |", "|---|---:|---:|---:|---:|"]
    for source,data in report["sources"].items():
        for name,stats in data["features"].items():
            lines.append(f"| {source} / {name} | {stats['minimum']} | {stats['median']} | {stats['maximum']} | {stats['mean']} |")
    lines += ["", "## Quality and traceability", "",
        "All accepted events reconcile to raw file/line hashes. Twelve representative train/validation rows cover both labels in each source. See traceability-checks.json.", "",
        "Full corpus exclusion counts are preserved in eda-quality-report.json. Missing feature cells and raw web missing-input counts are reported separately.", "",
        "## Limitations and review", ""] + ["- "+item for item in report["limitations"]]
    lines += ["", "Review conclusion: no new data bug or collection gap was identified by these checks. Preserve current labels/features and splits. Automated review is not independent teammate sign-off.", ""]
    (output/"report.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
    (output/"checksums.json").write_text(json.dumps(hashes,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
