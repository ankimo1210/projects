"""Structural + numerical tests for the johnhull Plotly builders.

These exercise every ``plotly_*`` helper (a broken builder fails here, mirroring
``analytics/report``'s end-to-end test) and pin a couple of finance facts that
must show up in the figure data (tree -> BSM, VaR monotone in confidence).
"""

from itertools import pairwise

import numpy as np
from hullkit import bsm
from hullkit import plotly_viz as pv

BUILDERS = [
    pv.plotly_strategy_payoffs,
    pv.plotly_delta_vs_spot,
    pv.plotly_delta_hedge_cost,
    pv.plotly_tree_convergence,
    pv.plotly_var_es,
    pv.plotly_credit_survival,
    pv.plotly_quadratic_variation,
    pv.plotly_ito_correction,
    pv.plotly_girsanov,
    pv.plotly_heston_smile,
    pv.plotly_cos_density_convergence,
    pv.plotly_sabr_smile,
    pv.plotly_mc_variance_reduction,
    pv.plotly_qmc_vs_pseudo,
    pv.plotly_american_boundary,
    pv.plotly_exposure_profile,
    pv.plotly_portfolio_loss_correlation,
    pv.plotly_copula_scatter,
    pv.plotly_gamma_surface,
    pv.plotly_stop_loss_vs_delta_hedge,
    pv.plotly_binomial_lattice,
    pv.plotly_garch_volatility,
    pv.plotly_garch_term_structure,
    pv.plotly_merton_structural,
    pv.plotly_portfolio_diversification,
    pv.plotly_yield_curve,
    pv.plotly_bond_convexity,
    pv.plotly_swap_value,
    pv.plotly_barrier_knockout,
    pv.plotly_asian_vs_european,
]


def test_every_builder_returns_a_figure():
    for fn in BUILDERS:
        fig = fn()
        assert fig.__class__.__name__ == "Figure"
        assert len(fig.data) >= 1


def test_interactive_builders_have_a_control():
    # payoffs uses a dropdown (updatemenus); the rest use a slider.
    assert pv.plotly_strategy_payoffs().layout.updatemenus
    for fn in (
        pv.plotly_delta_vs_spot,
        pv.plotly_delta_hedge_cost,
        pv.plotly_var_es,
        pv.plotly_credit_survival,
        pv.plotly_quadratic_variation,
        pv.plotly_ito_correction,
        pv.plotly_girsanov,
        pv.plotly_heston_smile,
        pv.plotly_cos_density_convergence,
        pv.plotly_sabr_smile,
        pv.plotly_american_boundary,
        pv.plotly_exposure_profile,
        pv.plotly_portfolio_loss_correlation,
        pv.plotly_copula_scatter,
        pv.plotly_stop_loss_vs_delta_hedge,
        pv.plotly_merton_structural,
        pv.plotly_yield_curve,
        pv.plotly_barrier_knockout,
    ):
        assert fn().layout.sliders, fn.__name__


def test_tree_converges_to_bsm():
    fig = pv.plotly_tree_convergence()
    tree, bsm_line = fig.data[0], fig.data[1]
    # the BSM reference line is flat at the closed-form price
    assert np.allclose(bsm_line.y, bsm_line.y[0])
    # high-N tree price is within a cent of the closed form
    assert abs(tree.y[-1] - bsm_line.y[0]) < 0.05


def test_delta_curve_steepens_as_maturity_shrinks():
    fig = pv.plotly_delta_vs_spot(K=100.0)
    # data traces are ordered by decreasing T (1.0 .. 0.02); the shortest-dated
    # delta should span a wider range (closer to a 0/1 step) than the longest.
    longest, shortest = fig.data[0], fig.data[-1]
    assert (shortest.y.max() - shortest.y.min()) > (longest.y.max() - longest.y.min())


def test_var_increases_with_confidence():
    fig = pv.plotly_var_es()
    var_x = [tr.x[0] for tr in fig.data if tr.name.startswith("VaR")]
    # VaR lines sit at x = -VaR (left tail); higher confidence => more negative.
    assert all(b < a for a, b in pairwise(var_x)), var_x


def test_ito_correction_concentrates_on_half_t():
    # the figure plots (midpoint - left) = ½[W]_t; it must center on ½T and
    # tighten as the mesh refines (the deterministic Itô correction).
    fig = pv.plotly_ito_correction(T=1.0)
    coarse, fine = fig.data[0].x, fig.data[3].x  # n=8 vs n=512
    assert abs(float(np.mean(fine)) - 0.5) < 0.02
    assert float(np.std(fine)) < float(np.std(coarse))


def test_girsanov_q_price_invariant_across_drift():
    # the headline claim: self-normalized Q call price stays at BSM for every μ.
    fig = pv.plotly_girsanov()
    prices = [
        float(s["args"][1]["title.text"].split("≈")[1].split("(")[0])
        for s in fig.layout.sliders[0].steps
    ]
    assert max(prices) - min(prices) < 0.05  # invariant to the real-world drift


def test_delta_hedge_centers_on_bsm_price():
    # rebuild the finest-rebalance cost and confirm its mean ~ the BSM price the
    # figure annotates (Hull §19.4: hedging cost -> option value).
    rng = np.random.default_rng(pv.SEED)
    from hullkit import hedging

    S0, K, r, sigma, T = 49.0, 50.0, 0.05, 0.20, 20.0 / 52.0
    cost = hedging.simulate_delta_hedge(S0, K, r, sigma, T, 52, 4000, rng=rng)
    assert abs(cost.mean() - bsm.call_price(S0, K, r, sigma, T)) < 0.10
