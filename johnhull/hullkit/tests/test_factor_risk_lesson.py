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
