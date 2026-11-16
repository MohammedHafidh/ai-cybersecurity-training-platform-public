import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ingestion.reservation import verify_reservation


def main():
    base = ROOT / "data/reserved-final-test-v1"
    lock = json.loads((base / "reservation-lock.json").read_text())
    development = {row["run_id"] for split in ("train","validation","test") for row in json.loads((ROOT / f"data/processed/day21/{split}.json").read_text())}
    result = verify_reservation(base / "evidence.tar.gz", lock["archive_sha256"], development)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
