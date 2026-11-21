"""Create and verify a tracked-source submission archive; no local files are copied."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "v1.0.0"
ARTIFACTS = (
    "data/processed/day32/evaluation.json",
    "data/processed/day56/provenance.json",
    "data/releases/capstone-ml-v1/pipeline.joblib",
    "data/knowledge/day45/chunks.json",
    "data/knowledge/day46/index.faiss",
    "docs/evidence/day60/rc1-manifest.json",
)
REQUIRED = (*ARTIFACTS, "README.md", "compose.demo.yml", "backend/requirements.txt",
            "frontend/package-lock.json", "docs/final-technical-guide.md",
            "docs/architecture.md", "docs/day61-defense-demo.md",
            "docs/day62-submission-checklist.md", "docs/day63-final-release.md",
            "docs/evidence/day60/fallback-evidence.png")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def sha(contents):
    return hashlib.sha256(contents).hexdigest()


def archive_source(root, commit, archive):
    # git archive otherwise honors the machine's core.autocrlf setting.
    subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                    "-C", str(root), "archive", "--format=zip", "-o", str(archive), commit], check=True)


def safe_path(name):
    path = PurePosixPath(name)
    blocked = {".git", ".venv", "node_modules", "private-evidence", "__pycache__", "test-results"}
    return (not path.is_absolute() and ".." not in path.parts
            and not blocked.intersection(path.parts)
            and not (path.name.startswith(".env") and path.name != ".env.example")
            and path.suffix.lower() not in {".pem", ".key", ".db", ".pyc"})


def verify_archive(archive, expected):
    with ZipFile(archive) as package:
        names = package.namelist()
        files = {name for name in names if not name.endswith("/")}
        if len(names) != len(set(names)) or files != set(expected):
            raise ValueError("Archive members differ from the tracked source")
        if not all(safe_path(name) for name in names):
            raise ValueError("Unsafe archive member")
        if not set(REQUIRED).issubset(files) or package.testzip() is not None:
            raise ValueError("Missing or corrupt release content")
        for name in files:
            if sha(package.read(name)) != expected[name]:
                raise ValueError(f"Content hash mismatch: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/final-release")
    args = parser.parse_args()
    if git("status", "--porcelain", "--untracked-files=no").strip():
        parser.exit(1, "Commit tracked changes before packaging.\n")
    commit = git("rev-parse", "HEAD").decode().strip()
    files = git("ls-tree", "-rz", "--name-only", commit).decode().split("\0")[:-1]
    if not all(safe_path(name) for name in files):
        parser.exit(1, "Unsafe tracked source path.\n")
    hashes = {name: sha(git("show", f"{commit}:{name}")) for name in files}
    output = args.output.resolve()
    if output == ROOT:
        parser.exit(1, "Use a dedicated output directory.\n")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"capstone-{RELEASE}-source.zip"
    archive_source(ROOT, commit, archive)
    verify_archive(archive, hashes)
    manifest = {
        "release": RELEASE, "commit": commit,
        "tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
        "rc1_commit": "bc7e7c15cfeb9ab89b1dc8d757f7962aba70ceaa",
        "archive": archive.name, "archive_sha256": sha(archive.read_bytes()),
        "file_count": len(files), "files_sha256": hashes,
        "artifact_sha256": {name: hashes[name] for name in ARTIFACTS},
        "integrity": "ZIP CRC and every tracked member SHA-256 verified",
        "privacy": "Tracked public source only; credential-pattern review is not an absolute guarantee",
        "verification": "Required verify, postgres and retrieval jobs for this exact commit must pass before tagging",
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    deliverables = (archive, manifest_path)
    sums = output / "SHA256SUMS"
    sums.write_text("".join(f"{sha(path.read_bytes())}  {path.name}\n" for path in deliverables), encoding="utf-8", newline="\n")
    for line in sums.read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert sha((output / name).read_bytes()) == expected
    print(f"Verified {RELEASE} source package for {commit}: {manifest['archive_sha256']}")


if __name__ == "__main__":
    main()
