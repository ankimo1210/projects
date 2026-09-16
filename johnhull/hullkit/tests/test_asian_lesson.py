"""Semantic figure tests for §26.13, pinned to the frozen M5a reference table."""

import importlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRICES = json.loads((ROOT / "docs/validation/section-26-13/prices.json").read_text())
RECORD = json.loads((ROOT / "docs/validation/section-26-13/numerical-check.json").read_text())
BROWSER = json.loads((ROOT / "docs/validation/section-26-13/browser-reference.json").read_text())
KEYS = ["asian_payoff", "asian_distribution", "asian_observations", "asian_error"]
FAMILIES = ["contract", "distribution", "observations", "errors", "seasoned"]
SOURCES = [
    "hullkit/src/hullkit/exotics.py",
    "scripts/build_asian_lesson_data.py",
    "scripts/build_asian_reference.py",
    "docs/validation/section-26-13/prices.json",
    "docs/validation/section-26-13/numerical-check.json",
]


@pytest.fixture(scope="module")
def lesson():
    return importlib.import_module("hullkit._asian_lesson")


@pytest.fixture(scope="module")
def figures(lesson):
    return lesson._figures()


@pytest.fixture(scope="module")
def data(lesson):
    return lesson._load_data()


def trace(fig, role, scenario):
    return next(t for t in fig.data if t.meta["role"] == role and t.meta["scenario"] == scenario)


def priced(market, contract, spot_ratio, observations):
    return next(
        row
        for row in PRICES["rows"]
        if row["market"] == market
        and row["contract"] == contract
        and row["spot_ratio"] == spot_ratio
        and row["observations"] == observations
    )


def independent_moments(spot, rate, dividend, volatility, dates):
    """Plain double sum for E[A] and E[A^2]; no suffix-sum shortcut."""
    forwards = [spot * math.exp((rate - dividend) * t) for t in dates]
    first = sum(forwards) / len(dates)
    second = sum(
        f_i * f_j * math.exp(volatility**2 * min(t_i, t_j))
        for f_i, t_i in zip(forwards, dates, strict=True)
        for f_j, t_j in zip(forwards, dates, strict=True)
    ) / len(dates) ** 2
    return first, second


def test_keys_metadata_and_every_menu(figures):
    assert list(figures) == KEYS
    for key, fig in figures.items():
        assert fig.layout.meta["section"] == "26.13"
        assert fig.layout.meta["figure"] == key
        assert fig.layout.meta["units"]["money"] == "currency"
        for menu in fig.layout.updatemenus:
            for button in menu.buttons:
                visibility, layout = button.args
                state = layout["meta"]["scenario"]
                assert visibility["visible"] == [t.meta["scenario"] == state for t in fig.data]
    assert len(figures["asian_payoff"].layout.updatemenus[0].buttons) == 2
    assert len(figures["asian_distribution"].layout.updatemenus[0].buttons) == 3
    assert len(figures["asian_observations"].layout.updatemenus[0].buttons) == 6
    assert len(figures["asian_error"].layout.updatemenus[0].buttons) == 2


def test_payoffs_follow_from_the_plotted_path(figures, data):
    fig = figures["asian_payoff"]
    row = data["contract"]["rows"][0]
    path = list(trace(fig, "path", "average_price").y)
    assert path == row["path"]
    # Today is drawn but is not an observation date.
    observations = path[1:]
    average = sum(observations) / len(observations)
    terminal, strike = path[-1], row["strike"]
    assert trace(fig, "average", "average_price").y[0] == pytest.approx(average)
    assert trace(fig, "strike", "average_price").y[0] == pytest.approx(strike)
    assert trace(fig, "terminal", "average_price").y[0] == pytest.approx(terminal)
    expected = {
        "average_price": [max(average - strike, 0.0), max(strike - average, 0.0)],
        "average_strike": [max(terminal - average, 0.0), max(average - terminal, 0.0)],
    }
    for state, (call, put) in expected.items():
        bars = trace(fig, "payoff", state)
        assert list(bars.y) == pytest.approx([call, put, max(terminal - strike, 0.0)])
    assert average != terminal


def test_distribution_moments_density_and_the_missing_skewness(figures, data):
    fig = figures["asian_distribution"]
    for row in data["distribution"]["rows"]:
        state = row["market"]
        dates = [(i + 1) * row["expiry"] / row["observations"] for i in range(row["observations"])]
        first, second = independent_moments(
            data["strike"], row["rate"], row["dividend"], row["volatility"], dates
        )
        assert row["moment_1"] == pytest.approx(first, rel=1e-12)
        assert row["moment_2"] == pytest.approx(second, rel=1e-12)
        scale = math.sqrt(math.log(second / first**2))
        assert row["matched_volatility"] * math.sqrt(row["expiry"]) == pytest.approx(scale)
        moment = trace(fig, "moment", state)
        assert moment.x[0] == pytest.approx(first)
        location = math.log(first) - 0.5 * scale**2
        fitted = trace(fig, "fitted", state)
        for centre, density in zip(fitted.x, fitted.y, strict=True):
            expected = math.exp(-0.5 * ((math.log(centre) - location) / scale) ** 2) / (
                centre * scale * math.sqrt(2.0 * math.pi)
            )
            assert density == pytest.approx(expected, rel=1e-12)
        simulated = trace(fig, "simulated", state)
        assert list(simulated.x) == list(fitted.x)
        # Measured, not assumed: the average is more right-skewed than the fit, in every market.
        assert row["simulated_skewness"] > row["fitted_skewness"]


def test_observation_curve_matches_the_frozen_table_and_its_bounds(figures, data):
    fig = figures["asian_observations"]
    for row in data["observations"]["rows"]:
        state = row["market"]
        approximation = trace(fig, "approximation", state)
        reference = trace(fig, "reference", state)
        geometric = trace(fig, "geometric", state)
        assert list(approximation.x) == [12, 52, 250]
        for index, count in enumerate(approximation.x):
            frozen = priced(state, "call", 1.0, count)
            assert approximation.y[index] == pytest.approx(frozen["turnbull_wakeman"], rel=1e-12)
            assert geometric.y[index] == pytest.approx(frozen["geometric"], rel=1e-12)
            spread = 4.0 * math.hypot(
                reference.error_y["array"][index] / 4.0, frozen["standard_error"]
            )
            assert abs(reference.y[index] - frozen["reference"]) <= max(spread, 1e-9)
            assert geometric.y[index] <= reference.y[index] + 1e-9
        assert reference.y[0] >= reference.y[-1]
        continuous = trace(fig, "continuous", state)
        assert continuous.y[0] == pytest.approx(row["continuous_turnbull_wakeman"])
        assert continuous.y[0] < approximation.y[-1]


def test_error_figure_reports_both_signs_and_the_recorded_extremes(figures):
    plotted = {}
    for state in ("call", "put"):
        fig = figures["asian_error"]
        for item in fig.data:
            if item.meta["scenario"] != state or not item.meta["role"].startswith("market:"):
                continue
            market = item.meta["role"].split(":", 1)[1]
            for ratio, percent in zip(item.x, item.y, strict=True):
                frozen = priced(market, state, ratio, 52)
                expected = (frozen["turnbull_wakeman"] - frozen["reference"]) / frozen["reference"]
                assert percent == pytest.approx(100.0 * expected, rel=1e-12)
                plotted[(market, state, ratio)] = expected
    assert max(plotted.values()) > 0.0 > min(plotted.values())
    # The figure shows 52 observations only; the record's extremes range over 2/12/52/250,
    # so the plotted extremes must never exceed them.
    for key, sign in (("largest_overprice", 1.0), ("largest_underprice", -1.0)):
        worst = RECORD["approximation_error"][key]
        shown = max(plotted.values(), key=lambda value: sign * value)
        assert sign * shown > 0.0
        assert sign * shown <= sign * worst["relative_error"]
        key_52 = (worst["market"], worst["contract"], worst["spot_ratio"])
        if key_52 in plotted:
            matching = priced(*key_52, 52)
            assert plotted[key_52] == pytest.approx(
                (matching["turnbull_wakeman"] - matching["reference"]) / matching["reference"],
                rel=1e-12,
            )
        else:
            # Dropped by the figure's own filter, not missing: too small to quote a ratio.
            assert worst["observations"] != 52 or priced(*key_52, 52)["reference"] <= 0.5
    assert max(plotted.values()) == pytest.approx(0.22712, abs=5e-5)
    assert min(plotted.values()) == pytest.approx(-0.02893, abs=5e-5)
    # The same spot-to-strike ratio carries both signs, so no rule in moneyness holds.
    for ratio in (0.8, 1.0, 1.25):
        at_ratio = [value for (_, _, r), value in plotted.items() if r == ratio]
        assert max(at_ratio) > 0.0 > min(at_ratio)


def test_unresolved_points_are_marked_and_counted_in_the_note(figures, lesson, data):
    """Points whose difference hides inside the simulation noise must be drawn apart."""
    rows = data["errors"]["rows"]
    unresolved = {
        (row["market"], row["contract"], row["spot_ratio"])
        for row in rows
        if abs(row["turnbull_wakeman"] - row["reference"]) <= 4.0 * row["standard_error"]
    }
    assert unresolved, "the figure claims some points are unresolved"
    fig = figures["asian_error"]
    seen = set()
    for item in fig.data:
        market = item.meta["role"].split(":", 1)[1]
        for ratio, symbol, flag in zip(
            item.x, item.marker.symbol, (row[1] for row in item.customdata), strict=True
        ):
            key = (market, item.meta["scenario"], ratio)
            assert flag == (key not in unresolved)
            assert (symbol == "x-thin") == (key in unresolved)
            if symbol == "x-thin":
                seen.add(key)
    assert seen == unresolved
    note = fig.layout.annotations[0].text
    assert f"×印の{len(unresolved)}点" in note
    assert "はるかに小さい" not in note
    assert "0.5以下" in note


def test_seasoned_rows_are_the_contract_the_notebook_displays(data):
    """The saved evidence and the displayed table must price the same contract."""
    rows = data["seasoned"]["rows"]
    displayed = BROWSER["seasoned"]
    assert [row["observed_average"] for row in rows] == [
        pin["observed_average"] for pin in displayed["rows"]
    ]
    for key in ("spot", "strike", "rate", "dividend", "volatility", "elapsed", "remaining"):
        assert {row[key] for row in rows} == {displayed["inputs"][key]}
    for row, pin in zip(rows, displayed["rows"], strict=True):
        assert row["shifted_strike"] == pytest.approx(pin["shifted_strike"], rel=1e-12)
        assert row["certain_exercise"] == pin["certain_exercise"]
        # The independent browser reference never imports the pricer under test.
        assert row["price"] == pytest.approx(pin["price"], rel=1e-9)


def test_seasoned_shift_holds_two_ways_including_the_certain_call(data):
    rows = data["seasoned"]["rows"]
    assert any(row["certain_exercise"] for row in rows)
    for row in rows:
        strike = row["strike"]
        window = row["elapsed"] + row["remaining"]
        weight = row["remaining"] / window
        assert row["weight"] == pytest.approx(weight)
        shifted = strike / weight - row["observed_average"] * row["elapsed"] / row["remaining"]
        assert row["shifted_strike"] == pytest.approx(shifted, rel=1e-12)
        # The same shift written on the whole window instead of the remaining one.
        assert weight * shifted == pytest.approx(
            strike - (1.0 - weight) * row["observed_average"], rel=1e-12
        )
        assert row["certain_exercise"] == (shifted <= 0.0)
        if row["certain_exercise"]:
            discount = math.exp(-row["rate"] * row["remaining"])
            whole = (
                row["elapsed"] * row["observed_average"]
                + row["remaining"] * row["remaining_moment_1"]
            ) / window
            assert row["price"] == pytest.approx(discount * (whole - strike), rel=1e-12)
            assert row["price"] == pytest.approx(
                weight * discount * (row["remaining_moment_1"] - shifted), rel=1e-12
            )
            assert row["put_price"] == 0.0


def test_refuse_stale_hashes(lesson, tmp_path):
    data = lesson._load_data()
    data["errors"]["source_hashes"]["hullkit/src/hullkit/exotics.py"] = "0" * 64
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
    from hullkit import exotics

    def forbidden(*args, **kwargs):
        raise AssertionError("figure construction must use saved prices")

    for name in (
        "asian_moments",
        "asian_average_price",
        "asian_average_strike",
        "asian_seasoned_average_price",
        "asian_call_turnbull_wakeman",
    ):
        monkeypatch.setattr(exotics, name, forbidden)
    assert list(lesson._figures()) == KEYS
