"""Integrity-only access to reserved evidence; never produces model inputs."""
from collections import Counter
import hashlib
import json
from pathlib import PurePosixPath
import tarfile

from app.models.runs import RunMetadata
from app.ingestion.validation import validate_run_metadata


def verify_reservation(archive, expected_sha256, development_ids):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("reserved archive checksum mismatch")
    prefix = "reserved-final-test-v1/"
    with tarfile.open(archive) as source:
        members = {}
        for member in source.getmembers():
            if member.isdir():
                continue
            if not member.isfile() or not member.name.startswith(prefix) or ".." in PurePosixPath(member.name).parts:
                raise ValueError("unsafe reserved archive member")
            if member.name in members:
                raise ValueError("duplicate archive member")
            members[member.name] = member

        def read(name):
            return source.extractfile(members[prefix + name]).read()

        reservation = json.loads(read("reservation.json"))
        if reservation["protocol_commit"] != "a409025f6023113c4d47de396cda40d8b51e6549" or reservation["protocol_blob"] != "10a60c2daaa432658459405d926cc76fee90c40d":
            raise ValueError("reservation protocol mismatch")
        for name, expected in reservation["files"].items():
            if hashlib.sha256(read(name)).hexdigest() != expected:
                raise ValueError("reserved source hash mismatch")
        manifest = json.loads(read("manifest.json"))
        ids, counts = set(), Counter()
        for entry in manifest["runs"]:
            run = RunMetadata.model_validate_json(read(entry["metadata"]))
            if validate_run_metadata(run) or run.status != "valid":
                raise ValueError("invalid reserved metadata")
            if run.run_id in ids or run.run_id in development_ids:
                raise ValueError("reserved/development identity collision")
            if entry["log"] not in run.log_sources:
                raise ValueError("primary evidence not declared")
            ids.add(run.run_id)
            counts[f"{entry['source_type']}:{run.expected_label}"] += 1
        expected_counts = {f"{s}:{l}":2 for s in ("auth","web","network") for l in ("benign","malicious")}
        if counts != expected_counts or sorted(ids) != reservation["reserved_run_ids"]:
            raise ValueError("reserved coverage/membership mismatch")
        return dict(run_count=len(ids), source_label_run_counts=dict(counts),
            archive_sha256=expected_sha256, integrity_verified=True,
            detector_evaluated=False, purpose="Reserved for Day 32")
