"""quantkit.tax — Japan-resident after-tax returns (taxable vs NISA).

:class:`~quantkit.tax.japan.TaxConfig` carries the rate assumptions (from
``configs/tax_japan.yaml``); :func:`~quantkit.tax.japan.annual_after_tax` applies an
annual mark-to-market capital-gains tax with 3-year loss carryforward;
:func:`~quantkit.tax.japan.compare_accounts` lays pre-tax vs taxable vs NISA side by
side (CAGR, tax paid, drag). Rates are assumptions, shown in reports — not advice.
"""

from __future__ import annotations

from .japan import (
    TaxConfig,
    after_tax_cagr,
    after_tax_equity,
    annual_after_tax,
    compare_accounts,
)

__all__ = [
    "TaxConfig",
    "after_tax_cagr",
    "after_tax_equity",
    "annual_after_tax",
    "compare_accounts",
]
