import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from verify_frozen_corpus import main as verify_development
from app.ingestion.corpus import audit_corpus
from app.ingestion.pipeline import load_run_metadata
from app.processing.modeling import build_modeling_tables
from app.processing.eda import build_eda,write_eda


def build_report(output):
    verify_development()
    table_dir=ROOT/"data/processed/day20"
    hashes=json.loads((table_dir/"checksums.json").read_text())
    for name,expected in hashes.items():
        if hashlib.sha256((table_dir/name).read_bytes()).hexdigest()!=expected:
            raise ValueError("Day 20 input checksum mismatch")
    tables={s:[json.loads(line) for line in (table_dir/f"{s}.jsonl").read_text().splitlines()] for s in ("auth","web","network")}
    split_dir=ROOT/"data/processed/day21"
    split_report=json.loads((split_dir/"split-report.json").read_text())
    for name,expected in split_report["input_sha256"].items():
        if hashlib.sha256((table_dir/name).read_bytes()).hexdigest()!=expected:
            raise ValueError("split source checksum mismatch")
    splits={s:json.loads((split_dir/f"{s}.json").read_text()) for s in ("train","validation","test")}
    with tempfile.TemporaryDirectory() as directory:
        with tarfile.open(ROOT/"data/raw-corpus-v0.1/raw-corpus-v0.1.tar.gz") as archive:
            archive.extractall(directory,filter="data")
        base=Path(directory)/"raw-corpus-v0.1"
        manifest=json.loads((base/"manifest.json").read_text())
        events,_,quality,_=audit_corpus(base/"manifest.json")
        metadata={}
        for entry in manifest["runs"]:
            run=load_run_metadata(base/entry["metadata"])
            metadata[run.run_id]=run
        if build_modeling_tables(events,metadata)!=tables:
            raise ValueError("committed features differ from raw-evidence rebuild")
        report,traces=build_eda(tables,splits,events,manifest,base,quality)
        report["input_sha256"]={str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/"data/raw-corpus-v0.1/raw-corpus-v0.1.tar.gz",*[table_dir/f"{s}.jsonl" for s in tables],*[split_dir/f"{s}.json" for s in splits]]}
        write_eda(report,traces,output)
        print(f"EDA and traceability passed: {len(traces)} representative development rows; reserved observations untouched")


def main():
    parser=argparse.ArgumentParser(description="Official Day 22 development EDA and quality report")
    parser.add_argument("output",type=Path)
    build_report(parser.parse_args().output)


if __name__=="__main__":
    main()
