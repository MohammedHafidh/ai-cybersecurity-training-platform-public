from datetime import datetime, timedelta, timezone

import pytest

from app.models.events import NormalizedEvent
from app.models.runs import RunMetadata
from app.processing.network_features import build_network_windows


START = datetime(2026, 10, 22, tzinfo=timezone.utc)


def event(n, seconds=0, **updates):
    data = dict(event_id=str(n), run_id="run", timestamp=START + timedelta(seconds=seconds),
                source_type="network", event_type="tcp_connection", source_ip="172.20.0.2",
                destination_port=8080, protocol="tcp", raw_source_file="network.log",
                attack_label="benign", scenario="benign")
    return NormalizedEvent(**(data | updates))


def context():
    return {"run": RunMetadata(run_id="run", scenario="benign", expected_label="benign",
        start_time=START, end_time=START + timedelta(minutes=3), source="client",
        target="recon-target", tool_or_method="bounded health burst", log_sources=["network.log"])}


def test_half_open_windows_sources_and_rate():
    rows = build_network_windows([event(1), event(2, 59.999999, destination_port=9090),
        event(3, 60), event(4, source_ip="172.20.0.3")], context())
    first = next(row for row in rows if row.connection_count == 2)
    assert first.unique_destination_port_count == 2
    assert first.connections_per_second == 2 / 60
    assert first.window_end == START + timedelta(seconds=60)
    assert len(rows) == 3


def test_equivalent_timezones_and_order_are_deterministic():
    events = [event(1), event(2, 1)]
    changed = events[1].model_copy(update={"timestamp": events[1].timestamp.astimezone(timezone(timedelta(hours=4)))})
    assert build_network_windows(events, context()) == build_network_windows([changed, events[0]], context())


def test_runs_are_never_combined():
    ctx = context()
    ctx["other"] = ctx["run"].model_copy(update={"run_id": "other", "target": "other-target"})
    assert len(build_network_windows([event(1), event(2, run_id="other")], ctx)) == 2


def test_duplicate_ids_fail_but_distinct_same_time_connections_count():
    with pytest.raises(ValueError, match="duplicate"):
        build_network_windows([event(1), event(1)], context())
    assert build_network_windows([event(1), event(2)], context())[0].connection_count == 2


@pytest.mark.parametrize("update", [
    {"source_ip": None}, {"destination_port": None}, {"protocol": None},
    {"timestamp": START.replace(tzinfo=None)}, {"timestamp": START - timedelta(seconds=1)},
    {"attack_label": "malicious"}, {"raw_source_file": "unknown.log"},
])
def test_bad_evidence_fails_closed(update):
    with pytest.raises(ValueError):
        build_network_windows([event(1, **update)], context())


def test_labels_do_not_determine_observed_features():
    benign = build_network_windows([event(1), event(2, destination_port=9090)], context())
    ctx = context()
    ctx["run"] = ctx["run"].model_copy(update={"expected_label": "malicious", "scenario": "reconnaissance"})
    attack = [event(i, destination_port=port, attack_label="malicious", scenario="reconnaissance") for i, port in [(1,8080),(2,9090)]]
    assert benign == build_network_windows(attack, ctx)


@pytest.mark.parametrize("size", [0, -1, True, 1.5, 3601])
def test_invalid_window_size(size):
    with pytest.raises(ValueError):
        build_network_windows([], {}, size)
