"""Japan-resident after-tax returns (capital gains + loss carryforward; NISA).

Tax rates are ASSUMPTIONS held in ``configs/tax_japan.yaml`` (never hard-coded)
and must be shown in any report. The model is **annual mark-to-market** with a
3-year loss carryforward: each Japanese tax year (calendar year) its compounded
return is treated as realized, gains are offset by banked losses (oldest first),
and the rest taxed at ``capital_gains_rate``. That is conservative for a long-term
holder (real tax is on realized lots, deferring the drag), and exact for a fully
turned-over book. A NISA account applies zero tax (its annual/lifetime quota is
NOT modeled here — this is return-space, not yen-space).

Not tax advice; verify against current NTA rules before relying on numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TaxConfig:
    capital_gains_rate: float = 0.20315
    dividend_rate: float = 0.20315
    us_dividend_withholding: float = 0.10
    loss_carryforward_years: int = 3
    name: str = "taxable"

    @classmethod
    def from_config(cls, cfg: dict) -> TaxConfig:
        t = (cfg or {}).get("taxable_account", {})
        return cls(
            capital_gains_rate=float(t.get("capital_gains_rate", 0.20315)),
            dividend_rate=float(t.get("dividend_rate", 0.20315)),
            us_dividend_withholding=float(t.get("us_dividend_withholding", 0.10)),
            loss_carryforward_years=int(t.get("loss_carryforward_years", 3)),
            name="taxable",
        )

    @classmethod
    def nisa(cls) -> TaxConfig:
        """A NISA account: gains and dividends are tax-free."""
        return cls(0.0, 0.0, 0.0, loss_carryforward_years=0, name="nisa")


def annual_after_tax(returns: pd.Series, tax: TaxConfig) -> pd.DataFrame:
    """Per-tax-year gross vs after-tax return, with loss carryforward.

    Returns a frame indexed by calendar year with columns ``gross_return``,
    ``taxable_gain``, ``tax`` and ``after_tax_return``. Losses are banked and
    offset future gains (oldest first) until they expire after
    ``loss_carryforward_years``.
    """
    r = returns.dropna()
    if r.empty:
        return pd.DataFrame(columns=["gross_return", "taxable_gain", "tax", "after_tax_return"])
    yearly = (1.0 + r).groupby(r.index.year).prod() - 1.0
    lcf = tax.loss_carryforward_years
    bank: list[list[float]] = []  # [origin_year, remaining_loss]
    rows = []
    for year, g in yearly.items():
        bank = [e for e in bank if (year - e[0]) <= lcf and e[1] > 1e-12]
        taxable_gain, tax_amt = 0.0, 0.0
        if g > 0:
            need = g
            for entry in bank:  # offset with banked losses, oldest first
                use = min(entry[1], need)
                entry[1] -= use
                need -= use
                if need <= 0:
                    break
            taxable_gain = max(0.0, need)
            tax_amt = tax.capital_gains_rate * taxable_gain
        elif g < 0:
            bank.append([year, -g])
        rows.append(
            {
                "gross_return": g,
                "taxable_gain": taxable_gain,
                "tax": tax_amt,
                "after_tax_return": g - tax_amt,
            }
        )
    out = pd.DataFrame(rows, index=pd.Index(yearly.index, name="year"))
    return out


def _cagr(yearly_returns: pd.Series) -> float:
    yr = yearly_returns.dropna()
    if yr.empty:
        return float("nan")
    growth = float((1.0 + yr).prod())
    return growth ** (1.0 / len(yr)) - 1.0 if growth > 0 else -1.0


def after_tax_cagr(returns: pd.Series, tax: TaxConfig) -> float:
    return _cagr(annual_after_tax(returns, tax)["after_tax_return"])


def after_tax_equity(returns: pd.Series, tax: TaxConfig) -> pd.Series:
    """Annual after-tax growth-of-1 curve (one point per tax year)."""
    df = annual_after_tax(returns, tax)
    eq = (1.0 + df["after_tax_return"]).cumprod()
    eq.name = tax.name
    return eq


def compare_accounts(returns: pd.Series, taxable: TaxConfig) -> pd.Series:
    """Pre-tax vs taxable vs NISA: CAGR, total tax paid, and the annual tax drag."""
    df_tax = annual_after_tax(returns, taxable)
    pretax = _cagr(df_tax["gross_return"])
    taxable_cagr = _cagr(df_tax["after_tax_return"])
    nisa_cagr = after_tax_cagr(returns, TaxConfig.nisa())
    return pd.Series(
        {
            "pretax_cagr": pretax,
            "taxable_cagr": taxable_cagr,
            "nisa_cagr": nisa_cagr,
            "total_tax_paid": float(df_tax["tax"].sum()),
            "annual_tax_drag": pretax - taxable_cagr if not np.isnan(pretax) else float("nan"),
        }
    )
