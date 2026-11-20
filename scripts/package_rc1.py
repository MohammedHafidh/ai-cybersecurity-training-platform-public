"""Archive the checked-out release candidate and record its commit and artifact hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/release-candidate")
    args = parser.parse_args()
    if git("status", "--porcelain", "--untracked-files=no").strip():
        parser.exit(1, "Commit tracked changes before packaging RC1.\n")
    commit = git("rev-parse", "HEAD").decode().strip()
    output = args.output.resolve()
    if output == ROOT:
        parser.exit(1, "Use a dedicated output directory.\n")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "rc1-source.zip"
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=zip", "-o", str(archive), commit], check=True)
    paths = [
        "data/processed/day32/evaluation.json",
        "data/processed/day56/provenance.json",
        "data/releases/capstone-ml-v1/pipeline.joblib",
        "data/knowledge/day45/chunks.json",
        "data/knowledge/day46/index.faiss",
    ]
    manifest = {
        "release_candidate": "RC1",
        "commit": commit,
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "tracked_file_count": len(git("ls-tree", "-r", "--name-only", commit).splitlines()),
        "artifact_sha256": {
            path: hashlib.sha256(git("show", f"{commit}:{path}")).hexdigest() for path in paths
        },
        "verification": "See the successful GitHub Actions run for this exact commit.",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )
    print(f"RC1 source and manifest prepared for {commit}")


if __name__ == "__main__":
    main()
