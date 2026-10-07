"""Hull §7.12 introductory CDS cash, not a calibrated CDS valuation."""

import pytest
from hullkit import _swap_foundations as s


def test_source_two_cds_amounts():
    a = s.intro_cds_cash(1e8, 0.012, 0.4)
    assert [a["annual_premium"], a["protection"]] == pytest.approx([1.2e6, 60e6])


def test_independent_bond_recovery_and_protection_cash():
    for recovery in [0, 0.4, 1]:
        a = s.intro_cds_cash(1e8, 0.012, recovery)
        bond_recovery = 1e8 * recovery
        assert bond_recovery + a["protection"] == pytest.approx(1e8)
    a = s.intro_cds_cash(1e8, 0.012, 0.4)
    assert 4 * a["annual_premium"] * 0.25 == pytest.approx(1.2e6)
