import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from app.ingestion.reservation import verify_reservation


def fixture_archive(tmp_path, collision=False):
    # Synthetic metadata-only unit fixture, never presented as real lab evidence.
    files, runs, ids = {}, [], []
    for source, scenario in (("auth","brute_force"),("web","sql_injection"),("network","reconnaissance")):
        for label in ("benign","malicious"):
            for index in range(2):
                run_id = f"reserved-{source}-{label}-{index}"
                ids.append(run_id)
                metadata_name = f"{run_id}.json"
                log_name = f"{run_id}.log"
                files[log_name] = b"unit fixture only"
                files[metadata_name] = json.dumps(dict(run_id=run_id,
                    scenario="benign" if label == "benign" else scenario, expected_label=label,
                    start_time="2026-11-06T00:00:00Z", end_time="2026-11-06T00:01:00Z",
                    source="client", target="lab-target", tool_or_method="fixture", log_sources=[log_name])).encode()
                runs.append(dict(metadata=metadata_name,log=log_name,source_type=source))
    files["manifest.json"] = json.dumps(dict(runs=runs)).encode()
    files["reservation.json"] = json.dumps(dict(protocol_commit="a409025f6023113c4d47de396cda40d8b51e6549",
        protocol_blob="10a60c2daaa432658459405d926cc76fee90c40d", reserved_run_ids=sorted(ids),
        files={name:hashlib.sha256(value).hexdigest() for name,value in files.items()})).encode()
    path = tmp_path / "fixture.tar.gz"
    with tarfile.open(path,"w:gz") as target:
        for name,value in files.items():
            member = tarfile.TarInfo("reserved-final-test-v1/" + name)
            member.size = len(value)
            target.addfile(member,io.BytesIO(value))
    return path, hashlib.sha256(path.read_bytes()).hexdigest(), ids


def test_metadata_integrity_and_isolation_without_detectors(tmp_path):
    archive, digest, ids = fixture_archive(tmp_path)
    result = verify_reservation(archive,digest,{"development-run"})
    assert result["run_count"] == 12
    assert not result["detector_evaluated"]
    with pytest.raises(ValueError,match="collision"):
        verify_reservation(archive,digest,{ids[0]})
    with pytest.raises(ValueError,match="checksum"):
        verify_reservation(archive,"0"*64,set())
