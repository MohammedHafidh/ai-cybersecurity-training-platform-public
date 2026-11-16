"""Score only the committed reserved evidence with the frozen detectors."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.detection.auth_baseline import binary_metrics
from app.detection.scenario_baselines import INPUT_MODELS, detect_scenario_rows
from app.ingestion.corpus import audit_corpus
from app.ingestion.parsers import parsed_lines
from app.ingestion.pipeline import _event_id, load_run_metadata
from app.ingestion.reservation import verify_reservation
from app.ml.frozen_v1 import load_pipeline, predict_observations
from app.processing.modeling import FEATURES, build_modeling_tables


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def evaluate(output):
    if output.exists():
        raise FileExistsError(output)
    reserved = ROOT / "data/reserved-final-test-v1"
    bundle = ROOT / "data/releases/capstone-ml-v1"
    lock = read_json(reserved / "reservation-lock.json")
    rule = read_json(ROOT / "data/processed/day26/freeze-manifest.json")
    model = read_json(bundle / "metadata.json")
    for manifest in (rule, model):
        for path, expected in manifest["source_sha256"].items():
            if sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")) != expected:
                raise ValueError(f"frozen source changed: {path}")
    pipeline = load_pipeline(bundle)
    development = {row["run_id"] for key in ("development_train_manifest",
        "development_validation_manifest", "historical_exploratory_test_manifest")
        for row in read_json(ROOT / lock[key])}
    archive = reserved / "evidence.tar.gz"
    verify_reservation(archive, lock["archive_sha256"], development)
    with TemporaryDirectory() as temp:
        with tarfile.open(archive) as source:
            source.extractall(temp, filter="data")
        base = Path(temp) / "reserved-final-test-v1"
        manifest = base / "manifest.json"
        events, _, quality, provenance = audit_corpus(manifest)
        if any(quality["counts"].get(k, 0) for k in ("parse_error_lines", "unparsed_candidate", "invalid_record")):
            raise ValueError("unresolved evidence quality issue")
        metadata = {r["run_id"]: load_run_metadata(base / r["metadata"]) for r in provenance["runs"]}
        tables = build_modeling_tables(events, metadata)
        locations = {}
        accepted = {event.event_id for event in events}
        for r in provenance["runs"]:
            for line, record, raw, _ in parsed_lines((base / r["log"]).read_text(encoding="utf-8").splitlines(), r["source_type"]):
                event_id = _event_id(r["run_id"], r["log"], line, record, raw)
                if event_id in accepted:
                    locations[event_id] = dict(file=r["log"], line=line, record=record, line_sha256=sha256(raw.encode()))
    if locations.keys() != accepted:
        raise ValueError("missing evidence trace")
    decisions, errors, metrics = [], [], {}
    for source, rows in tables.items():
        schema = INPUT_MODELS[source]
        rule_predictions = {d["row_id"]: d for d in detect_scenario_rows(source, [
            schema(**{k: r[k] for k in schema.model_fields}) for r in rows])}
        ml_predictions = predict_observations(pipeline, [
            {"source_type": source, **{k: r[k] for k in FEATURES[source]}} for r in rows])
        for r, ml in zip(rows, ml_predictions, strict=True):
            d = rule_predictions[r["row_id"]]
            decisions.append(dict(run_id=r["run_id"], row_id=r["row_id"], source=source,
                rule=d["predicted_label"], ml=ml["predicted_label"],
                ml_malicious_probability=ml["malicious_probability"],
                rule_evidence=d["evidence"], event_ids=r["event_ids"]))
    runs = []
    for run, truth in sorted(metadata.items()):
        rows = [d for d in decisions if d["run_id"] == run]
        result = dict(run_id=run, source=rows[0]["source"], truth=truth.expected_label)
        for detector in ("rule", "ml"):
            result[detector] = "malicious" if any(r[detector] == "malicious" for r in rows) else "benign"
            if result[detector] != result["truth"]:
                errors.append(dict(run_id=run, source=result["source"], detector=detector,
                    truth=result["truth"], predicted=result[detector],
                    observations=rows, raw_evidence=[dict(event_id=e, **locations[e])
                        for e in sorted({e for r in rows for e in r["event_ids"]})]))
        runs.append(result)
    for detector in ("rule", "ml"):
        metrics[detector] = {}
        for group in ("overall", *tables):
            selected = [r for r in runs if group == "overall" or r["source"] == group]
            metrics[detector][group] = binary_metrics([r["truth"] for r in selected], [r[detector] for r in selected])
    output.mkdir(parents=True, exist_ok=False)
    report = dict(archive_sha256=lock["archive_sha256"], model_sha256=model["model_sha256"],
        model_version=model["version"], rule_version=rule["version"], thresholds=rule["thresholds"],
        run_aggregation="any malicious observation", metrics=metrics, runs=runs,
        observations=decisions, errors=errors)
    (output / "evaluation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    evaluate(parser.parse_args().output)
