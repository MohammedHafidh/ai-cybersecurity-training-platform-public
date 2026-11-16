from sqlalchemy import func, select
from fastapi.testclient import TestClient

from app.detection.comparison import compare_detectors
from app.main import app
from app.ml.evaluation import evaluate_and_select, train_selected_model
from app.ml.inference import inference_request_from_features, load_selected_model
from app.persistence.database import (
    DetectorComparisonRecord,
    FeatureRunRecord,
    MLDetectionRecord,
    RuleDetectionRecord,
    build_engine,
    create_schema,
    session_factory,
)
from app.persistence.repository import get_comparison, save_comparison
from test_ml_training import balanced_rows


client = TestClient(app)


def prepared_comparison(tmp_path):
    rows = balanced_rows()
    report, _ = evaluate_and_select(rows)
    model_path = train_selected_model(rows, report, tmp_path)
    bundle = load_selected_model(
        model_path, tmp_path / "selected-model-metadata.json"
    )
    request = inference_request_from_features(rows[0])
    return request, compare_detectors(bundle, request)


def database(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'day16.db'}")
    create_schema(engine)
    return engine


def test_comparison_is_stored_in_separate_linked_records(tmp_path):
    request, comparison = prepared_comparison(tmp_path)
    engine = database(tmp_path)
    with session_factory(engine)() as session:
        assert save_comparison(session, request, comparison) == comparison
        assert session.scalar(select(func.count()).select_from(FeatureRunRecord)) == 1
        assert session.scalar(select(func.count()).select_from(RuleDetectionRecord)) == 1
        assert session.scalar(select(func.count()).select_from(MLDetectionRecord)) == 1
        assert (
            session.scalar(select(func.count()).select_from(DetectorComparisonRecord))
            == 1
        )


def test_stored_feature_snapshot_has_no_ground_truth(tmp_path):
    request, comparison = prepared_comparison(tmp_path)
    engine = database(tmp_path)
    with session_factory(engine)() as session:
        save_comparison(session, request, comparison)
        run = session.get(FeatureRunRecord, request.run_id)
        assert "attack_label" not in run.observed_features
        assert "scenario" not in run.observed_features


def test_round_trip_reconstructs_complete_comparison(tmp_path):
    request, comparison = prepared_comparison(tmp_path)
    engine = database(tmp_path)
    with session_factory(engine)() as session:
        save_comparison(session, request, comparison)
        assert get_comparison(session, request.run_id) == comparison


def test_identical_save_is_idempotent(tmp_path):
    request, comparison = prepared_comparison(tmp_path)
    engine = database(tmp_path)
    with session_factory(engine)() as session:
        save_comparison(session, request, comparison)
        save_comparison(session, request, comparison)
        assert session.scalar(select(func.count()).select_from(FeatureRunRecord)) == 1


def test_conflicting_comparison_for_run_is_rejected(tmp_path):
    request, comparison = prepared_comparison(tmp_path)
    engine = database(tmp_path)
    with session_factory(engine)() as session:
        save_comparison(session, request, comparison)
        changed = comparison.model_copy(update={"review_recommended": True})
        try:
            save_comparison(session, request, changed)
        except ValueError as exc:
            assert "different stored comparison" in str(exc)
        else:
            raise AssertionError("conflicting comparison was accepted")


def test_api_stores_and_reads_comparison(tmp_path, monkeypatch):
    rows = balanced_rows()
    report, _ = evaluate_and_select(rows)
    model_path = train_selected_model(rows, report, tmp_path)
    metadata_path = tmp_path / "selected-model-metadata.json"
    database_url = f"sqlite:///{tmp_path / 'api.db'}"
    monkeypatch.setenv("ML_MODEL_PATH", str(model_path))
    monkeypatch.setenv("ML_MODEL_METADATA_PATH", str(metadata_path))
    monkeypatch.setenv("DATABASE_URL", database_url)
    request = inference_request_from_features(rows[0])

    stored = client.post("/detections/compare/store", json=request.model_dump())
    assert stored.status_code == 200
    fetched = client.get(f"/detections/comparisons/{request.run_id}")
    assert fetched.status_code == 200
    assert fetched.json() == stored.json()


def test_api_returns_not_found_for_unknown_run(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'empty.db'}"
    engine = build_engine(database_url)
    create_schema(engine)
    monkeypatch.setenv("DATABASE_URL", database_url)
    response = client.get("/detections/comparisons/unknown-run")
    assert response.status_code == 404
