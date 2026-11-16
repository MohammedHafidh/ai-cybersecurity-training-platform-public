"""Build or verify the frozen Day 45 explanation corpus without network access."""
import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1] / "data/knowledge/day45"
SCENARIOS = {"brute_force", "sql_injection", "reconnaissance"}
MAX_WORDS = 120


def source_sections(text):
    title, *sections = re.split(r"^## ", text, flags=re.MULTILINE)
    if not title.startswith("# ") or len(title.strip().splitlines()) != 1 or not sections:
        raise ValueError("each source needs one title and at least one section")
    seen = set()
    for section in sections:
        heading, _, body = section.partition("\n")
        words = body.split()
        if not heading.strip() or heading in seen or not words:
            raise ValueError("section headings must be unique and nonempty, with body text")
        seen.add(heading)
        for start in range(0, len(words), MAX_WORDS):
            yield heading, " ".join(words[start:start + MAX_WORDS])


def build_corpus(root=ROOT):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    sources = manifest["sources"]
    expected = {f"{scenario}.md" for scenario in SCENARIOS}
    actual = {path.name for path in (root / "sources").iterdir()}
    if (manifest["version"] != "v1" or len(sources) != len(SCENARIOS)
            or {source["scenario"] for source in sources} != SCENARIOS or actual != expected):
        raise ValueError("source inventory must match the frozen three-scenario manifest")

    chunks = []
    for source in sorted(sources, key=lambda item: item["scenario"]):
        scenario = source["scenario"]
        path = root / "sources" / f"{scenario}.md"
        if path.is_symlink():
            raise ValueError("frozen sources must be regular corpus files")
        text = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != source["sha256"]:
            raise ValueError(f"frozen source hash mismatch for {scenario}")
        for index, (heading, body) in enumerate(source_sections(text), 1):
            chunks.append({
                "chunk_id": f"v1:{scenario}:{index:02d}",
                "scenario": scenario,
                "source_path": f"sources/{scenario}.md",
                "source_title": source["title"],
                "source_sha256": digest,
                "references": source["references"],
                "section": heading,
                "text": body,
            })
    return {
        "version": manifest["version"],
        "purpose": manifest["purpose"],
        "chunks": chunks,
    }


def serialize(corpus):
    return json.dumps(corpus, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the committed chunk snapshot")
    args = parser.parse_args()
    output = ROOT / "chunks.json"
    generated = serialize(build_corpus())
    if args.check:
        if output.read_text(encoding="utf-8") != generated:
            parser.exit(1, "Frozen Day 45 chunks do not reproduce.\n")
        print("Frozen Day 45 corpus verified")
    else:
        output.write_text(generated, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
