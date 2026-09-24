"""Saved-data §26.16 lesson figures: values, menu states and provenance."""

import hashlib
import importlib
import json
import math
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
FAMILIES = ("payoff", "strip", "replication", "convexity")
SOURCES = (
    "hullkit/src/hullkit/variance_swaps.py",
    "scripts/build_variance_swap_reference.py",
    "docs/validation/section-26-16/reference.json",
    "docs/validation/section-26-16/numerical-check.json",
    "scripts/build_variance_swap_lesson_data.py",
)
KEYS = ["varswap_payoff", "varswap_strip", "varswap_replication", "volswap_convexity"]
STATES = {
    "varswap_payoff": ("payoffs", "difference"),
    "varswap_strip": ("q", "contribution"),
    "varswap_replication": ("absolute", "relative"),
    "volswap_convexity": ("levels", "error"),
}
REFERENCE = json.loads(
    (ROOT / "docs/validation/section-26-16/reference.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def lesson():
    return importlib.import_module("hullkit._variance_swap_lesson")


@pytest.fixture(scope="module")
def figures(lesson):
    return lesson._figures()


@pytest.fixture(scope="module")
def data(lesson):
    return lesson._load_data()


def _trace(fig, role, scenario):
    found = [t for t in fig.data if t.meta["role"] == role and t.meta["scenario"] == scenario]
    assert len(found) == 1, (role, scenario)
    return found[0]


def test_keys_metadata_and_every_menu_state(figures):
    assert list(figures) == KEYS
    for key, fig in figures.items():
        states = STATES[key]
        assert fig.layout.meta["section"] == "26.16"
        assert fig.layout.meta["figure"] == key
        assert fig.layout.meta["scenario"] == states[0]
        buttons = fig.layout.updatemenus[0].buttons
        assert [button.args[1]["meta"]["scenario"] for button in buttons] == list(states)
        for button, state in zip(buttons, states, strict=True):
            visible = button.args[0]["visible"]
            assert any(visible)
            assert visible == [t.meta["scenario"] == state for t in fig.data]
        assert all(t.visible == (t.meta["scenario"] == states[0]) for t in fig.data)


def test_payoff_link_is_tangent_at_the_strike(figures, data):
    fig = figures["varswap_payoff"]
    payload = data["payoff"]["data"]
    assert payload["variance_notional"] == pytest.approx(100.0 / 0.46, rel=1e-15)
    vol = _trace(fig, "volatility-payoff", "payoffs")
    var = _trace(fig, "variance-payoff", "payoffs")
    diff = _trace(fig, "difference", "difference")
    index = list(vol.x).index(0.30)
    assert vol.y[index] == pytest.approx(7.0, abs=1e-12)
    assert var.y[index] == pytest.approx(100.0 / 0.46 * (0.09 - 0.0529), rel=1e-12)
    assert diff.y[index] == pytest.approx(100.0 * 0.07**2 / 0.46, rel=1e-10)
    at_strike = list(vol.x).index(0.23)
    assert vol.y[at_strike] == pytest.approx(0.0, abs=1e-12)
    assert var.y[at_strike] == pytest.approx(0.0, abs=1e-12)
    assert min(diff.y) >= -1e-12


def test_strip_shows_example_26_4_and_its_sum(figures, data):
    fig = figures["varswap_strip"]
    rows = REFERENCE["example_26_4"]["rows"]
    bars = [t for t in fig.data if t.meta["role"].startswith("q-") and t.meta["scenario"] == "q"]
    got = {x: y for t in bars for x, y in zip(t.x, t.y, strict=True)}
    assert got == {row["strike"]: pytest.approx(row["q"], abs=1e-12) for row in rows}
    printed = _trace(fig, "printed-q", "q")
    assert list(printed.y) == [row["printed_q"] for row in rows]
    contribution = [
        t
        for t in fig.data
        if t.meta["role"].startswith("contribution-") and t.meta["scenario"] == "contribution"
    ]
    total = math.fsum(y for t in contribution for y in t.y)
    payload = data["strip"]["data"]
    assert payload["boundary_terms"] + total == pytest.approx(
        payload["expected_variance"], abs=1e-15
    )
    assert payload["expected_variance"] == pytest.approx(0.0621, abs=5e-5)
    kinds = {t.meta["role"] for t in bars}
    assert kinds == {"q-put", "q-average", "q-call"}


def test_replication_error_traces_equal_saved_grids(figures):
    fig = figures["varswap_replication"]
    block = REFERENCE["strip_convergence"]
    for family in block["families"]:
        absolute = _trace(fig, f"strip-error-{family['range']}", "absolute")
        assert list(absolute.x) == [row["delta_k"] for row in family["rows"]]
        assert list(absolute.y) == pytest.approx([row["error"] for row in family["rows"]], abs=0)
        relative = _trace(fig, f"strip-error-{family['range']}", "relative")
        assert list(relative.y) == pytest.approx(
            [100 * row["error"] / block["exact"] for row in family["rows"]], rel=1e-12
        )
    wide = _trace(fig, "strip-error-wide", "absolute")
    assert wide.y[0] / wide.y[1] == pytest.approx(4.0, rel=0.01)
    narrow = _trace(fig, "strip-error-narrow", "absolute")
    assert narrow.y[-1] < 0 < narrow.y[0]


def test_convexity_levels_and_mc_uncertainty(figures):
    fig = figures["volswap_convexity"]
    rows = REFERENCE["volatility_convexity"]["rows"]
    exact = _trace(fig, "exact", "levels")
    approx = _trace(fig, "approximation", "levels")
    naive = _trace(fig, "naive", "levels")
    assert list(exact.y) == pytest.approx(
        [100 * r["exact_expected_volatility"] for r in rows], abs=0
    )
    assert list(approx.y) == pytest.approx([100 * r["approximation"] for r in rows], abs=0)
    assert all(n > e > a for n, e, a in zip(naive.y, exact.y, approx.y, strict=True))
    mc = _trace(fig, "mc-estimate", "levels")
    mc_rows = [r for r in rows if r["mc"] is not None]
    assert list(mc.x) == [r["xi"] for r in mc_rows]
    assert list(mc.error_y.array) == pytest.approx(
        [400 * r["mc"]["sqrt_mean_se"] for r in mc_rows], rel=1e-12
    )
    error = _trace(fig, "approximation-error", "error")
    assert all(y < 0 for y in error.y)
    assert list(error.y) == pytest.approx([100 * r["approximation_error"] for r in rows], abs=0)


def test_source_hashes_are_exact_and_generator_is_reproducible(data):
    for family in FAMILIES:
        assert set(data[family]["source_hashes"]) == set(SOURCES)
        for source in SOURCES:
            expected = hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
            assert data[family]["source_hashes"][source] == expected
    from build_variance_swap_lesson_data import build

    assert build() == data


def test_refuse_stale_hash(lesson, tmp_path):
    data = lesson._load_data()
    data["strip"]["source_hashes"][SOURCES[2]] = "0" * 64
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="stale"):
        lesson._load_data(path)


@pytest.mark.parametrize("family", FAMILIES)
def test_refuse_missing_required_source_hash(lesson, tmp_path, family):
    data = lesson._load_data()
    del data[family]["source_hashes"][SOURCES[0]]
    path = tmp_path / "missing-hash.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=r"missing.*source"):
        lesson._load_data(path)


def test_refuse_deleted_mandatory_source(lesson, tmp_path):
    data_path = tmp_path / "lesson-data.json"
    shutil.copy(ROOT / "docs/validation/section-26-16/lesson-data.json", data_path)
    for source in SOURCES:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / source, target)
    (tmp_path / "scripts/build_variance_swap_reference.py").unlink()
    with pytest.raises(ValueError, match="missing variance-swap lesson source"):
        lesson._load_data(data_path, root=tmp_path)


def test_figure_module_holds_no_numerical_code(lesson):
    """The figure layer reads saved data only: its module globals hold no numerical module."""
    modules = {name for name, value in vars(lesson).items() if isinstance(value, types.ModuleType)}
    assert modules == {"hashlib", "json", "go"}


def test_building_figures_imports_nothing_beyond_plotly():
    """After ``import hullkit``, building the figures loads no pricing or reference code."""
    script = (
        "import sys, hullkit\n"
        "before = set(sys.modules)\n"
        "import hullkit._variance_swap_lesson as m\n"
        "m._figures()\n"
        "print('\\n'.join(sorted(set(sys.modules) - before)))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "PYTHONPATH": str(ROOT / "hullkit/src")},
        capture_output=True,
        text=True,
        check=True,
    )
    loaded = set(completed.stdout.split())
    allowed = ("plotly", "_plotly_utils", "narwhals", "hullkit._variance_swap_lesson")
    assert "hullkit._variance_swap_lesson" in loaded
    assert [name for name in loaded if not name.startswith(allowed)] == []
