"""税務計算テスト。"""

from __future__ import annotations

from re_engine.tax import (
    annual_depreciation,
    capital_gain_tax,
    disallowed_land_interest,
    income_tax,
    taxable_income,
)


def test_depreciation_new_rc() -> None:
    """RC造新築 5000万円 / 法定47年 → 償却率 ≒ 0.021 → 年額約 1,050,000円。"""
    dep = annual_depreciation(50_000_000, "rc", 2026, 2026)
    # 1/47 = 0.0213 → 50,000,000 * 0.021 = 1,050,000
    assert 1_040_000 <= dep <= 1_070_000


def test_depreciation_new_wood() -> None:
    """木造新築 2000万円 / 法定22年 → 償却率 ≒ 0.045 → 年額約 900,000円。"""
    dep = annual_depreciation(20_000_000, "wood", 2026, 2026)
    # 1/22 = 0.0454 → 20,000,000 * 0.045 = 900,000
    assert 880_000 <= dep <= 920_000


def test_depreciation_used_full_elapsed() -> None:
    """木造築30年 → 全部経過 → 22 * 0.2 = 4年。建物2000万なら 5,000,000円/年。"""
    dep = annual_depreciation(20_000_000, "wood", 1995, 2026)
    # 1/4 = 0.25 → 20,000,000 * 0.25 = 5,000,000
    assert 4_900_000 <= dep <= 5_100_000


def test_depreciation_used_partial() -> None:
    """RC造築15年 → (47-15) + 15*0.2 = 35年。建物3000万なら約 857,000円。"""
    dep = annual_depreciation(30_000_000, "rc", 2011, 2026)
    # 1/35 = 0.0285 → 30,000,000 * 0.029 = 870,000
    assert 800_000 <= dep <= 900_000


def test_depreciation_zero_building() -> None:
    assert annual_depreciation(0, "rc", 2020, 2026) == 0


def test_disallowed_land_interest() -> None:
    # 利息 1,000,000円、土地比率 20% (800万 / 4000万)
    d = disallowed_land_interest(1_000_000, 8_000_000, 40_000_000)
    assert d == 200_000


def test_taxable_income_positive() -> None:
    # NOI 500万、利息 100万、減価償却 200万 → 課税所得 200万
    t = taxable_income(5_000_000, 1_000_000, 2_000_000)
    assert t == 2_000_000


def test_taxable_income_loss_with_land_interest_excluded() -> None:
    """赤字 -300万、利息 100万、土地利息分 (土地2000万/価格1億 = 20%) = 20万。
    赤字から土地利息分を戻し: -300万 + 20万 = -280万。
    """
    t = taxable_income(
        noi_yen=1_000_000,
        interest_yen=1_000_000,
        depreciation_yen=3_000_000,
        land_value_yen=20_000_000,
        total_price_yen=100_000_000,
    )
    assert t == -2_800_000


def test_taxable_income_loss_no_land_info() -> None:
    """土地情報未指定なら通常の損益通算を許す (赤字そのまま)。"""
    t = taxable_income(
        noi_yen=1_000_000,
        interest_yen=1_000_000,
        depreciation_yen=3_000_000,
    )
    assert t == -3_000_000


def test_income_tax_positive() -> None:
    # 200万円課税 × (20% + 10%) = 600,000円
    assert income_tax(2_000_000, 0.20, 0.10) == 600_000


def test_income_tax_negative_returns_zero() -> None:
    """赤字は税0 (還付は給与側で吸収する想定)。"""
    assert income_tax(-500_000, 0.20, 0.10) == 0


def test_capital_gain_long_term() -> None:
    """5年超: 長期譲渡 約20%。譲渡所得500万 → 100万。"""
    tax = capital_gain_tax(
        sale_price_yen=50_000_000,
        selling_costs_yen=2_000_000,
        book_value_yen=43_000_000,  # 譲渡所得 = 50,000,000 - 2,000,000 - 43,000,000 = 5,000,000
        hold_period_years=10,
        short_rate=0.39,
        long_rate=0.20,
    )
    assert tax == 1_000_000


def test_capital_gain_short_term() -> None:
    """5年以下: 短期譲渡 約39%。譲渡所得500万 → 1,950,000。"""
    tax = capital_gain_tax(
        sale_price_yen=50_000_000,
        selling_costs_yen=2_000_000,
        book_value_yen=43_000_000,
        hold_period_years=3,
        short_rate=0.39,
        long_rate=0.20,
    )
    assert tax == 1_950_000


def test_capital_gain_loss_zero() -> None:
    """譲渡損は税0。"""
    tax = capital_gain_tax(
        sale_price_yen=30_000_000,
        selling_costs_yen=1_000_000,
        book_value_yen=40_000_000,
        hold_period_years=10,
        short_rate=0.39,
        long_rate=0.20,
    )
    assert tax == 0
