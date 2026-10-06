"""Hull §25.1 simplified contractual year fractions, not calendar day counts."""

from decimal import Decimal

import numpy as np
import pytest
from hullkit import _credit_contracts as c


def test_source_quarterly_premium_default_protection_and_accrual():
    result = c.cds_contract_cashflows(100e6, 0.009, 5, default_time=1 + 2 / 12, recovery=0.35)
    assert result["regular_premium_rate"] * 10000 == pytest.approx(22.5)
    assert result["regular_premium"] == pytest.approx(225000)
    assert result["protection"][-1] == pytest.approx(65e6)
    assert result["premium"][-1] == pytest.approx(150000)
    assert c.basis_points_to_rate(250) == pytest.approx(0.025)
    assert c.basis_points_to_rate(260) == pytest.approx(0.026)
    assert c.cds_bond_basis(0.02, 0.07, 0.05)["protected_yield"] == pytest.approx(0.05)
    assert result["buyer_cashflows"][-1] == pytest.approx(
        float(Decimal("100000000") * (Decimal(1) - Decimal("0.35")) - Decimal("150000"))
    )


def test_alive_default_and_exact_payment_date_cashflow_signs():
    alive = c.cds_contract_cashflows(100, 0.02, 1)
    assert alive["premium"].sum() == pytest.approx(2)
    assert alive["protection"].sum() == 0
    default = c.cds_contract_cashflows(100, 0.02, 1, default_time=0.5, recovery=0.4)
    assert default["times"] == pytest.approx([0.25, 0.5])
    assert default["premium"] == pytest.approx([0.5, 0.5])
    assert default["protection"] == pytest.approx([0, 60])
    # Par recovery on bond plus CDS's loss-of-par payment restores par at default.
    assert default["protection"][-1] + 40 == pytest.approx(100)
    assert default["buyer_cashflows"] == pytest.approx(-default["seller_cashflows"])


def test_cds_basis_uses_yield_spread_and_preserves_negative_basis():
    result = c.cds_bond_basis(0.015, 0.07, 0.05)
    assert result["basis"] == pytest.approx(-0.005)
    assert np.isfinite(result["protected_yield"])
    with pytest.raises(ValueError):
        c.cds_contract_cashflows(100, 0.02, 1, default_time=-1)
