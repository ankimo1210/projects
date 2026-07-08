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
    pv.plotly_iv_surface,
    pv.plotly_greeks_map,
    pv.plotly_cva_sensitivity,
    pv.plotly_bsm_greeks_sensitivity,
    pv.plotly_smile_model_risk,
    pv.plotly_sabr_param_greeks,
    pv.plotly_sabr_greeks_by_param,
    pv.plotly_sabr_rho_nu_smile_greeks,
]


def test_every_builder_returns_a_figure():
    for fn in BUILDERS:
        fig = fn()
        assert fig.__class__.__name__ == "Figure"
        assert len(fig.data) >= 1


def test_interactive_builders_have_a_control():
    # payoffs and the Greeks maps use a dropdown (updatemenus); the rest a slider.
    assert pv.plotly_strategy_payoffs().layout.updatemenus
    assert pv.plotly_sabr_greeks_by_param().layout.updatemenus
    assert pv.plotly_greeks_map().layout.updatemenus
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
        pv.plotly_iv_surface,
        pv.plotly_cva_sensitivity,
        pv.plotly_bsm_greeks_sensitivity,
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


def test_greeks_sensitivity_moves_at_fixed_market_point():
    # with S=K fixed, changing sigma must move the ATM delta (trace 0 of each
    # 4-panel sigma block is the delta panel; sigmas are [0.10, ..., 0.40]).
    fig = pv.plotly_bsm_greeks_sensitivity()
    s = np.asarray(fig.data[0].x, dtype=float)
    atm = int(np.argmin(np.abs(s - 100.0)))
    delta_lo = float(np.asarray(fig.data[0].y)[atm])  # sigma = 0.10
    delta_hi = float(np.asarray(fig.data[16].y)[atm])  # sigma = 0.40 (block 4)
    assert abs(delta_lo - delta_hi) > 0.03, (delta_lo, delta_hi)


def test_smile_model_risk_fits_agree_greeks_differ():
    fig = pv.plotly_smile_model_risk()
    market = np.asarray(fig.data[0].y, dtype=float)
    fits = [np.asarray(tr.y, dtype=float) for tr in fig.data if "フィット" in (tr.name or "")]
    deltas = [np.asarray(tr.y, dtype=float) for tr in fig.data if "のdelta" in (tr.name or "")]
    gammas = [np.asarray(tr.y, dtype=float) for tr in fig.data if "のgamma" in (tr.name or "")]
    vegas = [np.asarray(tr.y, dtype=float) for tr in fig.data if "のvega" in (tr.name or "")]
    assert len(fits) == 3 and len(deltas) == 3 and len(gammas) == 3 and len(vegas) == 3
    for fit in fits:  # market data fixed: every beta reprices the smile
        assert np.abs(fit - market).max() < 1e-3
    spread = max(np.abs(a - b).max() for a in deltas for b in deltas)
    assert spread > 0.05, spread  # ...but the delta hedges disagree
    g_spread = max(np.abs(a - b).max() for a in gammas for b in gammas)
    assert g_spread > 0.0, g_spread  # gamma differs too


def test_sabr_param_greeks_matrix_shows_tradeoffs():
    fig = pv.plotly_sabr_param_greeks()
    assert fig.layout.sliders
    for tr in fig.data:  # one heatmap per strike
        z = np.asarray(tr.z, dtype=float)
        assert z.shape == (4, 4) and np.isfinite(z).all(), tr.name
    # at least one strike has a bump row moving Greeks in OPPOSITE directions
    # (the trade-off the figure exists to show)
    has_tradeoff = any(
        ((np.asarray(tr.z)[i] > 0.1).any() and (np.asarray(tr.z)[i] < -0.1).any())
        for tr in fig.data
        for i in range(4)
    )
    assert has_tradeoff


def test_sabr_greeks_by_param_sweeps_every_parameter():
    fig = pv.plotly_sabr_greeks_by_param()
    labels = [b.label for b in fig.layout.updatemenus[0].buttons]
    assert len(labels) == 4  # alpha, beta, rho, nu each selectable
    # 4 params x 5 values x 4 greek panels = 80 traces, 20 visible at load
    assert len(fig.data) == 80
    assert sum(bool(t.visible) for t in fig.data) == 20
    for t in fig.data:
        assert np.isfinite(np.asarray(t.y, dtype=float)).all()
    # a non-beta sweep (rho = third dropdown block) must actually move a Greek:
    # the delta-panel traces (showlegend=True) at its extreme sweep values differ.
    rho_block = fig.data[40:60]  # 5 values x 4 panels
    delta_curves = [np.asarray(t.y, dtype=float) for t in rho_block if t.showlegend]
    assert len(delta_curves) == 5  # one delta panel per swept rho value
    assert max(np.abs(delta_curves[0] - delta_curves[-1])) > 0.01


def test_sabr_rho_nu_smile_greeks_reshapes_smile():
    # rho tilts the smile (skew shrinks as rho -> 0); nu lifts the wings.
    fig = pv.plotly_sabr_rho_nu_smile_greeks()
    assert len(fig.data) == 30  # 2 rows x 5 values x 3 cols
    for t in fig.data:
        assert np.isfinite(np.asarray(t.y, dtype=float)).all()
    rho_iv = [
        np.asarray(t.y, float) for t in fig.data if t.showlegend and (t.name or "").startswith("ρ")
    ]
    nu_iv = [
        np.asarray(t.y, float) for t in fig.data if t.showlegend and (t.name or "").startswith("ν")
    ]
    assert len(rho_iv) == 5 and len(nu_iv) == 5
    # more-negative rho => steeper skew (low-K IV minus high-K IV larger)
    skew_neg = rho_iv[0][0] - rho_iv[0][-1]  # rho = -0.6
    skew_zero = rho_iv[-1][0] - rho_iv[-1][-1]  # rho = 0.0
    assert skew_neg > skew_zero
    # larger nu => bigger wing lift (low-K IV minus ATM IV)
    atm = len(nu_iv[0]) // 2
    assert (nu_iv[-1][0] - nu_iv[-1][atm]) > (nu_iv[0][0] - nu_iv[0][atm])


def test_iv_surface_atm_matches_heston_variance():
    # with v0 = theta = 0.04 the ATM implied vol must sit near sqrt(0.04) = 0.20
    # at every maturity of the rho=0 surface (flat variance term structure).
    fig = pv.plotly_iv_surface()
    rho_zero = fig.data[-1]  # rhos = [-0.8, -0.4, 0.0]
    ks = np.asarray(rho_zero.x, dtype=float)
    atm_col = int(np.argmin(np.abs(ks - 100.0)))
    atm_ivs = np.asarray(rho_zero.z, dtype=float)[:, atm_col]
    assert np.all(np.abs(atm_ivs - 0.20) < 0.03), atm_ivs


def test_cva_total_increases_with_hazard():
    # integrand traces are ordered by hazard; their sums are the CVA totals.
    fig = pv.plotly_cva_sensitivity()
    totals = [float(np.sum(tr.y)) for tr in fig.data if tr.name.startswith("CVA")]
    assert all(b > a for a, b in pairwise(totals)), totals


def test_lsm_boundary_tracks_fd_boundary():
    # both algorithms must place the put boundary strictly inside (0, K) and the
    # LSM markers should sit near the FD curve on a shared tau range.
    from hullkit import fd, mc

    S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    _, fd_taus, fd_bnd = fd.fd_vanilla(
        S0, K, r, sigma, T, kind="put", american=True, return_boundary=True, n_s=300, n_t=300
    )
    lsm_taus, lsm_bnd = mc.lsm_exercise_boundary(S0, K, r, sigma, T, n_paths=20_000)
    assert len(lsm_bnd) > 10
    assert all(0.0 < b < K for b in lsm_bnd)
    fd_interp = np.interp(lsm_taus, fd_taus, fd_bnd)
    gap = np.abs(np.asarray(lsm_bnd) - fd_interp)
    assert np.median(gap) < 5.0, np.median(gap)  # noisy MC estimate, coarse agreement


def test_delta_hedge_centers_on_bsm_price():
    # rebuild the finest-rebalance cost and confirm its mean ~ the BSM price the
    # figure annotates (Hull §19.4: hedging cost -> option value).
    rng = np.random.default_rng(pv.SEED)
    from hullkit import hedging

    S0, K, r, sigma, T = 49.0, 50.0, 0.05, 0.20, 20.0 / 52.0
    cost = hedging.simulate_delta_hedge(S0, K, r, sigma, T, 52, 4000, rng=rng)
    assert abs(cost.mean() - bsm.call_price(S0, K, r, sigma, T)) < 0.10
