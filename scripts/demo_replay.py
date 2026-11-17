"""Replay one synthetic authentication log through the local demo API."""
import argparse
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/tests")]
from auth_browser_capture import synthetic_capture


def request(path, payload=None, *, post=False):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    message = Request(
        "http://127.0.0.1:8000" + path, data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if post else "GET",
    )
    with urlopen(message, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rag", action="store_true", help="also verify the enabled local explanation service")
    options = parser.parse_args()
    stage = "database readiness"
    try:
        request("/health/database")
        capture = synthetic_capture()
        run = capture["run"]["run_id"]
        stage = "ingestion"
        request("/ingestion/runs", capture, post=True)
        stage = "detection processing"
        result = request(f"/runs/{run}/process", post=True)
        stage = "saved prediction readback"
        details = [request(f"/detections/{key}") for key in result["detection_ids"]]
        expected = {event["event_id"] for event in capture["events"]}
        if {row["detector"] for row in details} != {"rule", "ml"} or any(
            row["run_id"] != run or set(row["evidence"]["event_ids"]) != expected for row in details
        ):
            raise SystemExit("Saved detector results did not match the demo run.")
        if options.rag:
            stage = "local RAG"
            rule = next(row for row in details if row["detector"] == "rule")
            explanation = request(f"/detections/{rule['detection_id']}/rag-explanation?question=why_suspicious")
            if explanation["status"] != "grounded" or not explanation["sources"]:
                raise SystemExit("The demo explanation did not return trusted sources.")
            if [request(f"/detections/{row['detection_id']}") for row in details] != details:
                raise SystemExit("The saved detections changed during explanation.")
            print(f"Grounded explanation returned {len(explanation['sources'])} source(s).")
    except (HTTPError, URLError, TimeoutError) as error:
        raise SystemExit(f"Demo failed during {stage}: {error}") from None
    print(f"Run {run}: " + ", ".join(f"{row['detector']}={row['predicted_label']}" for row in details))


if __name__ == "__main__":
    main()
