"""Industry run-ups and crashes from French's data library (spec 7): parsing, windows, episodes, clusters."""

from __future__ import annotations

import pytest
from portfolio_analyzer.ai_bubble.history import (
    cluster_bootstrap,
    crash_flags,
    episode_starts,
    forward_drawdown,
    industry_for_sic,
    levels,
    outcome,
    parse_french_factors,
    parse_french_industry,
    parse_french_sic,
    percentile_interval,
    pooled_mean,
    predictive_splits,
    quantile,
    runup_flags,
    s_classify,
    trailing_return,
)

INDUSTRY_CSV = """This file was created using the 202608 CRSP database.
It contains value- and equal-weighted returns for 49 industry portfolios.

Missing data are indicated by -99.99 or -999.


  Average Value Weighted Returns -- Monthly
,Agric,Food ,Other
202606,   1.00,  -99.99,   2.00
202607,  -2.00,   3.00,   0.50
202608,   0.50,   1.00,  -999


  Average Equal Weighted Returns -- Monthly
,Agric,Food ,Other
202606,   9.00,   9.00,   9.00


  Average Value Weighted Returns -- Annual
,Agric,Food ,Other
  2025,  12.00,  13.00,  14.00


  Number of Firms in Portfolios
,Agric,Food ,Other
202606,     12,      0,     30
202607,     12,      9,     30
202608,     11,     10,     31
"""

FACTORS_CSV = """This file was created using the 202608 CRSP database.

,Mkt-RF,SMB,HML,RF
202607,   2.00,  -2.42,  -2.75,   0.30
202608,  -1.00,  -1.44,   4.13,   0.25

 Annual Factors: January-December
,Mkt-RF,SMB,HML,RF
  2025,  13.30, -10.79,   8.71,   4.25
"""

SIC_TXT = (
    " 1 Agric  Agriculture\r\n"
    "          0100-0199 Agricultural production - crops\r\n"
    "\r\n"
    "37 Chips  Electronic Equipment\r\n"
    "          3600-3600 Electronic and other electrical equipment\r\n"
    "          3674-3674 Semiconductors and related devices\r\n"
)


def test_the_industry_file_gives_monthly_value_weighted_returns_and_firm_counts_only():
    out = parse_french_industry(INDUSTRY_CSV)
    assert out["version"] == "202608"
    assert out["months"] == ["2026-06", "2026-07", "2026-08"]
    assert out["industries"] == ["Agric", "Food", "Other"]
    assert out["vw"]["Agric"] == pytest.approx([0.01, -0.02, 0.005])
    assert out["vw"]["Food"][0] is None and out["vw"]["Other"][2] is None
    assert out["nfirms"]["Food"] == [0, 9, 10]


def test_the_factor_file_gives_monthly_market_excess_and_bill_rate():
    out = parse_french_factors(FACTORS_CSV)
    assert out["months"] == ["2026-07", "2026-08"]
    assert out["mkt_rf"] == pytest.approx([0.02, -0.01])
    assert out["rf"] == pytest.approx([0.003, 0.0025])


def test_the_sic_map_assigns_ranges_and_leaves_the_rest_to_other():
    ranges = parse_french_sic(SIC_TXT)
    assert ranges == [(100, 199, "Agric"), (3600, 3600, "Chips"), (3674, 3674, "Chips")]
    assert industry_for_sic(3674, ranges) == "Chips"
    assert industry_for_sic(9999, ranges) == "Other"


def test_levels_break_at_a_missing_month_and_restart_after_it():
    assert levels([0.1, 0.1]) == pytest.approx([1.1, 1.21])
    out = levels([None, 0.1, None, 0.5])
    assert out[0] is None and out[2] is None
    assert out[1] == pytest.approx(1.1) and out[3] == pytest.approx(1.5)


def test_forward_drawdown_counts_a_fall_from_any_point_in_the_window():
    assert forward_drawdown([100.0, 150.0, 90.0], 0, 2) == pytest.approx(-0.4)
    assert forward_drawdown([100.0, 140.0, 110.0], 0, 2) == pytest.approx(110 / 140 - 1)
    assert forward_drawdown([100.0, 150.0], 0, 2) is None
    assert forward_drawdown([100.0, None, 90.0], 0, 2) is None


def rising(gain: float, months: int = 24, flat: int = 37) -> list[float]:
    """Flat for ``flat`` months, then rising linearly by ``gain`` over ``months``."""
    return [1.0] * flat + [1.0 + gain * k / months for k in range(1, months + 1)]


def test_a_run_up_needs_raw_and_net_doubling_and_a_five_year_gain():
    firms = [12] * 61
    flags = runup_flags(rising(1.1), rising(0.05), firms)
    assert flags[60] is True
    assert flags[59] is None  # five years of history needed
    assert runup_flags(rising(1.1), rising(0.2), firms)[60] is False
    assert runup_flags(rising(1.1), rising(0.05), [12] * 60 + [9])[60] is None


def test_the_old_rule_takes_a_lower_net_threshold_and_no_five_year_condition():
    old = runup_flags(rising(1.1), rising(0.2), [12] * 61, net_threshold=0.5, five_year=None)
    assert old[60] is True
    assert old[24] is False


def test_compounded_monthly_excess_differs_from_the_difference_of_returns():
    ind = levels([0.0] * 37 + [0.035] * 24)
    mkt = levels([0.0] * 37 + [0.01] * 24)
    firms = [12] * 61
    assert runup_flags(ind, mkt, firms)[60] is True  # 128% - 27% = 101%
    assert runup_flags(ind, mkt, firms, net="compounded")[60] is False  # 1.025^24 - 1 = 81%


def test_an_episode_starts_at_the_first_flag_and_blocks_the_next_24_months():
    def flags_at(*months: int, n: int = 50) -> list[bool | None]:
        return [i in months for i in range(n)]

    assert episode_starts(flags_at(5, 6, 7, 40)) == [5, 40]
    assert episode_starts(flags_at(5, 20)) == [5]
    assert episode_starts(flags_at(*range(5, 36))) == [5, 29]
    assert episode_starts([None, True, None]) == [1]


def test_cluster_bootstrap_draws_whole_calendar_years():
    clusters = {"A": [1.0, 1.0], "B": [0.0]}
    draws = cluster_bootstrap(clusters, reps=400, seed=20261021)
    assert len(draws) == 400
    assert all(min(abs(d - x) for x in (0.0, 2 / 3, 1.0)) < 1e-12 for d in draws)
    assert any(abs(d - 2 / 3) < 1e-12 for d in draws)
    assert cluster_bootstrap(clusters, reps=400, seed=20261021) == draws
    assert pooled_mean(clusters) == pytest.approx(2 / 3)


def test_outcome_gives_the_crash_flag_and_returns_after_the_start():
    ind = [1.0] * 13 + [0.5] * 12
    mkt = [1.0] * 13 + [1.1] * 12
    out = outcome(ind, mkt, 0)
    assert out["crash"] is True and out["drawdown"] == pytest.approx(-0.5)
    assert out["raw_12m"] == 0.0 and out["raw_24m"] == pytest.approx(-0.5)
    assert out["net_24m"] == pytest.approx(-0.6)
    late = outcome(ind, mkt, 10)
    assert (
        late["crash"] is None and late["raw_24m"] is None and late["raw_12m"] == pytest.approx(-0.5)
    )


def test_crash_flags_need_ten_firms_and_a_complete_window():
    lv = [1.0, 0.5, 0.5, 0.6]
    assert crash_flags(lv, [12, 12, 12, 12], months=2) == [True, False, None, None]
    assert crash_flags(lv, [9, 12, 12, 12], months=2) == [None, False, None, None]


def test_quantile_interpolates_between_order_statistics():
    assert quantile([4.0, 1.0, 3.0, 2.0], 0.75) == pytest.approx(3.25)
    assert percentile_interval([i / 100 for i in range(101)], 0.95) == pytest.approx((0.025, 0.975))


def test_trailing_return_needs_the_whole_window():
    assert trailing_return([1.0, 1.5, 2.0], 2, 2) == pytest.approx(1.0)
    assert trailing_return([1.0, None, 2.0], 2, 2) is None
    assert trailing_return([1.0, 2.0], 1, 2) is None


@pytest.mark.parametrize(
    ("flag", "net", "q75", "low", "label"),
    [
        (True, 1.5, 0.4, 0.30, "支持"),
        (True, 1.5, 0.4, 0.10, "混在"),
        (False, 0.2, 0.4, 0.30, "弱める"),
        (False, 0.6, 0.4, 0.30, "混在"),
        (None, 0.2, 0.4, 0.30, "データ不足"),
    ],
)
def test_s_classify(flag, net, q75, low, label):
    assert s_classify(flag, net, q75, crash_ci_low=low, unconditional=0.14) == label


def test_prediction_needs_ten_calendar_years_in_each_of_three_splits():
    years = [str(1930 + i) for i in range(29)] + ["1930"]
    assert predictive_splits(years)["feasible"] is False
    out = predictive_splits([str(1930 + i) for i in range(30)])
    assert out["feasible"] is True
    assert out["splits"] == [["1930", "1939"], ["1940", "1949"], ["1950", "1959"]]
