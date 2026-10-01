"""Stock reset/payment markers, component PVs and constrained MC intervals."""

import importlib
import json

import pytest


def lesson():
    return importlib.import_module("hullkit._cliquet_lesson")


def test_reset_markers_and_stock_price_payments():
    plots = lesson()._figures()
    assert set(plots) == {
        "cliquet_reset",
        "cliquet_components",
        "cliquet_frequency",
        "cliquet_limits",
    }
    data = lesson()._load_reference()["figure"]["reset"]
    roles = {trace.meta["role"]: trace for trace in plots["cliquet_reset"].data}
    for i in range(4):
        assert list(roles[f"strike-{i}"].y) == [data["stock"][i]] * 2
        assert list(roles[f"strike-{i}"].x) == data["time"][i : i + 2]
    payments = roles["payment"]
    assert list(payments.x) == [0.5, 1, 1.5, 2]
    assert list(payments.customdata[0]) == [data["call_payoffs"][0], data["put_payoffs"][0]]


def test_components_and_single_period_frequency():
    plots = lesson()._figures()
    data = lesson()._load_reference()
    roles = {trace.meta["role"]: trace for trace in plots["cliquet_components"].data}
    assert sum(roles["call"].y) == pytest.approx(23.584835778168923, abs=1e-10)
    assert sum(roles["put"].y) == pytest.approx(19.75071882528576, abs=1e-10)
    roles = {trace.meta["role"]: trace for trace in plots["cliquet_frequency"].data}
    assert roles["call"].y[0] == roles["vanilla"].y[0]
    assert roles["call"].x[0] == 1
    assert "S=100" in plots["cliquet_components"].layout.meta["market"]


def test_diagnostic_preserves_standard_errors_and_distinct_market():
    figure = lesson()._figures()["cliquet_limits"]
    mc = next(trace for trace in figure.data if trace.meta["role"] == "mc")
    assert mc.error_y.visible and all(value > 0 for value in mc.error_y.array)
    assert "r=q=0" in figure.layout.meta["market"]


def test_missing_required_source_hash_is_rejected(tmp_path):
    module = lesson()
    record = json.loads(module._RECORD.read_text())
    del record["source_sha256"]["hullkit/src/hullkit/cliquet.py"]
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="source"):
        module._load_reference(path)
