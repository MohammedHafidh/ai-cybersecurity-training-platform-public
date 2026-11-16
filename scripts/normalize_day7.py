import argparse
from pathlib import Path

from app.ingestion.pipeline import normalize_manifest, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize trusted lab evidence")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    events = normalize_manifest(args.manifest)
    write_jsonl(events, args.output)
    print(f"wrote {len(events)} normalized events to {args.output}")


if __name__ == "__main__":
    main()

