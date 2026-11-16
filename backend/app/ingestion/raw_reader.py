from pathlib import Path


def read_raw_log(path: Path) -> list[str]:
    """Read a raw log without modifying it."""
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").splitlines()
