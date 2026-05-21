"""IRR・Equity Multiple・Payback・DSCR・Cap Rate のテスト。"""

from __future__ import annotations

import math

from re_engine.irr import (
    cap_rate,
    cash_on_cash,
    dscr,
    equity_irr,
    equity_multiple,
    ltv,
    payback_years,
)


def test_irr_known_simple_case() -> None:
    """-100, 0, 0, 0, 0, 161.05 → IRR = 10%。"""
    irr = equity_irr(100, [0, 0, 0, 0, 0], 161)
    assert irr is not None
    assert abs(irr - 0.10) < 0.001


def test_irr_all_loss_returns_none_or_negative() -> None:
    """全期間赤字なら IRR は負または None。"""
    irr = equity_irr(1_000_000, [-100_000] * 10, -500_000)
    # 解が見つかれば負、見つからなければ None
    assert irr is None or irr < 0


def test_equity_multiple() -> None:
    assert equity_multiple(1_000_000, 1_500_000) == 1.5


def test_payback_exact() -> None:
    """毎年100ずつ、自己資金500 → 5年で回収。"""
    assert payback_years(500, [100] * 10) == 5.0


def test_payback_interpolation() -> None:
    """4年で400、5年目に150入る → 5年は 400 + 線形補間。"""
    py = payback_years(500, [100, 100, 100, 100, 150, 0, 0])
    assert py is not None
    # year 5 で 400+150=550、equity=500 → 4 + (500-400)/150 = 4.667
    assert abs(py - 4 - 100 / 150) < 0.01


def test_payback_never() -> None:
    """累計が equity に届かない場合は None。"""
    assert payback_years(1_000_000, [50_000] * 5) is None


def test_dscr_positive() -> None:
    assert dscr(2_000_000, 1_000_000) == 2.0


def test_dscr_zero_debt_service() -> None:
    assert math.isinf(dscr(1_000_000, 0))


def test_cap_rate() -> None:
    assert cap_rate(2_000_000, 40_000_000) == 0.05


def test_cash_on_cash() -> None:
    assert cash_on_cash(300_000, 10_000_000) == 0.03


def test_ltv() -> None:
    assert ltv(28_000_000, 40_000_000) == 0.70
