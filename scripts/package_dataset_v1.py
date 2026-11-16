"""Freeze reproducible development data and a separately sealed final archive."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]


def canonical_bytes(path):
    data=path.read_bytes()
    return data if path.name.endswith(".gz") else data.replace(b"\r\n",b"\n")


def inputs():
    paths=[]
    for folder in ("data/processed/day20","data/processed/day21","data/processed/day22",
                   "data/raw-corpus-v0.1","data/reserved-final-test-v1","backend/app","scripts"):
        paths += [p for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [ROOT/"backend/requirements.txt",ROOT/"pytest.ini"]
    return sorted(set(paths))


def verify_sources():
    with tempfile.TemporaryDirectory() as directory:
        for day,script in ((20,"build_day20_tables.py"),(21,"build_day21_splits.py"),(22,"build_day22_report.py")):
            target=Path(directory)/str(day)
            subprocess.run([sys.executable,str(ROOT/"scripts"/script),str(target)],cwd=ROOT,check=True)
            reference=ROOT/f"data/processed/day{day}"
            if {p.name:p.read_bytes() for p in reference.iterdir()} != {p.name:p.read_bytes() for p in target.iterdir()}:
                raise ValueError(f"Day {day} rebuild mismatch")
    # Only hash the sealed final archive; never extract or analyze its observations.
    base=ROOT/"data/reserved-final-test-v1"
    lock=json.loads((base/"reservation-lock.json").read_text())
    if hashlib.sha256((base/"evidence.tar.gz").read_bytes()).hexdigest()!=lock["archive_sha256"]:
        raise ValueError("reserved archive checksum mismatch")


def package_bytes():
    manifest=dict(version="dataset-v1",raw_corpus="raw-corpus-v0.1",
        development=dict(runs=30,rows=31,events=90,train_runs=18,validation_runs=6,
            exploratory_runs=6,exploratory_role="Previously explored; excluded from final benchmark"),
        final_test=dict(role="sealed until Day 32",runs=12,source_label_runs=2,
            archive="data/reserved-final-test-v1/evidence.tar.gz",feature_rows_generated=False),
        targets=dict(benign=0,malicious=1),
        policy="Lab-generated data only. Preserve run groups. Fit preprocessing on training only. No reserved-data tuning.",
        files={str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(canonical_bytes(p)).hexdigest() for p in inputs()})
    encoded=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode()
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode="w",format=tarfile.USTAR_FORMAT) as archive:
        for name,data in [("dataset-v1/manifest.json",encoded)]+[("dataset-v1/"+name,canonical_bytes(ROOT/name)) for name in sorted(manifest["files"])]:
            member=tarfile.TarInfo(name)
            member.size=len(data)
            member.mode=0o644
            archive.addfile(member,io.BytesIO(data))
    # RFC 1951 stored blocks with explicit boundaries avoid zlib-version differences.
    raw=buffer.getvalue()
    chunks=[raw[i:i+65535] for i in range(0,len(raw),65535)]
    payload=b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff"
    for i,chunk in enumerate(chunks):
        payload+=bytes([int(i==len(chunks)-1)])+struct.pack("<HH",len(chunk),65535-len(chunk))+chunk
    payload+=struct.pack("<II",zlib.crc32(raw),len(raw) % 2**32)
    return encoded,payload


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    if args.verify:
        hashes=json.loads((args.output/"checksums.json").read_text())
        for name,expected in hashes.items():
            if hashlib.sha256((args.output/name).read_bytes()).hexdigest()!=expected:
                raise ValueError(f"release checksum mismatch: {name}")
        # Replay the archived source version, insulated from future application work.
        with tempfile.TemporaryDirectory() as directory:
            with tarfile.open(args.output/"dataset-v1.tar.gz") as source:
                source.extractall(directory,filter="data")
            archived=Path(directory)/"dataset-v1"
            manifest=json.loads((archived/"manifest.json").read_text())
            if (archived/"manifest.json").read_bytes()!=(args.output/"manifest.json").read_bytes():
                raise ValueError("inner/outer manifest mismatch")
            for name,expected in manifest["files"].items():
                if hashlib.sha256((archived/name).read_bytes()).hexdigest()!=expected:
                    raise ValueError(f"archived source mismatch: {name}")
            rebuilt=Path(directory)/"rebuilt"
            subprocess.run([sys.executable,str(archived/"scripts/package_dataset_v1.py"),str(rebuilt)],cwd=archived,check=True)
            for name in ("manifest.json","dataset-v1.tar.gz","checksums.json"):
                if (rebuilt/name).read_bytes()!=(args.output/name).read_bytes():
                    raise ValueError(f"archived rebuild differs: {name}")
        print("Dataset v1 reproduced from archived pipeline; reserved observations remain sealed")
        return
    verify_sources()
    manifest,archive=package_bytes()
    checksums=(json.dumps({"manifest.json":hashlib.sha256(manifest).hexdigest(),"dataset-v1.tar.gz":hashlib.sha256(archive).hexdigest()},indent=2,sort_keys=True)+"\n").encode()
    payload={"manifest.json":manifest,"dataset-v1.tar.gz":archive,"checksums.json":checksums}
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in payload.items():
        (args.output/name).write_bytes(value)
    print("Dataset v1 package and development rebuild verified; reserved observations remain sealed")


if __name__=="__main__":
    main()
