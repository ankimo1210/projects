"""Independent 3/2 finite-difference reference (no spectral imports)."""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from hullkit import bsm, trees
from hullkit._dsinc_types import PutContract, VarianceModel

PATH = Path(__file__).resolve().parents[2] / "research/DSINC/reference_fd.py"
CONTRACT = PutContract(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
MODEL = VarianceModel("three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)
SPOTS = np.array([0.9, 1.0, 1.1])
WIDE = (math.log(1e-5), math.log(8.0))
NARROW = (math.log(0.02), math.log(0.08))


@pytest.fixture(scope="module")
def fd():
    spec = importlib.util.spec_from_file_location("dsinc_reference_fd_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def constant(fd, n_var=4, variance=0.04):
    zero = np.zeros(n_var)
    return fd.FDCoefficients(
        variance=np.full(n_var, variance), var_drift=zero, var_diffusion=zero, cross=zero
    )


def test_reference_does_not_import_the_spectral_modules():
    text = PATH.read_text()
    assert "_dsinc_spectral" not in text and "_dsinc_american" not in text


def test_operator_matches_the_three_halves_generator(fd):
    errors = []
    for nx, nv in ((41, 21), (81, 41)):
        x, z = np.linspace(-0.6, 0.6, nx), np.linspace(math.log(0.01), math.log(0.5), nv)
        A, _, _ = fd.assemble_operator(CONTRACT, fd.three_halves_coefficients(MODEL, z), x, z)
        X, Z = np.meshgrid(x, z, indexing="ij")
        w = math.pi / (z[-1] - z[0])
        f = np.exp(0.3 * X) * np.cos(w * (Z - z[0]))
        fz = -w * np.exp(0.3 * X) * np.sin(w * (Z - z[0]))
        v = np.exp(Z)
        exact = (
            (0.05 - 0.02 - v / 2) * 0.3 * f
            + 0.5 * v * 0.09 * f
            + (0.8 - 28.0 * v) * fz
            + (-0.5 * 4.0 * v) * 0.3 * fz
            + 8.0 * v * (-(w**2) * f)
            - 0.05 * f
        )
        applied = (A @ f[1:-1].ravel()).reshape(nx - 2, nv)
        errors.append(
            np.max(np.abs(applied[1:-1] - exact[2:-2]))
        )  # rows whose x-neighbours are unknowns
    assert (
        1.8 < math.log2(errors[0] / errors[1]) < 2.2
    )  # planning run: 1.986 (flipping rho gives an error of 0.14)


def test_constant_variance_fixture_matches_bsm_and_crr(fd):
    cfg = fd.FDConfig(
        n_x=961, n_var=4, n_time=300, log_spot_bounds=(-1.2, 1.2), log_var_bounds=NARROW
    )
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg, coefficients=constant(fd))
    eu = [bsm.put_price(s, 1.0, 0.05, 0.2, 0.5, q=0.02) for s in SPOTS]
    am = [
        trees.crr_price(s, 1.0, 0.05, 0.2, 0.5, 4000, q=0.02, kind="put", american=True)
        for s in SPOTS
    ]
    np.testing.assert_allclose(out.european, eu, rtol=0, atol=5e-6)  # planning run: 2.2e-6
    np.testing.assert_allclose(out.american, am, rtol=0, atol=2e-5)  # planning run: 4.0e-6


def test_american_solution_satisfies_the_obstacle(fd):
    cfg = fd.FDConfig(
        n_x=121, n_var=41, n_time=60, log_spot_bounds=(-1.2, 1.2), log_var_bounds=WIDE
    )
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg)
    c = out.complementarity
    assert c["min_payoff_gap"] >= 0.0 and c["min_multiplier"] >= 0.0
    assert c["max_complementarity_product"] <= 1e-14 and c["solve_residual"] <= 1e-10
    assert np.all(out.american >= out.european)


def test_contact_edges_are_indexed_by_calendar_step(fd):
    cfg = fd.FDConfig(
        n_x=241,
        n_var=4,
        n_time=8,
        log_spot_bounds=(-1.2, 1.2),
        log_var_bounds=NARROW,
        exercises=("american",),
        record_boundary=True,
    )
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg, coefficients=constant(fd))
    edge = out.contact_edge
    assert edge.shape == (9, 4) and np.all(np.isnan(edge[8])) and np.all(np.isfinite(edge[:8]))
    assert np.all(np.diff(edge[:8, 0]) >= 0.0)  # the put boundary rises towards expiry
    np.testing.assert_array_equal(
        edge[:, 0], edge[:, 3]
    )  # zero variance coefficients decouple the rows
    assert out.european is None


def test_wide_domain_base_level_matches_the_planning_run(fd):
    cfg = fd.FDConfig(
        n_x=241, n_var=101, n_time=150, log_spot_bounds=(-1.2, 1.2), log_var_bounds=WIDE
    )
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg)
    np.testing.assert_allclose(
        out.european, [0.10253835, 0.04718844, 0.01908019], rtol=0, atol=1e-8
    )
    np.testing.assert_allclose(
        out.american, [0.10757684, 0.04861780, 0.01946888], rtol=0, atol=1e-8
    )


@pytest.mark.parametrize(
    "bad", ["heston", "spot", "variance", "expiry", "boundary_without_american"]
)
def test_reference_rejects_unsupported_inputs(fd, bad):
    def call():
        model, spots, contract, bounds, exercises = (
            MODEL,
            SPOTS,
            CONTRACT,
            WIDE,
            ("european", "american"),
        )
        if bad == "heston":
            model = VarianceModel("heston", kappa=2.0, theta=0.04, xi=0.2, rho=-0.5, v0=0.04)
        elif bad == "spot":
            spots = np.array([0.25])  # log(0.25) < -1.2: outside the x domain, never extrapolated
        elif bad == "variance":
            bounds = (math.log(0.05), math.log(8.0))
        elif bad == "expiry":
            contract = PutContract(strike=1.0, expiry=0.0, domestic_rate=0.05, foreign_rate=0.02)
        else:
            exercises = ("european",)
        cfg = fd.FDConfig(
            n_x=41,
            n_var=11,
            n_time=10,
            log_spot_bounds=(-1.2, 1.2),
            log_var_bounds=bounds,
            exercises=exercises,
            record_boundary=bad == "boundary_without_american",
        )
        return fd.reference_put(contract, model, spots, cfg)

    with pytest.raises(ValueError):
        call()
