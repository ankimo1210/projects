import numpy as np
import pytest
from timesfm_lab.baselines import QUANTILE_LEVELS
from timesfm_lab.datasets import SPEC_BY_KEY, SYNTHETIC_SPECS, build_windows
from timesfm_lab.synthetic import PROCESS_BY_KEY, PROCESSES


@pytest.mark.parametrize("proc", PROCESSES, ids=lambda p: p.key)
def test_every_process_generates_finite_paths_and_futures(proc):
    rng = np.random.default_rng(0)
    values, aux = proc.generate(rng, 700)
    assert values.shape == (700,)
    assert np.isfinite(values).all()
    paths = proc.simulate(aux, 600, 24, rng)
    assert paths.shape[1] == 24
    assert np.isfinite(paths).all()


def test_random_walk_optimum_is_the_last_value():
    """The whole ceiling argument rests on the oracle being the real optimum."""
    spec = SPEC_BY_KEY["syn_random_walk"]
    for w in build_windows(spec)[:25]:
        want = np.repeat(float(w.context[-1]), len(w.actual))
        np.testing.assert_allclose(w.oracle_point, want, atol=1e-3)


def test_ar1_optimum_decays_geometrically_to_the_mean():
    spec = SPEC_BY_KEY["syn_ar1"]
    proc = PROCESS_BY_KEY["syn_ar1"]
    for w in build_windows(spec)[:25]:
        h = np.arange(1, len(w.actual) + 1)
        want = proc.mu + proc.phi**h * (float(w.context[-1]) - proc.mu)
        np.testing.assert_allclose(w.oracle_point, want, atol=1e-3)


def test_the_chaotic_process_has_a_zero_error_ceiling():
    """A deterministic map has no irreducible noise, so the optimum is exact."""
    spec = SPEC_BY_KEY["syn_chaos"]
    ws = build_windows(spec)
    err = max(float(np.abs(w.oracle_point - w.actual).max()) for w in ws)
    assert err < 1e-9, err
    # ...and its fan is degenerate, because there is nothing to be uncertain about
    for w in ws[:5]:
        assert float(np.ptp(w.oracle_quantiles, axis=1).max()) < 1e-9


def test_oracle_quantile_fans_are_well_formed():
    for spec in SYNTHETIC_SPECS:
        w = build_windows(spec)[0]
        q = w.oracle_quantiles
        assert q.shape == (spec.horizon, len(QUANTILE_LEVELS))
        assert (np.diff(q, axis=1) >= -1e-9).all(), spec.key
        # The mean is never below the 10th percentile for any of these processes.
        assert (q[:, 0] <= w.oracle_point + 1e-9).all(), spec.key


def test_the_intermittent_mean_and_median_disagree_by_construction():
    """Why the ceiling has to be the median: on sparse demand the two diverge.

    When the arrival rate is under 10%, over 90% of the mass sits on the atom at
    zero. The median is then 0 — and 0 is what minimises absolute error — while
    the expected value is a positive number no realisation ever takes.
    """
    proc = PROCESS_BY_KEY["syn_intermittent"]
    rng = np.random.default_rng(0)
    _values, aux = proc.generate(rng, 700)
    paths = proc.simulate(aux, 600, 48, rng)
    mean, median = paths.mean(axis=0), np.median(paths, axis=0)
    assert (median == 0.0).any()
    assert (mean > median + 1e-9).all()
    # and the median really is the better absolute-error summary
    truth = paths[0]
    assert np.abs(truth - median).mean() < np.abs(truth - mean).mean()


def test_the_oracle_beats_every_baseline_on_its_own_process():
    """If anything beats the ceiling, the ceiling is defined wrong.

    This is the test that caught the optimum being the conditional mean rather
    than the median: on the intermittent process the "optimum" was losing by a
    wide margin, which is impossible for a genuine optimum.
    """
    from timesfm_lab.baselines import BASELINES
    from timesfm_lab.metrics import mae

    for spec in SYNTHETIC_SPECS:
        key = spec.key
        ws = build_windows(spec)[:30]
        oracle = np.mean([mae(w.actual, w.oracle_point) for w in ws])
        for name, fn in BASELINES.items():
            got = np.mean([mae(w.actual, fn(w.context, spec.horizon, spec.season).point) for w in ws])
            assert oracle <= got * 1.02, f"{key}: {name} ({got:.3f}) beat the optimum ({oracle:.3f})"


def test_generation_is_deterministic_and_processes_do_not_share_a_path():
    a = [w.uid for w in build_windows(SPEC_BY_KEY["syn_seasonal"], seed=3)]
    b = [w.uid for w in build_windows(SPEC_BY_KEY["syn_seasonal"], seed=3)]
    assert a == b
    x = build_windows(SPEC_BY_KEY["syn_seasonal"], seed=3)[0].context
    y = build_windows(SPEC_BY_KEY["syn_heteroskedastic"], seed=3)[0].context
    assert not np.allclose(x, y)


def test_synthetic_series_are_identical_across_processes():
    """Reproducibility must survive a fresh interpreter, not just a fresh call.

    Seeding from ``hash(key)`` looked deterministic inside one run and silently
    regenerated different series on the next, because Python randomises string
    hashing per process. This runs the generator in a subprocess to catch that.
    """
    import subprocess
    import sys

    code = (
        "import numpy as np;"
        "from timesfm_lab.datasets import SPEC_BY_KEY, build_windows;"
        "w=build_windows(SPEC_BY_KEY['syn_seasonal'])[0];"
        "print(float(np.asarray(w.context, float).sum()))"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True,
            env={"PYTHONHASHSEED": str(h), "PATH": "/usr/bin:/bin"},
        ).stdout.strip()
        for h in (0, 1, 2)
    }
    assert len(runs) == 1, runs
    here = float(np.asarray(build_windows(SPEC_BY_KEY["syn_seasonal"])[0].context, float).sum())
    assert abs(float(next(iter(runs))) - here) < 1e-3
