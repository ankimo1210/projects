import numpy as np
import pandas as pd
import pytest
from bond_timing.evaluate import (
    Evidence,
    cer,
    diff_test,
    holm,
    prevailing_mean,
    r2_oos,
    sharpe,
    stationary_indices,
    verdict,
)


def test_cer_follows_the_design_formula():
    assert cer([0.01, 0.03]) == pytest.approx(12 * (0.02 - 2.5 * 0.0002))


def test_sharpe_of_a_flat_series_is_zero():
    assert sharpe(np.zeros(24)) == 0.0
    assert sharpe([0.01, 0.03]) == pytest.approx(np.sqrt(12) * 0.02 / np.std([0.01, 0.03], ddof=1))


def test_stationary_indices_are_reproducible_and_in_range():
    a = stationary_indices(50, 200, 12, np.random.default_rng(7))
    np.testing.assert_array_equal(a, stationary_indices(50, 200, 12, np.random.default_rng(7)))
    assert a.min() >= 0 and a.max() < 50 and a.shape == (200, 50)
    restarts = (np.diff(a, axis=1) != 1) & ~((a[:, :-1] == 49) & (a[:, 1:] == 0))
    assert 8 < 1 / restarts.mean() < 16  # mean block length near 12
    assert stationary_indices(10, 3, 12, np.random.default_rng(0), length=25).shape == (3, 25)


def test_identical_strategies_have_p_one():
    r = pd.Series(np.random.default_rng(0).normal(0.004, 0.02, 120))
    result = diff_test(r, r, n_boot=500)
    assert result.delta_cer == 0.0 and result.p_cer == 1.0 and result.p_sharpe == 1.0


def test_a_clearly_better_strategy_is_significant():
    base = pd.Series(np.random.default_rng(1).normal(0.0, 0.02, 228))
    result = diff_test(base + 0.01, base, n_boot=2000)
    assert result.delta_cer == pytest.approx(0.12)
    assert result.p_cer < 0.01 and result.months == 228


def test_holm_matches_a_worked_example():
    adjusted = holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.005})
    assert adjusted == pytest.approx({"d": 0.02, "a": 0.03, "c": 0.06, "b": 0.06})


def test_r2_oos_and_prevailing_mean():
    index = pd.period_range("2000-01", periods=40, freq="M")
    y = pd.Series(np.arange(40.0), index=index)
    decisions = index[20:30]
    bench = prevailing_mean(y, decisions, 12)
    assert bench.iloc[0] == pytest.approx(np.mean(np.arange(9.0)))  # s <= t - 12
    loose = prevailing_mean(y, decisions, 12, complete=False)
    assert loose.iloc[0] == pytest.approx(np.mean(np.arange(20.0)))  # s <= t - 1
    assert r2_oos(y.reindex(decisions), y.reindex(decisions), bench) == 1.0


def ml(**changes) -> Evidence:
    values = {
        "p_vs_hold": 0.01,
        "robust_vs_hold": True,
        "oos_b_vs_hold": 0.01,
        "p_vs_p1": 0.01,
        "robust_vs_p1": True,
        "oos_b_vs_p1": 0.01,
        "g3_p": 0.01,
    }
    values.update(changes)
    return Evidence(**values)


def evidence(**changes) -> dict[str, Evidence]:
    weak = Evidence(p_vs_hold=0.2, robust_vs_hold=True, oos_b_vs_hold=0.01)
    base = {"P1": weak, "P2": weak, "P3": weak, "P4": ml(), "P5": ml(p_vs_hold=0.2)}
    base.update(changes)
    return base


def test_verdict_branches():
    assert verdict(evidence()) == "ml_signal_usable"
    no_g3 = ml(g3_p=0.2)
    assert verdict(evidence(P4=no_g3)) == "no_usable_signal"
    assert verdict(evidence(P4=ml(oos_b_vs_p1=-0.001))) == "no_usable_signal"
    assert verdict(evidence(P4=ml(robust_vs_p1=False))) == "no_usable_signal"
    simple = Evidence(p_vs_hold=0.01, robust_vs_hold=True, oos_b_vs_hold=0.002)
    assert verdict(evidence(P4=no_g3, P2=simple)) == "simple_rule_usable"
    fragile = Evidence(p_vs_hold=0.01, robust_vs_hold=False, oos_b_vs_hold=0.002)
    assert verdict(evidence(P4=no_g3, P2=fragile)) == "no_usable_signal"
    late_loss = Evidence(p_vs_hold=0.01, robust_vs_hold=True, oos_b_vs_hold=-0.001)
    assert verdict(evidence(P4=no_g3, P2=late_loss)) == "no_usable_signal"
