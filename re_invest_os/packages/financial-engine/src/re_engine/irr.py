"""IRR・Equity Multiple・Payback Period (純粋関数)。

- equity_irr: 自己資金IRR (10年保有 + 売却手残り込み)
- equity_multiple: 回収倍率
- payback_years: 自己資金回収年数 (累計ATCFがequityを超える時点、線形補間)
- dscr / cap_rate / cash_on_cash: 単発比率
"""

from __future__ import annotations

import numpy as np
import numpy_financial as npf


def equity_irr(
    equity_invested_yen: int,
    atcfs_yen: list[int],
    net_proceeds_yen: int,
) -> float | None:
    """自己資金IRR。

    キャッシュフロー = [-equity, ATCF_1, ..., ATCF_n-1, ATCF_n + net_proceeds]
    """
    if equity_invested_yen <= 0 or not atcfs_yen:
        return None
    flows = [-equity_invested_yen, *list(atcfs_yen[:-1]), atcfs_yen[-1] + net_proceeds_yen]
    try:
        irr = float(npf.irr(flows))
    except Exception:
        return None
    if np.isnan(irr):
        return None
    return irr


def equity_multiple(equity_invested_yen: int, total_distributions_yen: int) -> float:
    if equity_invested_yen <= 0:
        return 0.0
    return total_distributions_yen / equity_invested_yen


def payback_years(equity_invested_yen: int, atcfs_yen: list[int]) -> float | None:
    """累計ATCFが自己資金を超える年数 (線形補間)。回収しないなら None。"""
    if equity_invested_yen <= 0:
        return 0.0
    cumulative = 0
    for i, cf in enumerate(atcfs_yen, start=1):
        prev = cumulative
        cumulative += cf
        if cumulative >= equity_invested_yen:
            # 線形補間: (equity - prev) / (cumulative - prev)
            if cumulative == prev:
                return float(i)
            frac = (equity_invested_yen - prev) / (cumulative - prev)
            return (i - 1) + frac
    return None


def dscr(noi_yen: int, debt_service_yen: int) -> float:
    if debt_service_yen <= 0:
        return float("inf")
    return noi_yen / debt_service_yen


def cap_rate(noi_yen: int, purchase_price_yen: int) -> float:
    if purchase_price_yen <= 0:
        return 0.0
    return noi_yen / purchase_price_yen


def cash_on_cash(btcf_year1_yen: int, equity_yen: int) -> float:
    if equity_yen <= 0:
        return 0.0
    return btcf_year1_yen / equity_yen


def ltv(loan_amount_yen: int, purchase_price_yen: int) -> float:
    if purchase_price_yen <= 0:
        return 0.0
    return loan_amount_yen / purchase_price_yen
