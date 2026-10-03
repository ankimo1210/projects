"""Shared plots must retain signed pins and reject stale or incomplete evidence."""

import importlib
import json

import pytest

KEYS = {
    "factor_risk_contributions",
    "factor_risk_loading",
    "factor_risk_hedge",
    "factor_risk_validation",
}


def test_shared_figures_show_signed_excess_pin_and_total_risk_free_hedge():
    m = importlib.import_module("hullkit._factor_risk_lesson")
    plots = m._figures()
    assert set(plots) == KEYS
    assert list(plots["factor_risk_contributions"].data[0].y) == pytest.approx(
        [0.01, -0.01, 0.06, 0.06]
    )
    for key, f in plots.items():
        assert f.layout.meta["section"] == "28.2" and f.layout.meta["figure"] == key
        assert f.layout.height == 540
    assert plots["factor_risk_hedge"].layout.shapes[0].y0 == pytest.approx(0.04)
    assert len(plots["factor_risk_validation"].data) == 2


@pytest.mark.parametrize("mutation", ["status", "artifact", "source", "missing source"])
def test_shared_figure_loader_rejects_bad_evidence(tmp_path, mutation):
    m = importlib.import_module("hullkit._factor_risk_lesson")
    record = json.loads(m._RECORD.read_text())
    if mutation == "status":
        record["status"] = "FAIL"
    elif mutation == "artifact":
        record["artifact_sha256"] = "0" * 64
    elif mutation == "source":
        record["source_sha256"]["hullkit/src/hullkit/factor_risk.py"] = "0" * 64
    else:
        del record["source_sha256"]["hullkit/src/hullkit/risk_premium.py"]
    bad = tmp_path / "record.json"
    bad.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        m._load_reference(bad)


@pytest.mark.parametrize(
    "mutation",
    [
        "changed",
        "missing",
        "short",
        "long",
        "nan",
        "inf",
        "negative inf",
        "nested",
        "string",
        "bool",
        "null",
    ],
)
def test_figure_consumer_rejects_invalid_saved_api_results(tmp_path, monkeypatch, mutation):
    m = importlib.import_module("hullkit._factor_risk_lesson")
    record = json.loads(m._RECORD.read_text())
    values = record["api_excess_returns"]
    if mutation == "changed":
        values[0] += 0.6
    elif mutation == "missing":
        del record["api_excess_returns"]
    elif mutation == "short":
        values.pop()
    elif mutation == "long":
        values.append(0.0)
    else:
        values[0] = {
            "nan": float("nan"),
            "inf": float("inf"),
            "negative inf": -float("inf"),
            "nested": [values[0]],
            "string": str(values[0]),
            "bool": True,
            "null": None,
        }[mutation]
    bad = tmp_path / "record.json"
    bad.write_text(json.dumps(record))
    monkeypatch.setattr(m, "_RECORD", bad)
    with pytest.raises(ValueError, match="API results"):
        m._figures()


def test_figure_consumer_reads_numerical_record_once(monkeypatch):
    m = importlib.import_module("hullkit._factor_risk_lesson")
    original = m.Path.read_text
    reads = []

    def read(path, *args, **kwargs):
        if path == m._RECORD:
            reads.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(m.Path, "read_text", read)
    figure = m._figures()["factor_risk_validation"]
    assert list(figure.data[1].y) == pytest.approx(list(figure.data[0].y), abs=1e-12)
    assert len(reads) == 1
