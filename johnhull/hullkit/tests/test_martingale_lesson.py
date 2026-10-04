"""Consumer rejects result corruption before showing conditional or pricing figures."""

import importlib
import json

import pytest

KEYS = {
    "martingale_ito",
    "martingale_conditional",
    "martingale_conditional_mc",
    "martingale_pricing",
}


def test_four_figures_and_conditional_error_bars():
    m = importlib.import_module("hullkit._martingale_lesson")
    figures = m._figures()
    assert set(figures) == KEYS
    assert list(figures["martingale_ito"].data[0].y) == pytest.approx([-0.1, 0.04, 0.06, 0])
    assert len(figures["martingale_conditional_mc"].data[0].error_y.array) == 9
    assert len(figures["martingale_pricing"].data[0].error_y.array) == 4


@pytest.mark.parametrize(
    "mutation",
    [
        "status",
        "reference hash",
        "source missing",
        "api changed",
        "api missing",
        "mc changed",
        "pricing changed",
        "result hash",
    ],
)
def test_consumer_rejects_bad_evidence(tmp_path, monkeypatch, mutation):
    m = importlib.import_module("hullkit._martingale_lesson")
    record = json.loads(m._RECORD.read_text())
    if mutation == "status":
        record["status"] = "FAIL"
    elif mutation == "reference hash":
        record["artifact_sha256"] = "0" * 64
    elif mutation == "source missing":
        del record["source_sha256"]["hullkit/src/hullkit/_martingales.py"]
    elif mutation == "api changed":
        record["api_conditional_means"][0] += 0.6
    elif mutation == "api missing":
        del record["api_conditional_means"]
    elif mutation == "mc changed":
        record["conditional_mc"][0]["mean"] += 0.6
    elif mutation == "pricing changed":
        record["pricing"][0]["mean"] += 6
    else:
        record["result_sha256"] = "0" * 64
    bad = tmp_path / "record.json"
    bad.write_text(json.dumps(record))
    monkeypatch.setattr(m, "_RECORD", bad)
    with pytest.raises(ValueError):
        m._figures()
