import numpy as np

from macrokit.termstructure import dns, synthetic


def test_loadings_at_the_short_and_long_end():
    load = dns.ns_loadings(np.array([1e-6, 1e6]))
    np.testing.assert_allclose(load[0], [1.0, 1.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(load[1], [1.0, 0.0, 0.0], atol=1e-4)


def test_dns_with_the_true_dynamics_reproduces_the_true_expectation():
    syn = synthetic.dns_dgp(300, np.random.default_rng(25), noise_pct=0.0)
    fit = dns.fit_dns(syn.panel)
    # With no noise the least-squares factors equal the DGP path, so the true VAR
    # parameters must give back the DGP's expectation and short rate.
    mu_true = (np.eye(3) - synthetic.DNS_PHI) @ synthetic.DNS_MEAN
    np.testing.assert_allclose(
        fit.expected(120, mu_true, synthetic.DNS_PHI), syn.expected_pct, atol=1e-10
    )
    np.testing.assert_allclose(fit.factors @ fit.short_loading, syn.short_pct, atol=1e-10)


def test_dns_estimate_tracks_its_own_curve_on_a_long_sample():
    # A fixed-draw pin: the level error comes from the sample mean of the 0.99 factor
    # and is sampling error, so the bound is on correlation and a loose RMSE.
    syn = synthetic.dns_dgp(5000, np.random.default_rng(21))
    fit = dns.fit_dns(syn.panel)
    estimate = fit.expected(120)
    rmse = np.sqrt(((estimate - syn.expected_pct) ** 2).mean())
    assert np.corrcoef(estimate, syn.expected_pct)[0, 1] > 0.99
    assert rmse < 0.2


def test_bootstrap_shape_and_centre():
    syn = synthetic.dns_dgp(400, np.random.default_rng(22))
    fit = dns.fit_dns(syn.panel)
    draws = dns.bootstrap_expected_dns(fit, 120, 100, np.random.default_rng(23))
    assert draws.shape == (100, 400)
    assert abs(np.median(draws[:, -1]) - fit.expected(120)[-1]) < 0.5


def test_decompose_labels_the_model():
    syn = synthetic.dns_dgp(300, np.random.default_rng(24))
    dec = dns.decompose_dns(syn.panel, dns.fit_dns(syn.panel), maturity=60)
    assert dec.model == "dns"
    np.testing.assert_array_equal(dec.yield_pct, syn.panel.column(60))
    assert dec.expected_pct.shape == (300,)
