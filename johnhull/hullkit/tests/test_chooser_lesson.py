"""Shared plots preserve choice threshold, replication components and MC errors."""

import importlib
import json

import pytest

KEYS = {"chooser_choice", "chooser_package", "chooser_timing", "chooser_validation"}


def lesson():
    return importlib.import_module("hullkit._chooser_lesson")


def test_figures_choice_boundary_and_package():
    figures = lesson()._figures()
    assert set(figures) == KEYS
    assert all(f.layout.meta["section"] == "26.8" for f in figures.values())
    roles = {t.meta["role"]: t for t in figures["chooser_choice"].data}
    assert roles["boundary"].x[0] == pytest.approx(98.51119396030626, abs=1e-10)
    assert roles["chosen"].y[0] == roles["put"].y[0]
    assert roles["chosen"].y[-1] == roles["call"].y[-1]
    roles = {t.meta["role"]: t for t in figures["chooser_package"].data}
    assert roles["chooser"].y[20] == pytest.approx(13.344280448069238, abs=1e-10)
    assert all(
        v == pytest.approx(c + p, abs=1e-10)
        for v, c, p in zip(roles["chooser"].y, roles["call"].y, roles["extra_put"].y, strict=True)
    )


def test_timing_endpoints_and_mc_uncertainty():
    f = lesson()._figures()
    roles = {t.meta["role"]: t for t in f["chooser_timing"].data}
    assert roles["chooser"].y[0] == pytest.approx(roles["immediate"].y[0], abs=1e-10)
    assert roles["chooser"].y[-1] == pytest.approx(roles["straddle"].y[-1], abs=1e-10)
    roles = {t.meta["role"]: t for t in f["chooser_validation"].data}
    assert len(roles["mc"].y) == 4 and roles["mc"].error_y.visible
    assert all(e > 0 for e in roles["mc"].error_y.array)


@pytest.mark.parametrize("mutation", ["source", "artifact"])
def test_hash_guard_rejects_incomplete_sources_and_bad_reference(tmp_path, mutation):
    m = lesson()
    record = json.loads(m._RECORD.read_text())
    if mutation == "source":
        record["source_sha256"].pop("hullkit/src/hullkit/chooser.py")
    else:
        record["artifact_sha256"] = "0" * 64
    p = tmp_path / "record.json"
    p.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        m._load_reference(p)
