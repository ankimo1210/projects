"""Offline tests for the factor estimation script (no network)."""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "estimate_factors", PROJECT_ROOT / "scripts/estimate_factors.py"
)
estimate_factors = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(estimate_factors)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("R8.8.3", date(2026, 8, 3)),
        ("H31.4.30", date(2019, 4, 30)),
        ("S49.9.24", date(1974, 9, 24)),
        ("", None),
        ("2026-08-03", None),
    ],
)
def test_parse_wareki(text: str, expected: date | None) -> None:
    assert estimate_factors.parse_wareki(text) == expected


def test_parse_jgb_csv_reads_the_requested_tenor() -> None:
    text = "国債金利情報,,\n基準日,1年,10年\nR8.8.3,1.287,2.824\nR8.8.4,1.290,-\n"

    series = estimate_factors.parse_jgb_csv(text, tenor="10年")

    assert list(series.index.date) == [date(2026, 8, 3)]
    assert series.iloc[0] == pytest.approx(2.824)


def test_parse_jgb_csv_rejects_an_unknown_tenor() -> None:
    text = "国債金利情報,,\n基準日,1年,10年\nR8.8.3,1.287,2.824\n"

    with pytest.raises(KeyError):
        estimate_factors.parse_jgb_csv(text, tenor="7年")


def test_find_price_spikes_catches_a_run_of_bad_prints() -> None:
    index = pd.bdate_range("2026-01-01", periods=20)
    prices = pd.Series(100.0, index=index)
    prices.iloc[10] = 10.0  # a dropped decimal place, two sessions long
    prices.iloc[11] = 10.1

    spikes = estimate_factors.find_price_spikes(prices)

    assert [stamp.date() for stamp in spikes] == [index[10].date(), index[11].date()]


def test_find_price_spikes_leaves_a_real_crash_alone() -> None:
    index = pd.bdate_range("2026-01-01", periods=30)
    prices = pd.Series(
        [100.0] * 10 + [100.0 * 0.96**step for step in range(1, 11)] + [66.0] * 10,
        index=index,
    )

    assert estimate_factors.find_price_spikes(prices) == []


def test_screen_prices_skips_series_that_may_legitimately_halve() -> None:
    index = pd.bdate_range("2026-01-01", periods=20)
    frame = pd.DataFrame({"^TNX": 4.0, "SPY": 100.0}, index=index)
    frame.loc[index[10], "^TNX"] = 0.5  # a real yield collapse, not a bad print
    frame.loc[index[10], "SPY"] = 10.0

    screened, report = estimate_factors.screen_prices(frame, skip=("^TNX",))

    assert "^TNX" not in report
    assert screened.loc[index[10], "^TNX"] == pytest.approx(0.5)
    assert [row["date"] for row in report["SPY"]] == [index[10].date().isoformat()]
    assert pd.isna(screened.loc[index[10], "SPY"])


def test_robust_outlier_mask_flags_only_the_absurd_observation() -> None:
    returns = pd.Series([0.01, -0.02, 0.015, -0.01, 0.02, -0.015, 0.01, 2.5])

    mask = estimate_factors.robust_outlier_mask(returns)

    assert list(mask) == [False] * 7 + [True]


def test_build_factor_frame_uses_excess_returns_over_the_market_leg() -> None:
    index = pd.bdate_range("2026-01-01", periods=2)
    prices = pd.DataFrame(
        {
            "1306.T": [100.0, 90.0],
            "SPY": [100.0, 95.0],
            "SMH": [100.0, 85.0],
            "XLE": [100.0, 105.0],
            "1343.T": [100.0, 99.0],
            "JPY=X": [150.0, 145.5],
            # Equipment falls harder than the sector, platforms fall less.
            **{symbol: [100.0, 75.0] for symbol in estimate_factors.EQUIPMENT_BASKET},
            **{symbol: [100.0, 95.0] for symbol in estimate_factors.PLATFORM_BASKET},
        },
        index=index,
    )
    yields = pd.DataFrame({"jgb_10y": [1.0, 1.5], "^TNX": [4.0, 4.25]}, index=index)

    factors = estimate_factors.build_factor_frame(prices, yields)
    row = factors.iloc[1]

    assert row["株式全体"] == pytest.approx(0.5 * -0.10 + 0.5 * -0.05)
    assert row["情報技術"] == pytest.approx(-0.15 - -0.05)
    # The value-chain legs nest inside 情報技術: they are excess over the sector,
    # so an equipment holding carries 株式全体 + 情報技術 + IT装置, not IT装置 alone.
    assert row["IT装置"] == pytest.approx(-0.25 - -0.15)
    assert row["IT需要側"] == pytest.approx(-0.05 - -0.15)
    assert row["エネルギー"] == pytest.approx(0.05 - -0.05)
    assert row["不動産"] == pytest.approx(-0.01 - -0.10)
    assert row["外貨対円"] == pytest.approx(-0.03)
    assert row["日本金利"] == pytest.approx(0.005)
    assert row["海外金利"] == pytest.approx(0.0025)


def test_estimate_betas_recovers_a_known_beta() -> None:
    index = pd.bdate_range("2024-01-01", periods=200, freq="W-FRI")
    market = pd.Series([0.01, -0.02, 0.015, -0.005] * 50, index=index).cumsum() + 1
    target = pd.Series([0.02, -0.04, 0.030, -0.010] * 50, index=index).cumsum() + 1
    prices = pd.DataFrame({"MKT": market, "TGT": target})

    betas = estimate_factors.estimate_betas(prices, {"TGT": "MKT"})

    assert betas["TGT"]["observations"] > 52
    assert betas["TGT"]["beta"] == pytest.approx(2.0, rel=0.05)
    assert betas["TGT"]["correlation"] == pytest.approx(1.0, rel=0.01)
