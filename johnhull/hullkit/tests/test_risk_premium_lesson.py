"""Shared figures require current independent evidence and cover signed risks."""

import importlib
import json

import pytest

KEYS = {
    "risk_premium_loading",
    "risk_premium_hedge",
    "risk_premium_density",
    "risk_premium_validation",
}


def lesson():
    return importlib.import_module("hullkit._risk_premium_lesson")


def test_four_figures_and_raw_paired_mc_error_bars():
    figures = lesson()._figures()
    assert set(figures) == KEYS
    for key, fig in figures.items():
        assert fig.layout.meta["section"] == "28.1" and fig.layout.meta["figure"] == key
    density = figures["risk_premium_density"]
    assert list(density.data[1].y) == pytest.approx(list(density.data[2].y), abs=1e-13)
    validation = figures["risk_premium_validation"]
    ref = json.loads(lesson()._DATA.read_text())
    for trace, field in zip(validation.data[:2], ("weighted_se", "direct_se"), strict=True):
        assert list(trace.error_y.array) == pytest.approx(
            [1.959963984540054 * r[field] for r in ref["mc"]]
        )


@pytest.mark.parametrize("tamper", ["missing hash", "wrong hash", "reference hash", "status"])
def test_stale_or_incomplete_evidence_is_rejected(tmp_path, tamper):
    m = lesson()
    record = json.loads(m._RECORD.read_text())
    if tamper == "missing hash":
        del record["source_sha256"]["hullkit/src/hullkit/sde.py"]
    elif tamper == "wrong hash":
        record["source_sha256"]["hullkit/src/hullkit/risk_premium.py"] = "0" * 64
    elif tamper == "reference hash":
        record["artifact_sha256"] = "0" * 64
    else:
        record["status"] = "FAIL"
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        m._load_reference(path)
