import argparse
import json
from pathlib import Path

from app.ingestion.corpus import audit_corpus, freeze_corpus
from app.ingestion.pipeline import load_run_metadata
from app.processing.auth_features import build_auth_windows
from app.processing.network_features import build_network_windows
from app.processing.web_features import build_web_features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        _, _, report, snapshot = audit_corpus(args.manifest)
        frozen = json.loads((args.output / "provenance-manifest.json").read_text())
        if frozen != snapshot:
            raise ValueError("raw corpus differs from frozen manifest")
        print("Frozen raw corpus checksums and provenance verified")
        return
    events, _ = freeze_corpus(args.manifest, args.output)
    entries = json.loads(args.manifest.read_text())["runs"]
    metadata = {}
    for entry in entries:
        run = load_run_metadata(args.manifest.parent / entry["metadata"])
        metadata[run.run_id] = run
    auth = build_auth_windows(events, metadata)
    network = build_network_windows(events, metadata)
    web = build_web_features(events)
    for name, rows in (("auth-windows.json", auth), ("web-features.json", web), ("network-windows.json", [row.model_dump(mode="json") for row in network])):
        (args.output / name).write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    benign_ids = {run.run_id for run in metadata.values() if run.expected_label == "benign"}
    retries = [row for row in auth if row["run_id"] in benign_ids and row["success_after_failure"]]
    if not retries:
        raise ValueError("no real benign retry window validated")
    benign_web = [row for row in web if row["run_id"] in benign_ids]
    if not any(row["suspicious_token_count"] for row in benign_web) or not any(row["missing_input_count"] for row in benign_web):
        raise ValueError("real benign look-alike and missing-input cases required")
    print(f"Frozen corpus validated; {len(retries)} benign retry windows")


if __name__ == "__main__":
    main()
