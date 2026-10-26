"""DSINC input contracts, validation, status codes and digests."""

import math

import pytest
from hullkit._dsinc_types import (
    BOUNDARY_STATUS,
    PricingFailure,
    PutContract,
    SpectralConfig,
    VarianceModel,
    canonical_digest,
)

PANELS = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0)
BOUNDS = (math.log(2e-4), math.log(2.0))
CONTRACT = dict(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
MODEL = dict(kind="three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)


def s0(**changes):
    base = dict(
        n_time=100, n_var=160, log_var_bounds=BOUNDS, chi=0.5, panels=PANELS, points_per_panel=12
    )
    return SpectralConfig(**(base | changes))


def test_paper_inputs_are_accepted():
    PutContract(**CONTRACT)
    VarianceModel(**MODEL)
    VarianceModel("heston", kappa=2.0, theta=0.04, xi=0.2, rho=-0.5, v0=0.04)
    config = s0()
    assert config.root_widths == (0.1, 0.2, 0.3, 0.5) and config.crossing == "upper"
    assert (config.root_x_tol, config.root_residual_tol, config.root_maxiter) == (1e-10, 1e-8, 60)


@pytest.mark.parametrize(
    "field, value",
    [
        ("strike", 0.0),
        ("strike", -1.0),
        ("strike", math.nan),
        ("expiry", -0.1),
        ("expiry", math.inf),
        ("domestic_rate", 0.02),
        ("foreign_rate", -0.01),
        ("foreign_rate", math.nan),
    ],
)
def test_invalid_contract_is_rejected(field, value):
    with pytest.raises(ValueError):
        PutContract(**(CONTRACT | {field: value}))


@pytest.mark.parametrize(
    "field, value",
    [
        ("kappa", 0.0),
        ("theta", -0.04),
        ("xi", 0.0),
        ("rho", 1.0),
        ("rho", -1.0),
        ("v0", 0.0),
        ("v0", math.nan),
        ("kind", "sabr"),
    ],
)
def test_invalid_model_is_rejected(field, value):
    with pytest.raises(ValueError):
        VarianceModel(**(MODEL | {field: value}))


def test_three_halves_martingale_condition_includes_equality():
    VarianceModel(
        "three_halves", kappa=0.25, theta=0.04, xi=1.0, rho=0.75, v0=0.04
    )  # rho*xi == kappa + xi**2/2
    VarianceModel("heston", kappa=0.125, theta=0.04, xi=1.0, rho=0.75, v0=0.04)
    with pytest.raises(ValueError, match="martingale"):
        VarianceModel("three_halves", kappa=0.125, theta=0.04, xi=1.0, rho=0.75, v0=0.04)


@pytest.mark.parametrize(
    "changes",
    [
        dict(chi=0.0),
        dict(chi=1.0),
        dict(n_time=0),
        dict(n_time=True),
        dict(n_var=3),
        dict(log_var_bounds=(0.0, -1.0)),
        dict(panels=(1.0, 2.0)),
        dict(panels=(0.0, 5.0, 5.0)),
        dict(points_per_panel=0),
        dict(root_widths=(0.2, 0.1)),
        dict(root_maxiter=0),
        dict(crossing="middle"),
    ],
)
def test_invalid_spectral_config_is_rejected(changes):
    with pytest.raises(ValueError):
        s0(**changes)


def test_boundary_status_codes_are_fixed():
    assert BOUNDARY_STATUS == {
        "not_run": -1,
        "single": 0,
        "multiple_crossings": 1,
        "missing_sign_change": 2,
        "wrong_orientation": 3,
        "ambiguous_contact": 4,
        "nonfinite": 5,
        "maxiter": 6,
        "terminal": 7,
    }


def test_pricing_failure_keeps_code_and_details():
    error = PricingFailure("boundary_failure", "no sign change", {"time_index": 98})
    assert (error.code, error.message, error.details) == (
        "boundary_failure",
        "no sign change",
        {"time_index": 98},
    )
    assert "boundary_failure" in str(error)


def test_digest_tracks_every_field():
    parts = (PutContract(**CONTRACT), VarianceModel(**MODEL), s0())
    base = canonical_digest(*parts)
    assert base == canonical_digest(PutContract(**CONTRACT), VarianceModel(**MODEL), s0())
    changed = [
        (PutContract(**(CONTRACT | {"expiry": 1.0})), parts[1], parts[2]),
        (parts[0], VarianceModel(**(MODEL | {"rho": -0.4})), parts[2]),
        (parts[0], parts[1], s0(chi=0.25)),
        (parts[0], parts[1], s0(panels=(*PANELS, 1280.0))),
    ]
    assert all(canonical_digest(*c) != base for c in changed)
    assert canonical_digest({"a": (1.0, 2.0), "b": None}) == canonical_digest(
        {"b": None, "a": [1.0, 2.0]}
    )
    with pytest.raises(ValueError):
        canonical_digest({"a": math.nan})
