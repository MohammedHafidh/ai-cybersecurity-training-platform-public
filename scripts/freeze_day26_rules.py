"""Freeze development-only rule results and trace errors to original evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from build_day25_rules import build
from app.ingestion.corpus import audit_corpus
from app.ingestion.parsers import parsed_lines
from app.ingestion.pipeline import _event_id


def canonical(path):
    return path.read_bytes().replace(b"\r\n",b"\n")


def freeze(output):
    with tempfile.TemporaryDirectory() as directory:
        temporary=Path(directory)
        regenerated=temporary/"rules"
        build(regenerated)
        reference=ROOT/"data/processed/day25"
        if {p.name:p.read_bytes() for p in regenerated.iterdir()}!={p.name:p.read_bytes() for p in reference.iterdir()}:
            raise ValueError("Day 25 decisions or metrics changed before freeze")
        observations=json.loads((regenerated/"observation-decisions.json").read_text())
        decisions=json.loads((regenerated/"run-decisions.json").read_text())
        report=json.loads((regenerated/"validation-report.json").read_text())
        truth={}
        for split in ("train","validation"):
            for row in json.loads((ROOT/f"data/processed/day21/{split}.json").read_text()):
                if row["run_id"] in truth:
                    raise ValueError("duplicate run membership")
                truth[row["run_id"]]=row["attack_label"]
        error_decisions=[row for row in decisions if row["predicted_label"]!=truth[row["run_id"]]]
        # Development raw evidence only; never open the reserved final archive.
        raw_archive=ROOT/"data/raw-corpus-v0.1/raw-corpus-v0.1.tar.gz"
        if hashlib.sha256(raw_archive.read_bytes()).hexdigest()!="e35bfe2e7d5d4bc2638ed31dc0d830db57e35a0def8578277586d334d9b096b9":
            raise ValueError("development raw corpus checksum mismatch")
        with tarfile.open(raw_archive) as archive:
            archive.extractall(temporary/"raw",filter="data")
        base=temporary/"raw/raw-corpus-v0.1"
        events,_,_,snapshot=audit_corpus(base/"manifest.json")
        by_event={e.event_id:e for e in events}
        entries=json.loads((base/"manifest.json").read_text())["runs"]
        by_run={row["run_id"]:row for row in snapshot["runs"]}
        raw_locations={}
        for entry in entries:
            metadata=json.loads((base/entry["metadata"]).read_text())
            for line_number,record_number,line,_ in parsed_lines((base/entry["log"]).read_text().splitlines(),entry["source_type"]):
                eid=_event_id(metadata["run_id"],entry["log"],line_number,record_number,line)
                raw_locations[eid]=dict(file=entry["log"],line_number=line_number,record_number=record_number,
                    line_sha256=hashlib.sha256(line.encode()).hexdigest())
        errors=[]
        for decision in error_decisions:
            run_id=decision["run_id"]
            supporting=[d for d in observations if d["run_id"]==run_id]
            event_ids=sorted({eid for d in supporting for eid in d["evidence"]["event_ids"]})
            evidence=[]
            for eid in event_ids:
                event=by_event[eid]
                if event.run_id!=run_id or event.attack_label!=truth[run_id]:
                    raise ValueError("error trace context mismatch")
                evidence.append(dict(event_id=eid,request_data=event.request_data,
                    status_code=event.status_code,**raw_locations[eid]))
            errors.append(dict(run_id=run_id,source_type=decision["source_type"],split=decision["split"],
                ground_truth=truth[run_id],predicted_label=decision["predicted_label"],
                error_type="false_positive" if truth[run_id]=="benign" else "false_negative",
                metadata_file=by_run[run_id]["metadata"],rule_evidence=[d["evidence"] for d in supporting],
                raw_evidence=evidence,interpretation="The heuristic disagrees with trusted run intent; matching tokens/ports/counts are indicators, not ground truth."))
        report["stage"]="rule-engine-v1 frozen development results"
        report["evaluation_scope"]="18 training and six validation runs; reserved final benchmark not evaluated"
        report["error_count"]=len(errors)
        report["security_review"]={
            "auth":"Retries and attacks pass this small development set; legitimate repeated mistakes and distributed/slow attacks remain risks.",
            "web":"Observed benign SQL-like text triggers one false positive. Preserve it; do not tune to remove it.",
            "network":"Small development set passes; legitimate multi-port activity can trigger and service logs omit closed-port/SYN attempts.",
            "reviewer":"Automated trace checks and agent review; no independent teammate sign-off claimed."}
        output.mkdir(parents=True,exist_ok=False)
        payloads={"metrics.json":report,"error-review.json":errors,
            "run-decisions.json":decisions,"observation-decisions.json":observations}
        for name,value in payloads.items():
            (output/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
        lines=["# Rule engine v1 — frozen development evaluation","",
            "Training and validation only. Final-test evidence remains sealed until Day 32.","",
            "| Split / source | Runs | Accuracy | Precision | Recall | F1 | FPR | Confusion matrix [benign, malicious] |",
            "|---|---:|---:|---:|---:|---:|---:|---|"]
        for split,data in report["metrics"].items():
            rows=[("overall",data["overall_run_metrics"])]+[(source,values["run_metrics"]) for source,values in data["by_source"].items()]
            for source,m in rows:
                lines.append(f"| {split}/{source} | {m['sample_count']} | {m['accuracy']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['false_positive_rate']:.4f} | {m['confusion_matrix']} |")
        lines += ["","## Error review","",f"{len(errors)} development run error(s), all preserved with metadata and raw line hashes in error-review.json.",
            "The SQLi keyword heuristic flags benign look-alike text. Ground truth comes from the prescribed run, not the rule. No threshold change was made.","",
            "## Interpretation","","Small scripted samples do not establish general accuracy. Window and run metrics are separate in metrics.json. Run aggregation is any triggered observation.",
            "Legitimate retries and multi-service activity may trigger; slow/distributed activity and unrecognized SQL syntax may evade.",
            "No ML comparison or reserved final-test evaluation was performed. Frozen results are suitable for later UI/report integration with these limitations.",""]
        (output/"report.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")
        source_paths=[ROOT/p for p in ("backend/app/detection/auth_baseline.py","backend/app/detection/scenario_baselines.py",
            "scripts/build_day25_rules.py","scripts/freeze_day26_rules.py")]
        manifest=dict(version="rule-engine-v1",thresholds=report["thresholds"],
            input_sha256=report["input_sha256"],
            source_sha256={str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(canonical(p)).hexdigest() for p in source_paths},
            output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
            final_test_evaluated=False,threshold_changes=False)
        (output/"freeze-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
        print(f"Rule engine v1 development results frozen; {len(errors)} traced error(s); final evidence sealed")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    freeze(parser.parse_args().output)


if __name__=="__main__":
    main()
