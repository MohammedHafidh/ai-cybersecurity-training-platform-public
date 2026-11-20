import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/evidence/day60"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_evidence_package_preserves_rc1_and_frozen_hashes():
    for name, expected in read(EVIDENCE / "checksums.json").items():
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == expected
    manifest = read(EVIDENCE / "rc1-manifest.json")
    assert manifest["commit"] == "bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa"
    for name, expected in manifest["artifact_sha256"].items():
        path = ROOT / name
        contents = path.read_text(encoding="utf-8").encode("utf-8") if path.suffix == ".json" else path.read_bytes()
        assert hashlib.sha256(contents).hexdigest() == expected
    trace = read(EVIDENCE / "fallback-trace.json")
    assert trace["evidence_kind"] == "synthetic raw authentication fixture"
    assert trace["run_id"] == "day49-auth-102182a69b03443aa15aab546d884bc0"
    assert len(set(trace["event_ids"])) == trace["observed"] == trace["threshold"] == 3
    assert {row["detector"] for row in trace["predictions"]} == {"rule", "ml"}
    assert (EVIDENCE / trace["screenshot"]).read_bytes().startswith(b"\x89PNG")


def test_final_guide_matches_frozen_metrics_and_links_resolve():
    guide = (ROOT / "docs/final-technical-guide.md").read_text(encoding="utf-8")
    frozen = read(ROOT / "data/processed/day32/evaluation.json")
    for detector, label in (("rule", "Rules"), ("ml", "ML")):
        row = frozen["metrics"][detector]["overall"]
        rates = [f"{row[key]:.1%}" for key in ("accuracy", "precision", "recall", "f1", "false_positive_rate")]
        counts = " / ".join(str(value) for pair in row["confusion_matrix"] for value in pair)
        assert "| " + " | ".join([label, *rates, counts]) + " |" in guide
    docs = [
        ROOT / "README.md", ROOT / "docs/architecture.md",
        ROOT / "docs/final-technical-guide.md", ROOT / "docs/final-lab-reference.md", EVIDENCE / "README.md",
    ]
    for document in docs:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("https://", "#")):
                continue
            assert (document.parent / target).is_file(), (document.name, target)
    refs = read(EVIDENCE / "private-capture-references.json")
    index = (EVIDENCE / "README.md").read_text(encoding="utf-8")
    for capture in refs:
        assert capture["run_id"] in index
        assert capture["expected_label"] == "malicious"
        for entry in capture["files"]:
            assert re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
