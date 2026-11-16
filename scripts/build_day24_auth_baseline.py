import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.detection.auth_baseline import AuthWindowInput,RULE_VERSION,FAILURE_THRESHOLD,detect_auth_windows,binary_metrics


def build(output):
    base=ROOT/"data/processed/day20"
    hashes=json.loads((base/"checksums.json").read_text())
    if hashlib.sha256((base/"auth.jsonl").read_bytes()).hexdigest()!=hashes["auth.jsonl"]:
        raise ValueError("authentication table checksum mismatch")
    rows=[json.loads(line) for line in (base/"auth.jsonl").read_text().splitlines()]
    by_id={row["row_id"]:row for row in rows}
    predictions,run_decisions,reports=[],[],{}
    input_hashes={"data/processed/day20/auth.jsonl":hashes["auth.jsonl"]}
    used=set()
    for split in ("train","validation"):
        path=ROOT/f"data/processed/day21/{split}.json"
        input_hashes[str(path.relative_to(ROOT)).replace("\\","/")]=hashlib.sha256(path.read_bytes()).hexdigest()
        members=[run for run in json.loads(path.read_text()) if run["source_type"]=="auth"]
        if used.intersection(run["run_id"] for run in members):
            raise ValueError("training/validation run overlap")
        used.update(run["run_id"] for run in members)
        selected=[]
        truth_by_run={}
        for member in members:
            truth_by_run[member["run_id"]]=member["attack_label"]
            for row_id in member["row_ids"]:
                row=by_id[row_id]
                if row["run_id"]!=member["run_id"] or row["attack_label"]!=member["attack_label"]:
                    raise ValueError("split/feature context mismatch")
                selected.append(row)
        # Only observable fields enter the detector. Labels remain in this harness.
        inputs=[AuthWindowInput(**{name:row[name] for name in AuthWindowInput.model_fields}) for row in selected]
        detected=detect_auth_windows(inputs)
        predictions.extend(dict(split=split,**item) for item in detected)
        run_predictions={run_id:("malicious" if any(d["triggered"] for d in detected if d["run_id"]==run_id) else "benign") for run_id in truth_by_run}
        for run_id,predicted in sorted(run_predictions.items()):
            run_decisions.append(dict(run_id=run_id,split=split,predicted_label=predicted,
                rule_version=RULE_VERSION,aggregation="any window triggered",
                window_row_ids=sorted(d["row_id"] for d in detected if d["run_id"]==run_id)))
        reports[split]=dict(run_metrics=binary_metrics([truth_by_run[r] for r in sorted(run_predictions)],
            [run_predictions[r] for r in sorted(run_predictions)]),
            window_metrics=binary_metrics([by_id[d["row_id"]]["attack_label"] for d in detected],
                [d["predicted_label"] for d in detected]))
    report=dict(rule_version=RULE_VERSION,threshold=FAILURE_THRESHOLD,window_seconds=60,
        threshold_selection="Fixed three-failure baseline; no parameter search or test tuning",
        metrics=reports,input_sha256=input_hashes,
        limitations=["Small scripted development corpus; validation does not establish general accuracy.",
            "Legitimate repeated mistakes may trigger; slow/distributed attempts may evade.",
            "Successful logins do not cancel failures. Fixed window boundaries can divide activity.",
            "No final-test archive, historical test partition or ML model consumed."])
    output.mkdir(parents=True,exist_ok=False)
    for name,value in (("window-decisions.json",predictions),("run-decisions.json",run_decisions),("validation-report.json",report)):
        (output/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("Day 24 development-only brute-force rule validation complete")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    build(parser.parse_args().output)


if __name__=="__main__":
    main()
