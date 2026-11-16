import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.detection.scenario_baselines import INPUT_MODELS,detect_scenario_rows
from app.detection.auth_baseline import binary_metrics


def build(output):
    base=ROOT/"data/processed/day20"
    hashes=json.loads((base/"checksums.json").read_text())
    tables={}
    for source in INPUT_MODELS:
        path=base/f"{source}.jsonl"
        if hashlib.sha256(path.read_bytes()).hexdigest()!=hashes[path.name]:
            raise ValueError("feature checksum mismatch")
        tables[source]={row["row_id"]:row for row in map(json.loads,path.read_text().splitlines())}
    decisions,run_decisions,metrics=[],[],{}
    used=set()
    inputs={f"data/processed/day20/{s}.jsonl":hashes[f"{s}.jsonl"] for s in tables}
    for split in ("train","validation"):
        path=ROOT/f"data/processed/day21/{split}.json"
        members=json.loads(path.read_text())
        inputs[str(path.relative_to(ROOT)).replace("\\","/")]=hashlib.sha256(path.read_bytes()).hexdigest()
        ids=[member["run_id"] for member in members]
        if len(ids)!=len(set(ids)) or used.intersection(ids):
            raise ValueError("duplicate or overlapping run membership")
        used.update(ids)
        split_truth,split_predictions=[],[]
        by_source={}
        for source,model in INPUT_MODELS.items():
            source_members=[member for member in members if member["source_type"]==source]
            selected=[]
            truth={}
            for member in source_members:
                truth[member["run_id"]]=member["attack_label"]
                for row_id in member["row_ids"]:
                    row=tables[source][row_id]
                    if row["run_id"]!=member["run_id"] or row["attack_label"]!=member["attack_label"]:
                        raise ValueError("trusted context mismatch")
                    selected.append(row)
            observations=[model(**{name:row[name] for name in model.model_fields}) for row in selected]
            detected=detect_scenario_rows(source,observations)
            decisions.extend(dict(source_type=source,split=split,**item) for item in detected)
            predicted={run_id:("malicious" if any(d["triggered"] for d in detected if d["run_id"]==run_id) else "benign") for run_id in truth}
            for run_id in sorted(predicted):
                run_decisions.append(dict(source_type=source,split=split,run_id=run_id,
                    predicted_label=predicted[run_id],aggregation="any window/run rule triggered",
                    row_ids=sorted(d["row_id"] for d in detected if d["run_id"]==run_id)))
            by_source[source]=dict(run_metrics=binary_metrics([truth[r] for r in sorted(predicted)],[predicted[r] for r in sorted(predicted)]),
                observation_metrics=binary_metrics([tables[source][d["row_id"]]["attack_label"] for d in detected],[d["predicted_label"] for d in detected]))
            split_truth.extend(truth[r] for r in sorted(predicted))
            split_predictions.extend(predicted[r] for r in sorted(predicted))
        metrics[split]=dict(by_source=by_source,overall_run_metrics=binary_metrics(split_truth,split_predictions))
    report=dict(stage="Day 25 development validation; Day 26 freeze pending",metrics=metrics,input_sha256=inputs,
        thresholds=dict(auth_failed_logins=3,web_suspicious_tokens=1,network_unique_ports=2),
        threshold_changes="None: Day 24 auth retained; token>=1 and ports>=2 retain earlier heuristic values in validated contracts.",
        limitations=["Token matches are heuristic and can flag benign words or miss syntax/encoding variants.",
            "Two observed ports can be legitimate maintenance. Single-port or distributed scans can evade.",
            "Network evidence covers accepted service connections only. Fixed windows may divide activity.",
            "Small scripted development sample; no final test, historical test or ML evaluation performed."])
    output.mkdir(parents=True,exist_ok=False)
    for name,value in (("observation-decisions.json",decisions),("run-decisions.json",run_decisions),("validation-report.json",report)):
        (output/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("All three development rule baselines validated; final-test evidence untouched")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    build(parser.parse_args().output)


if __name__=="__main__":
    main()
