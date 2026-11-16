"""Build or query the frozen corpus v1 FAISS index."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.detection.retrieval import Retriever, build_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="generate the FAISS index and row metadata")
    search = commands.add_parser("search", help="retrieve source chunks for a local query")
    search.add_argument("query")
    search.add_argument("--top-k", type=int, default=2)
    args = parser.parse_args()
    if args.command == "build":
        build_index()
    else:
        print(json.dumps(Retriever().search(args.query, args.top_k), indent=2))


if __name__ == "__main__":
    main()
