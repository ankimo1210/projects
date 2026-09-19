"""Semantic figure tests for the saved-data Hull §26.15 basket lesson.

Every numerical claim is recomputed from the frozen M7a reference rows or
from literal terminal values. The lesson JSON never defines its own expected
values here.
"""

import hashlib
import importlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRICES = json.loads((ROOT / "docs/validation/section-26-15/prices.json").read_text())
KEYS = ["basket_payoff", "basket_correlation", "basket_comparison", "basket_error"]
FAMILIES = ["payoff", "correlation", "comparison", "error"]
SOURCES = [
    "hullkit/src/hullkit/exotics.py",
    "scripts/build_basket_reference.py",
    "docs/validation/section-26-15/prices.json",
    "docs/validation/section-26-15/numerical-check.json",
    "scripts/build_basket_lesson_data.py",
]
CORRELATION_MARKETS = ["negative-correlation", "baseline", "high-correlation"]
COMPARISON_STATES = ["baseline-call", "long-high-volatility-call", "baseline-put"]
ERROR_MARKETS = [
    "baseline",
    "long-high-volatility",
    "three-diversified",
    "three-high-volatility",
]


@pytest.fixture(scope="module")
def lesson():
    return importlib.import_module("hullkit._basket_lesson")


@pytest.fixture(scope="module")
def figures(lesson):
    return lesson._figures()


@pytest.fixture(scope="module")
def data(lesson):
    return lesson._load_data()


def _trace(fig, role, scenario):
    return next(
        item for item in fig.data if item.meta["role"] == role and item.meta["scenario"] == scenario
    )


def _frozen(market, strike, kind):
    return next(
        row
        for row in PRICES["rows"]
        if row["market"] == market and row["K"] == strike and row["kind"] == kind
    )


def test_keys_metadata_roles_and_every_menu_state(figures):
    """Dropping a shared figure, state, or semantic role breaks both delivery surfaces."""
    assert list(figures) == KEYS
    for key, fig in figures.items():
        assert fig.layout.meta["section"] == "26.15"
        assert fig.layout.meta["figure"] == key
        assert fig.layout.meta["scenario"]
        assert fig.layout.meta["units"]["money"] == "currency"
        assert fig.layout.updatemenus
        states = []
        for button in fig.layout.updatemenus[0].buttons:
            visibility, layout = button.args
            state = layout["meta"]["scenario"]
            states.append(state)
            assert layout["meta"]["section"] == "26.15"
            assert layout["meta"]["figure"] == key
            assert visibility["visible"] == [item.meta["scenario"] == state for item in fig.data]
        assert len(states) == len(set(states)) >= 2
        assert fig.layout.meta["scenario"] == states[0]
        assert [bool(item.visible) for item in fig.data] == [
            item.meta["scenario"] == states[0] for item in fig.data
        ]
        assert all(item.meta["role"] for item in fig.data)


def test_payoff_uses_literal_two_asset_terminal_values(figures, data):
    """Replacing a positive holding by zero or plotting a one-asset payoff must fail."""
    payload = data["payoff"]["data"]
    weights = payload["weights"]
    strike = payload["strike"]
    assert weights == [0.6, 0.5]
    assert all(weight > 0.0 for weight in weights)
    assert all(len(row["terminal_assets"]) == 2 for row in payload["rows"])
    for row in payload["rows"]:
        basket = sum(
            weight * terminal
            for weight, terminal in zip(weights, row["terminal_assets"], strict=True)
        )
        assert row["basket_terminal"] == pytest.approx(basket)
        assert row["call"] == pytest.approx(max(basket - strike, 0.0))
        assert row["put"] == pytest.approx(max(strike - basket, 0.0))

    otm = next(
        row for row in payload["rows"] if row["call"] == 0.0 and row["basket_terminal"] < strike
    )
    assert weights[1] * otm["terminal_assets"][1] > 0.0
    assert weights[1] * otm["terminal_assets"][1] != otm["call"]

    fig = figures["basket_payoff"]
    baskets = [row["basket_terminal"] for row in payload["rows"]]
    for kind in ("call", "put"):
        assert list(_trace(fig, "basket-terminal", kind).y) == pytest.approx(baskets)
        assert list(_trace(fig, "payoff", kind).y) == pytest.approx(
            [row[kind] for row in payload["rows"]]
        )


def test_correlation_uses_otherwise_identical_frozen_markets(figures, data):
    """Changing anything besides rho would make the correlation comparison misleading."""
    entries = data["correlation"]["data"]["entries"]
    assert [entry["market"] for entry in entries] == CORRELATION_MARKETS
    first = entries[0]
    fixed = ("spots", "weights", "volatilities", "dividends", "rate", "expiry")
    for entry in entries[1:]:
        assert {key: entry[key] for key in fixed} == {key: first[key] for key in fixed}

    for entry in entries:
        rho = entry["rho"]
        forwards = [
            weight * spot * math.exp((entry["rate"] - dividend) * entry["expiry"])
            for spot, weight, dividend in zip(
                entry["spots"],
                entry["weights"],
                entry["dividends"],
                strict=True,
            )
        ]
        expected_cross_covariance = (
            2.0
            * forwards[0]
            * forwards[1]
            * math.expm1(
                rho * entry["volatilities"][0] * entry["volatilities"][1] * entry["expiry"]
            )
        )
        frozen = _frozen(entry["market"], 100.0, "call")
        expected_volatility = math.sqrt(math.log(frozen["M2"] / frozen["M1"] ** 2) / frozen["T"])
        assert entry["cross_covariance_contribution"] == pytest.approx(
            expected_cross_covariance, abs=1e-12
        )
        assert entry["matched_volatility"] == pytest.approx(expected_volatility, abs=1e-12)

    fig = figures["basket_correlation"]
    assert list(_trace(fig, "cross-covariance", "all").x) == pytest.approx(
        [entry["rho"] for entry in entries]
    )
    assert list(_trace(fig, "cross-covariance", "all").y) == pytest.approx(
        [entry["cross_covariance_contribution"] for entry in entries]
    )
    assert list(_trace(fig, "matched-volatility", "all").y) == pytest.approx(
        [100.0 * entry["matched_volatility"] for entry in entries]
    )


def test_comparison_separates_proxy_reference_and_mc_uncertainty(figures, data):
    """Merging the independent value or its MC uncertainty into the proxy must fail."""
    assert [family["scenario"] for family in data["comparison"]["data"]] == COMPARISON_STATES
    fig = figures["basket_comparison"]
    for family in data["comparison"]["data"]:
        state = family["scenario"]
        frozen = [
            _frozen(family["market"], strike, family["kind"]) for strike in (80.0, 100.0, 120.0)
        ]
        assert all(row["reference_method"] == "conditional_quadrature" for row in frozen)
        approximation = _trace(fig, "approximation", state)
        independent = _trace(fig, "independent-reference", state)
        mc = _trace(fig, "mc-estimate", state)
        assert list(approximation.x) == [80.0, 100.0, 120.0]
        assert list(approximation.y) == pytest.approx([row["approximation"] for row in frozen])
        assert list(independent.y) == pytest.approx([row["reference"] for row in frozen])
        assert list(mc.y) == pytest.approx([row["mc"] for row in frozen])
        assert list(mc.error_y.array) == pytest.approx(
            [4.0 * row["standard_error"] for row in frozen]
        )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_error_figure_uses_absolute_relative_gap_and_marks_unresolved_sign(figures, data, kind):
    """An MC-sized gap may be drawn, but its positive/negative sign is not evidence."""
    family = next(item for item in data["error"]["data"] if item["scenario"] == kind)
    assert [entry["market"] for entry in family["entries"]] == ERROR_MARKETS
    fig = figures["basket_error"]
    established = _trace(fig, "absolute-relative-gap-established", kind)
    unresolved = _trace(fig, "absolute-relative-gap-unresolved", kind)
    uncertainty = _trace(fig, "four-se-relative-uncertainty", kind)
    assert "絶対" in fig.layout.yaxis.title.text
    assert "符号未確定" in unresolved.name

    frozen = [_frozen(market, 100.0, kind) for market in ERROR_MARKETS]
    established_expected = {
        row["market"]: 100.0 * abs(row["approximation"] - row["reference"]) / abs(row["reference"])
        for row in frozen
        if row["error_sign_established"]
    }
    unresolved_expected = {
        row["market"]: 100.0 * abs(row["approximation"] - row["reference"]) / abs(row["reference"])
        for row in frozen
        if not row["error_sign_established"]
    }
    assert dict(zip(established.x, established.y, strict=True)) == pytest.approx(
        established_expected
    )
    assert dict(zip(unresolved.x, unresolved.y, strict=True)) == pytest.approx(unresolved_expected)
    assert dict(zip(uncertainty.x, uncertainty.y, strict=True)) == pytest.approx(
        {
            row["market"]: 100.0 * 4.0 * row["standard_error"] / abs(row["reference"])
            for row in frozen
        }
    )

    diversified = next(
        entry for entry in family["entries"] if entry["market"] == "three-diversified"
    )
    assert diversified["absolute_gap"] == pytest.approx(0.01447026213114, abs=1e-13)
    assert diversified["four_standard_errors"] == pytest.approx(0.01830017469260, abs=1e-13)
    assert diversified["absolute_gap"] < diversified["four_standard_errors"]
    assert diversified["error_sign_established"] is False
    assert "three-diversified" in unresolved.x


def test_source_hashes_are_exact_and_generator_is_reproducible(lesson, data):
    """Every claim source, including the lesson generator itself, stays pinned."""
    for family in FAMILIES:
        assert set(data[family]["source_hashes"]) == set(SOURCES)
        for source in SOURCES:
            expected = hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
            assert data[family]["source_hashes"][source] == expected

    from build_basket_lesson_data import build

    assert build() == data


def test_refuse_stale_hash(lesson, tmp_path):
    """A changed pricing API invalidates every saved-data figure."""
    data = lesson._load_data()
    data["comparison"]["source_hashes"]["hullkit/src/hullkit/exotics.py"] = "0" * 64
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="stale"):
        lesson._load_data(path)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("source", SOURCES)
def test_refuse_missing_required_source_hash(lesson, tmp_path, family, source):
    """Omitting one mandatory provenance edge invalidates the artifact."""
    data = lesson._load_data()
    del data[family]["source_hashes"][source]
    path = tmp_path / "missing-hash.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=r"missing.*source"):
        lesson._load_data(path)


def test_refuse_deleted_mandatory_source(lesson, tmp_path):
    """A hash cannot bless a source file that no longer exists."""
    data = lesson._load_data()
    data_path = tmp_path / "lesson-data.json"
    data_path.write_text(json.dumps(data))
    for source in SOURCES:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / source).read_bytes())
    (tmp_path / "scripts/build_basket_reference.py").unlink()
    with pytest.raises(ValueError, match=r"missing.*source"):
        lesson._load_data(data_path, root=tmp_path)


def test_figures_never_run_pricing_quadrature_or_monte_carlo(lesson, monkeypatch):
    """Notebook and portal builds only deserialize the checked-in lesson JSON."""
    import build_basket_reference
    from hullkit import exotics

    def forbidden(*args, **kwargs):
        raise AssertionError("figure construction must use saved lesson data")

    monkeypatch.setattr(exotics, "basket_moments", forbidden)
    monkeypatch.setattr(exotics, "basket_option_price", forbidden)
    monkeypatch.setattr(build_basket_reference, "conditional_two_asset", forbidden)
    monkeypatch.setattr(build_basket_reference, "simulate", forbidden)
    assert list(lesson._figures()) == KEYS
