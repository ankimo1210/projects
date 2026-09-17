"""Semantic figure tests for §26.14, pinned to the frozen M6a reference table.

Every claim a figure makes in its title or note is recomputed here from the
independent references in `docs/validation/section-26-14/`, not from the saved
figure. Prices are in currency, maturities in years, yields and volatilities
annualised per year; the markets are synthetic.
"""

import importlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRICES = json.loads((ROOT / "docs/validation/section-26-14/prices.json").read_text())
RECORD = json.loads((ROOT / "docs/validation/section-26-14/numerical-check.json").read_text())
KEYS = ["exchange_payoff", "exchange_correlation", "exchange_rate", "exchange_american"]
FAMILIES = ["contract", "correlation", "rate", "american"]
SOURCES = [
    "hullkit/src/hullkit/exotics.py",
    "scripts/build_exchange_lesson_data.py",
    "scripts/build_exchange_reference.py",
    "docs/validation/section-26-14/prices.json",
    "docs/validation/section-26-14/numerical-check.json",
]


@pytest.fixture(scope="module")
def lesson():
    return importlib.import_module("hullkit._exchange_lesson")


@pytest.fixture(scope="module")
def figures(lesson):
    return lesson._figures()


@pytest.fixture(scope="module")
def data(lesson):
    return lesson._load_data()


def trace(fig, role, scenario):
    return next(t for t in fig.data if t.meta["role"] == role and t.meta["scenario"] == scenario)


def margrabe(spot_u, spot_v, sigma_u, sigma_v, rho, expiry, yield_u, yield_v):
    """Equation 26.5 written out here, so the figure cannot define its own check."""
    spread = math.sqrt(sigma_u**2 + sigma_v**2 - 2.0 * rho * sigma_u * sigma_v)
    forward_u = spot_u * math.exp(-yield_u * expiry)
    forward_v = spot_v * math.exp(-yield_v * expiry)
    if spread <= 0.0:
        return max(forward_v - forward_u, 0.0)
    scale = spread * math.sqrt(expiry)
    d1 = (math.log(forward_v / forward_u) + 0.5 * scale**2) / scale
    return forward_v * _cdf(d1) - forward_u * _cdf(d1 - scale)


def _cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def test_keys_metadata_and_every_menu(figures):
    assert list(figures) == KEYS
    for key, fig in figures.items():
        assert fig.layout.meta["section"] == "26.14"
        assert fig.layout.meta["figure"] == key
        assert fig.layout.meta["units"]["money"] == "currency"
        for menu in fig.layout.updatemenus:
            for button in menu.buttons:
                visibility, layout = button.args
                state = layout["meta"]["scenario"]
                assert visibility["visible"] == [t.meta["scenario"] == state for t in fig.data]
    for key in KEYS:
        assert len(figures[key].layout.updatemenus[0].buttons) == 3


def test_every_state_draws_a_distinct_colour(figures):
    """After the portal theme remap two lines in one panel must not merge."""
    remap = {"#d62728": "#2563eb", "#1f77b4": "#1d1d1f", "#2ca02c": "#86868b"}
    for key, fig in figures.items():
        by_state = {}
        for item in fig.data:
            colour = item.line.color or (item.marker.color if item.marker else None)
            by_state.setdefault(item.meta["scenario"], []).append(remap.get(colour, colour))
        for state, colours in by_state.items():
            assert len(set(colours)) == len(colours), (key, state, colours)


def test_the_payoff_figure_is_the_contract_and_its_decomposition(figures, data):
    fig = figures["exchange_payoff"]
    rows = data["contract"]["data"]["rows"]
    given = data["contract"]["data"]["terminal_u"]
    for row in rows:
        assert row["exchange"] == max(row["terminal_v"] - given, 0.0)
        assert row["better_of"] == max(given, row["terminal_v"])
        assert row["worse_of"] == min(given, row["terminal_v"])
        # max + min = U + V in every state, so no single leg can drift alone.
        assert row["better_of"] + row["worse_of"] == pytest.approx(given + row["terminal_v"])
    for state, key in (("exchange", "exchange"), ("better_of", "better_of"),
                       ("worse_of", "worse_of")):
        plotted = trace(fig, "payoff", state)
        assert list(plotted.x) == [row["terminal_v"] for row in rows]
        assert list(plotted.y) == pytest.approx([row[key] for row in rows])
    # The drawn decomposition markers must land exactly on the drawn payoff lines.
    for state, rebuilt in (
        ("better_of", [given + row["exchange"] for row in rows]),
        ("worse_of", [row["terminal_v"] - row["exchange"] for row in rows]),
    ):
        assert list(trace(fig, "decomposition", state).y) == pytest.approx(rebuilt)
        assert list(trace(fig, "payoff", state).y) == pytest.approx(rebuilt)
    assert list(trace(fig, "given", "exchange").y) == [given] * len(rows)
    assert list(trace(fig, "received", "exchange").y) == [row["terminal_v"] for row in rows]
    # A kink at V_T = U_T, so this is not a straight line masquerading as a payoff.
    assert any(row["exchange"] == 0.0 for row in rows)
    assert any(row["exchange"] > 0.0 for row in rows)


def test_the_correlation_curve_is_margrabe_and_falls_with_rho(figures, data):
    fig = figures["exchange_correlation"]
    for family in data["correlation"]["data"]:
        state = family["market"]
        prices = trace(fig, "price", state)
        volatility = trace(fig, "volatility", state)
        for index, correlation in enumerate(prices.x):
            expected = margrabe(
                family["spot"], family["spot"], family["volatility_u"], family["volatility_v"],
                correlation, family["expiry"], family["yield_u"], family["yield_v"],
            )
            assert prices.y[index] == pytest.approx(expected, rel=1e-12)
            spread = math.sqrt(
                family["volatility_u"] ** 2 + family["volatility_v"] ** 2
                - 2.0 * correlation * family["volatility_u"] * family["volatility_v"]
            )
            assert volatility.y[index] == pytest.approx(100.0 * spread, rel=1e-12)
        assert list(prices.y) == sorted(prices.y, reverse=True)
        assert list(volatility.y) == sorted(volatility.y, reverse=True)
        assert prices.y[0] > prices.y[-1]
        forward = trace(fig, "forward", state)
        expected_forward = max(
            family["spot"] * math.exp(-family["yield_v"] * family["expiry"])
            - family["spot"] * math.exp(-family["yield_u"] * family["expiry"]),
            0.0,
        )
        assert forward.y[0] == pytest.approx(expected_forward)
        assert min(prices.y) >= expected_forward - 1e-12


def test_the_correlation_title_quotes_the_plotted_endpoints(figures, data):
    fig = figures["exchange_correlation"]
    titles = {
        button.args[1]["meta"]["scenario"]: button.args[1]["title.text"]
        for button in fig.layout.updatemenus[0].buttons
    }
    for family in data["correlation"]["data"]:
        entries = family["entries"]
        title = titles[family["market"]]
        assert f"{entries[0]['price']:.4f} → {entries[-1]['price']:.4f}" in title
        assert entries[0]["price"] > entries[-1]["price"]


def test_the_rate_figure_shows_a_price_that_does_not_move(figures, data):
    fig = figures["exchange_rate"]
    for family in data["rate"]["data"]:
        state = family["market"]
        reference = trace(fig, "reference", state)
        restated = trace(fig, "restated", state)
        rates = [value / 100.0 for value in reference.x]
        assert min(rates) < 0.0 < max(rates), "a negative rate must be probed too"
        assert max(reference.y) - min(reference.y) < 1e-11
        assert family["reference_spread"] == pytest.approx(max(reference.y) - min(reference.y))
        # Equation 26.5 written out here agrees with the quadrature at every rate.
        closed = margrabe(
            100.0, 100.0 * family["value_ratio"],
            *_volatilities(family["market"]), family["expiry"],
            family["yield_u"], family["yield_v"],
        )
        for value in reference.y:
            assert value == pytest.approx(closed, abs=2e-9, rel=1e-10)
        assert list(restated.y) == pytest.approx([family["restated_price"]] * len(rates))
        assert family["restated_price"] == pytest.approx(closed, abs=2e-9, rel=1e-10)


def _volatilities(market):
    row = next(row for row in PRICES["rows"] if row["market"] == market)
    return row["volatility_u"], row["volatility_v"], row["correlation"]


def test_the_comparison_line_in_the_rate_figure_really_does_move(figures, data):
    """The flat line only teaches something next to one that is not flat."""
    fig = figures["exchange_rate"]
    for family in data["rate"]["data"]:
        naive = trace(fig, "naive", family["market"])
        assert list(naive.y) == sorted(naive.y), "a call struck at a fixed amount rises with r"
        assert max(naive.y) - min(naive.y) > 1.0
        # Same sigma-hat, so the only difference is that the strike is a fixed amount.
        for rate, value in zip((v / 100.0 for v in naive.x), naive.y, strict=True):
            forward = 100.0 * family["value_ratio"] * math.exp(rate * family["expiry"])
            scale = family["spread_volatility"] * math.sqrt(family["expiry"])
            d1 = (math.log(forward / 100.0) + 0.5 * scale**2) / scale
            expected = math.exp(-rate * family["expiry"]) * (
                forward * _cdf(d1) - 100.0 * _cdf(d1 - scale))
            assert value == pytest.approx(expected, rel=1e-12)


def test_the_rate_independence_matches_the_recorded_measurement(figures, data):
    fig = figures["exchange_rate"]
    assert RECORD["rate_independence"]["max_spread"] < 1e-11
    drawn = max(
        max(trace(fig, "reference", family["market"]).y)
        - min(trace(fig, "reference", family["market"]).y)
        for family in data["rate"]["data"]
    )
    assert drawn < 1e-11


def test_the_american_figure_separates_early_exercise_from_the_grid(figures, data):
    fig = figures["exchange_american"]
    for family in data["american"]["data"]:
        state = family["market"]
        european = trace(fig, "european", state)
        american = trace(fig, "american", state)
        premium = trace(fig, "premium", state)
        grid = trace(fig, "grid", state)
        intrinsic = trace(fig, "intrinsic", state)
        for index, ratio in enumerate(european.x):
            expected = margrabe(
                100.0, 100.0 * ratio, *_volatilities(state), family["expiry"],
                family["yield_u"], family["yield_v"],
            )
            assert european.y[index] == pytest.approx(expected, rel=1e-12)
            assert american.y[index] >= intrinsic.y[index] - 1e-9
            # The tree can sit below the closed form by the grid residual, so compare it
            # with the same grid; against the closed form only allow that measured gap.
            entry = family["entries"][index]
            assert american.y[index] >= entry["european_on_grid"] - 1e-9
            assert american.y[index] >= european.y[index] - 4e-3
            assert intrinsic.y[index] == pytest.approx(max(100.0 * ratio - 100.0, 0.0))
        if family["yield_v"] == 0.0:
            # No yield on the asset received: early exercise is worthless, and what is
            # left is the finite grid. The figure must not present one as the other.
            assert max(premium.y) < 1e-9
            assert max(grid.y) > 1e-4
            assert max(grid.y) > 1e6 * max(premium.y)
        else:
            assert max(premium.y) > 1.0
            assert max(premium.y) > 1_000.0 * max(grid.y)
        entries = family["entries"]
        assert list(premium.y) == pytest.approx([e["premium_on_grid"] for e in entries])
        assert list(grid.y) == pytest.approx([abs(e["grid_residual"]) for e in entries])


def test_the_american_premium_grows_with_moneyness_when_a_yield_is_paid(figures, data):
    for family in data["american"]["data"]:
        if family["yield_v"] == 0.0:
            continue
        premium = trace(figures["exchange_american"], "premium", family["market"])
        assert list(premium.y) == sorted(premium.y)
        deep = family["entries"][-1]
        # Deep in the money with a yield on the received asset, exercise now is optimal.
        assert deep["american"] == pytest.approx(deep["intrinsic"], abs=1e-6)


def test_the_american_titles_do_not_call_a_grid_residual_a_premium(figures, data):
    titles = {
        button.args[1]["meta"]["scenario"]: button.args[1]["title.text"]
        for button in figures["exchange_american"].layout.updatemenus[0].buttons
    }
    for family in data["american"]["data"]:
        title = titles[family["market"]]
        if family["yield_v"] == 0.0:
            assert "早期行使に価値なし" in title
        else:
            assert "倍" in title and "早期行使に価値なし" not in title


def test_the_convergence_record_refines_monotonically(data):
    for family in data["american"]["data"]:
        steps = [item["steps"] for item in family["convergence"]]
        assert steps == [64, 128, 256, 512, 1024]
        gaps = [item["gap_to_european"] for item in family["convergence"]]
        limit = gaps[-1]
        errors = [abs(gap - limit) for gap in gaps[:-1]]
        assert errors == sorted(errors, reverse=True), family["market"]


def test_refuse_stale_hashes(lesson, tmp_path):
    data = lesson._load_data()
    data["american"]["source_hashes"]["hullkit/src/hullkit/exotics.py"] = "0" * 64
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="stale"):
        lesson._load_data(path)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("source", SOURCES)
def test_refuse_missing_required_source_hash(lesson, tmp_path, family, source):
    data = lesson._load_data()
    del data[family]["source_hashes"][source]
    path = tmp_path / "missing-hash.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=r"missing.*source"):
        lesson._load_data(path)


def test_figures_do_not_price_again(lesson, monkeypatch):
    from hullkit import bsm, exotics

    def forbidden(*args, **kwargs):
        raise AssertionError("figure construction must use saved prices")

    for name in (
        "exchange_option",
        "exchange_option_american",
        "exchange_spread_volatility",
        "better_of_two_assets",
        "worse_of_two_assets",
    ):
        monkeypatch.setattr(exotics, name, forbidden)
    monkeypatch.setattr(bsm, "call_price", forbidden)
    assert list(lesson._figures()) == KEYS
