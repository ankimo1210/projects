"""Shared plots keep signed loadings, the riskless residual and MC errors (§28.1)."""

import importlib
import json

import pytest

KEYS = {"mpr_line", "mpr_riskless", "mpr_worlds", "mpr_validation"}


def lesson():
    return importlib.import_module("hullkit._market_price_of_risk_lesson")


def test_line_points_sit_on_slope_lambda_with_negative_put_loadings():
    figures = lesson()._figures()
    assert set(figures) == KEYS
    assert all(f.layout.meta["section"] == "28.1" for f in figures.values())
    claims = [t for t in figures["mpr_line"].data if t.meta["role"] == "claims"]
    assert len(claims) == 2 and sum(len(t.x) for t in claims) == 38
    for trace in claims:
        lam = trace.meta["market_lambda"]
        assert all(
            y == pytest.approx(lam * x, abs=1e-9) for x, y in zip(trace.x, trace.y, strict=True)
        )
        assert min(trace.x) < 0 < max(trace.x)
    example = next(t for t in figures["mpr_line"].data if t.meta["role"] == "example")
    assert list(example.y) == pytest.approx([-0.03, -0.045])


def test_riskless_residual_shrinks_and_worlds_share_width():
    f = lesson()._figures()
    for trace in (t for t in f["mpr_riskless"].data if t.meta["role"] == "pair"):
        assert list(trace.y) == sorted(trace.y, reverse=True)
    densities = [t for t in f["mpr_worlds"].data if t.meta["role"] == "density"]
    assert max(max(t.y) for t in densities) == pytest.approx(
        min(max(t.y) for t in densities), rel=1e-3
    )
    bars = [t for t in f["mpr_validation"].data if t.type == "bar"]
    assert len(bars) == 2 and all(t.error_y.visible and len(t.y) == 4 for t in bars)


@pytest.mark.parametrize("mutation", ["source", "artifact"])
def test_hash_guard_rejects_incomplete_sources_and_bad_reference(tmp_path, mutation):
    m = lesson()
    record = json.loads(m._RECORD.read_text())
    if mutation == "source":
        record["source_sha256"].pop("hullkit/src/hullkit/market_price_of_risk.py")
    else:
        record["artifact_sha256"] = "0" * 64
    p = tmp_path / "record.json"
    p.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        m._load_reference(p)
