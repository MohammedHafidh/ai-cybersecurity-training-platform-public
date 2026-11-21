import importlib.util
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

spec = importlib.util.spec_from_file_location("final_package", Path(__file__).resolve().parents[2] / "scripts/package_final_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.mark.parametrize("name", ["../escape", "/absolute", ".env", "backend/.env.local", "private-evidence/log.txt", ".git/config", "key.pem", "demo.db"])
def test_private_and_local_package_paths_are_rejected(name):
    assert not release.safe_path(name)


def test_package_verification_detects_valid_zip_content_tampering(tmp_path):
    archive = tmp_path / "source.zip"
    expected = {name: release.sha(b"source") for name in release.REQUIRED}
    with ZipFile(archive, "w") as package:
        for name in expected:
            package.writestr(name, b"source")
    release.verify_archive(archive, expected)
    with ZipFile(archive, "w") as package:
        for name in expected:
            package.writestr(name, b"altered" if name == "README.md" else b"source")
    with pytest.raises(ValueError, match="Content hash mismatch"):
        release.verify_archive(archive, expected)


def test_package_verification_rejects_extra_local_file(tmp_path):
    archive = tmp_path / "source.zip"
    with ZipFile(archive, "w") as package:
        package.writestr(".env", b"local")
    with pytest.raises(ValueError, match="members differ"):
        release.verify_archive(archive, {})


def test_archive_ignores_windows_checkout_line_conversion(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    git("config", "core.autocrlf", "true")
    (tmp_path / "source.txt").write_bytes(b"first\nsecond\n")
    git("-c", "core.autocrlf=false", "add", "source.txt")
    git("-c", "user.name=Release Test", "-c", "user.email=release@example.invalid", "commit", "-m", "fixture")
    archive = tmp_path / "source.zip"
    release.archive_source(tmp_path, "HEAD", archive)
    with ZipFile(archive) as package:
        assert package.read("source.txt") == b"first\nsecond\n"
