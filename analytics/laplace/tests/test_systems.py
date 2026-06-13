"""Tests for laplace_book.systems (transfer functions, stability, responses)."""

import numpy as np
from laplace_book import systems as S


def test_first_order_pole_gain_timeconstant():
    sys = S.first_order(tau=2.0, gain=3.0)
    np.testing.assert_allclose(S.poles(sys), [-0.5], atol=1e-12)
    assert abs(S.dc_gain(sys) - 3.0) < 1e-12
    assert abs(S.time_constant(sys) - 2.0) < 1e-12


def test_first_order_step_reaches_gain_and_one_tau():
    tau, gain = 2.0, 1.0
    sys = S.first_order(tau, gain)
    t = np.linspace(0, 20, 2000)
    y = S.step_response(sys, t)
    assert abs(y[-1] - gain) < 1e-2  # settles to DC gain
    # at t = tau the first-order step is gain*(1 - 1/e).
    k = int(np.argmin(np.abs(t - tau)))
    assert abs(y[k] - gain * (1 - np.exp(-1))) < 1e-2


def test_second_order_params_roundtrip():
    wn, zeta = 2.5, 0.4
    sys = S.second_order(wn, zeta)
    wn2, zeta2 = S.second_order_params(sys)
    assert abs(wn2 - wn) < 1e-9
    assert abs(zeta2 - zeta) < 1e-9


def test_stability_classification():
    assert S.classify_stability(S.first_order(1.0)) == "stable"
    assert S.is_stable(S.first_order(1.0))
    assert S.classify_stability(S.tf([1.0], [1.0, -1.0])) == "unstable"  # pole at +1
    assert S.classify_stability(S.tf([1.0], [1.0, 0.0, 1.0])) == "marginal"  # poles +/- i
    assert not S.is_stable(S.tf([1.0], [1.0, -1.0]))


def test_impulse_response_first_order_initial_value():
    tau = 0.5
    sys = S.first_order(tau)
    t = np.linspace(0, 5, 4000)
    h = S.impulse_response(sys, t)
    # h(t) = (1/tau) e^{-t/tau}; h(0) = 1/tau.
    assert abs(h[0] - 1.0 / tau) < 1e-2


def test_convolution_theorem_numeric():
    # (e^{-t} * e^{-2t})(t) = e^{-t} - e^{-2t}  (analytic), matching L^{-1}{F G}.
    dt = 0.005
    t = np.arange(0, 12, dt)
    f = np.exp(-t)
    g = np.exp(-2 * t)
    conv = S.convolve(f, g, dt)
    analytic = np.exp(-t) - np.exp(-2 * t)
    assert np.max(np.abs(conv - analytic)) < 2e-2


def test_feedback_unity():
    # Unity feedback of G = 1/(tau s + 1) gives 1/(tau s + 2): DC gain 1/2.
    G = S.first_order(tau=3.0)
    H = S.feedback(G)
    np.testing.assert_allclose(
        np.atleast_1d(H.den) / H.den[0], [3.0, 2.0] / np.array(3.0), atol=1e-9
    )
    assert abs(S.dc_gain(H) - 0.5) < 1e-12


def test_series_polynomial():
    H = S.series(S.tf([1.0], [1.0, 1.0]), S.tf([1.0], [1.0, 2.0]))
    np.testing.assert_allclose(np.atleast_1d(H.num), [1.0], atol=1e-12)
    np.testing.assert_allclose(np.atleast_1d(H.den), [1.0, 3.0, 2.0], atol=1e-12)


def test_root_locus_classic_integrator_plant():
    # G = 1/(s(s+1)): poles at 0,-1 (k=0); break away to -0.5 +/- j*... as k grows.
    G = S.tf([1.0], [1.0, 1.0, 0.0])
    _, locus = S.root_locus(G, [0.0, 0.25, 1.0])
    np.testing.assert_allclose(np.sort(locus[0]), [-1.0, 0.0], atol=1e-9)  # open-loop poles
    np.testing.assert_allclose(np.sort(locus[1]), [-0.5, -0.5], atol=1e-9)  # breakaway (double)
    np.testing.assert_allclose(
        np.sort_complex(locus[2]),
        np.sort_complex([-0.5 + 0.8660254j, -0.5 - 0.8660254j]),
        atol=1e-6,
    )


def test_root_locus_destabilizes():
    # G = 1/((s+1)(s+2)(s+3)): for large enough k a branch crosses into the RHP.
    G = S.tf([1.0], np.poly([-1.0, -2.0, -3.0]))
    _, locus = S.root_locus(G, [1.0, 100.0])
    assert np.all(locus[0].real < 0)  # low gain: stable
    assert np.any(locus[1].real > 0)  # high gain: a pole in the RHP


def test_routh_hurwitz_matches_root_count():
    for den in ([1, 3, 2], [1, 1, 1, 6], [1, 6, 11, 6], [1, 6, 11, 106]):
        stable, n_rhp, _ = S.routh_hurwitz(den)
        truth = int(np.sum(np.roots(den).real > 1e-9))
        assert n_rhp == truth
        assert stable == (truth == 0)


def test_partial_fraction_numeric_reconstructs():
    # 1/((s+1)(s+2)) = 1/(s+1) - 1/(s+2); value at s=0 must be 1/((1)(2)) = 0.5.
    r, p, k = S.partial_fraction_numeric([1.0], [1.0, 3.0, 2.0])
    val = sum(ri / (0.0 - pi) for ri, pi in zip(r, p, strict=True)) + (
        np.polyval(k, 0.0) if len(k) else 0.0
    )
    assert abs(val - 0.5) < 1e-9


def test_gain_phase_margin_known_systems():
    m1 = S.gain_phase_margin(S.tf([1.0], [1.0, 1.0, 0.0]))  # 1/(s(s+1))
    assert abs(m1["phase_margin_deg"] - 51.83) < 0.5
    assert np.isinf(m1["gain_margin"])  # phase never reaches -180 for a 2-pole type-1
    # 1/((s+1)(s+2)(s+3)) destabilizes at k=60, so its gain margin is ~60.
    m2 = S.gain_phase_margin(S.tf([1.0], np.poly([-1.0, -2.0, -3.0])))
    assert abs(m2["gain_margin"] - 60.0) < 1.0


def test_pid_pi_controller():
    K = S.pid(kp=2.0, ki=1.0)  # 2 + 1/s (proper: no derivative term)
    assert abs(S.evaluate(K, 1.0) - 3.0) < 1e-9  # K(1) = 2 + 1
    assert abs(S.evaluate(K, 0.5) - 4.0) < 1e-9  # K(0.5) = 2 + 2
