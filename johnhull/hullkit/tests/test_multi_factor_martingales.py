"""Independent factor/basis/conditional contracts for Hull GE §28.5."""

import numpy as np
import pytest
from hullkit._multi_factor_martingales import (
    correlation_factor,
    factor_numeraire_drifts,
    factor_ratio_conditional_mean,
    factor_ratio_drift,
)

SF = np.array([0.20, -0.10, 0.15])
SG = np.array([0.12, 0.08, -0.18])
C = np.array([[1.0, 0.45, -0.30], [0.45, 1.0, 0.20], [-0.30, 0.20, 1.0]])


def test_signed_correlated_ito_and_numeraire_drifts():
    mf, mg = factor_numeraire_drifts(0.04, SF, SG, C)
    assert mf == pytest.approx(0.04220, abs=1e-12)
    assert mg == pytest.approx(0.10904, abs=1e-12)
    assert factor_ratio_drift(0.04, 0.04, SF, SG, C) == pytest.approx(0.06684, abs=1e-12)
    assert factor_ratio_drift(mf, mg, SF, SG, C) == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize("rho", [-1.0, 1.0, 1 - 1e-12])
def test_psd_factor_without_inverse_or_jitter(rho):
    corr = np.array([[1.0, rho], [rho, 1.0]])
    L = correlation_factor(corr)
    np.testing.assert_allclose(L @ L.T, corr, rtol=0, atol=2e-14)
    sf, sg = np.array([0.2, -0.1]), np.array([0.08, 0.02])
    mf, mg = factor_numeraire_drifts(-0.01, sf, sg, corr)
    assert factor_ratio_drift(mf, mg, sf, sg, corr) == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize("value", [0.65, 1.25, 2.0])
@pytest.mark.parametrize("horizon", [0.0, 0.25, 1.0, 2.5])
def test_conditional_current_value_and_independent_future_increment(value, horizon):
    mf, mg = factor_numeraire_drifts(0.04, SF, SG, C)
    assert factor_ratio_conditional_mean(value, mf, mg, SF, SG, horizon, C) == pytest.approx(
        value, abs=1e-12
    )
    assert factor_ratio_conditional_mean(value, 0.04, 0.04, SF, SG, horizon, C) == pytest.approx(
        value * np.exp(0.06684 * horizon), abs=1e-12
    )


def test_independent_basis_rotation_and_one_factor_limit():
    L = correlation_factor(C)
    f, g = SF @ L, SG @ L
    angle = 0.37
    O = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    np.testing.assert_allclose(
        factor_numeraire_drifts(0.04, f, g), factor_numeraire_drifts(0.04, f @ O, g @ O), atol=1e-14
    )
    assert factor_ratio_drift(0.04, 0.04, [0.3], [-0.15]) == pytest.approx(0.0675)
    assert factor_ratio_conditional_mean(1.25, 0.04, 0.04, [0.3], [-0.15], 1.5) == pytest.approx(
        1.25 * np.exp(0.0675 * 1.5)
    )


def test_final_factor_axis_and_leading_batch_broadcast():
    f = np.array([[0.2, -0.1, 0.15], [0, 0, 0]])
    mf, mg = factor_numeraire_drifts(np.array([0.04, -0.01]), f, SG, C)
    assert mf.shape == mg.shape == (2,)
    out = factor_ratio_conditional_mean(
        np.array([[0.65], [2.0]]), mf, mg, f, SG, np.array([0.25, 2.5]), C
    )
    np.testing.assert_allclose(out, [[0.65, 0.65], [2.0, 2.0]], atol=1e-12)
    assert isinstance(factor_ratio_drift(0.04, 0.04, SF, SG, C), float)


@pytest.mark.parametrize(
    "bad",
    [
        np.nan,
        np.inf,
        1j,
        True,
        ".04",
        np.datetime64("NaT"),
        np.timedelta64(365, "D"),
        np.array([np.timedelta64(1, "D")], dtype=object),
    ],
)
def test_semantic_types_not_cast_into_years(bad):
    with pytest.raises(ValueError):
        factor_numeraire_drifts(bad, SF, SG, C)


@pytest.mark.parametrize(
    "bad",
    [
        [],
        [[1, 0], [0, 2]],
        [[1, 0.4], [0.3, 1]],
        [[1, 1.01], [1.01, 1]],
        [[1, np.inf], [np.inf, 1]],
        [[1, 0, 0], [0, 1, 0]],
        [[1e300, 0], [0, 1e300]],
    ],
)
def test_invalid_correlation_is_not_repaired(bad):
    with pytest.raises(ValueError):
        correlation_factor(bad)


@pytest.mark.parametrize(
    "f,g", [(0.3, [-0.15]), ([0.3], [-0.15, 0.2]), ([], []), ([[0.3, 0.1]], [[0.2, 0.1, 0.1]])]
)
def test_invalid_factor_axis_and_shape(f, g):
    with pytest.raises(ValueError):
        factor_ratio_drift(0.04, 0.04, f, g)


@pytest.mark.parametrize(
    "value,horizon", [(0, 1), (-1, 1), (1, -1), (np.inf, 0), (1, np.timedelta64(365, "D"))]
)
def test_domains_validated_before_empty_batch(value, horizon):
    with pytest.raises(ValueError):
        factor_ratio_conditional_mean(value, 0.04, 0.04, np.empty((0, 3)), SG, horizon, C)


def test_valid_empty_batch_and_representability():
    assert factor_ratio_conditional_mean(1, 0.04, 0.04, np.empty((0, 3)), SG, 1, C).shape == (0,)
    with pytest.raises(ValueError):
        factor_ratio_conditional_mean(1, 1e300, -1e300, [0.3], [0.15], 1e300)
    with pytest.raises(ValueError):
        factor_ratio_conditional_mean(1, -1e300, 1e300, [0.3], [0.15], 1)
    with pytest.raises(ValueError):
        factor_ratio_drift(0.04, 0.04, [1e300], [1e300])


@pytest.mark.parametrize("where", ["loading", "drift", "correlation"])
def test_mixed_bool_sequences_rejected_before_numpy_promotes_them(where):
    with pytest.raises(ValueError):
        if where == "loading":
            factor_numeraire_drifts(0.04, [0.2, True], [0.1, 0.2])
        elif where == "drift":
            factor_ratio_drift([0.04, True], 0.04, [0.2, 0.1], [0.1, 0.2])
        else:
            correlation_factor([[1, False], [False, 1]])
