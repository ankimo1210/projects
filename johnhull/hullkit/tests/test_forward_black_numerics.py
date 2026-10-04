"""Independent Q/T prices, rare-event uncertainty, and corrupt teacher rejection."""

import copy
import importlib
from types import SimpleNamespace

import pytest


def modules():
    return (
        importlib.import_module("johnhull.hullkit.tests._forward_black_reference"),
        importlib.import_module("johnhull.hullkit.tests._forward_black_validation"),
    )


def test_original_requirements_all_markets_and_independent_prices():
    builder, checker = modules()
    data = builder.build()
    assert data["source_requirements"] == [f"BF{i:02}" for i in range(1, 7)]
    assert data["synthetic"] is True and data["source_printed_pins"] == []
    assert len(data["cases"]) == 7
    assert sum(len(row["prices"]) * 2 for row in data["cases"]) == 42
    assert len(data["external_forward"]) == 3 and len(data["limits"]) == 12
    result = checker.verify(data)
    assert result["max_api_error"] < 1e-9
    assert result["max_quadrature_error"] < 1e-9
    assert result["max_moment_error"] < 1e-10
    assert result["max_mc_se"] < 5


def test_rare_positive_price_has_raw_importance_weight_and_nonzero_uncertainty():
    builder, checker = modules()
    result = checker.verify(builder.build())
    rare = next(row for row in result["cases"] if row["id"] == "zero_spot_vol_stochastic_rate")
    call = next(row for row in rare["prices"] if row["strike"] == 140)["call"]
    assert call["reference"] == pytest.approx(7.168352139439199e-8, rel=1e-10)
    assert call["direct_Q"]["hit_count"] == 0 and call["direct_T"]["hit_count"] == 0
    assert call["importance"]["normal_shift"] > 0
    for name in ("mc_Q", "mc_T"):
        assert call[name]["se"] > 0 and call[name]["mean"] > 0
        assert call[name]["hit_count"] > 0 and call[name]["z"] < 5
    with pytest.raises(ValueError, match=r"zero.*stochastic"):
        checker.mc_summary([0.0] * 10, call["reference"], stochastic=True)


def test_wrong_futures_price_cannot_pass_payment_measure_reference():
    from hullkit import _forward_black as api

    builder, checker = modules()
    data = builder.build()
    proxy = SimpleNamespace(**{name: getattr(api, name) for name in checker.API_NAMES})
    base = data["cases"][1]["statistics"]
    proxy.forward_black_price = lambda p, F, K, s, T, kind="call": api.forward_black_price(
        p, F * base["futures"] / base["forward"], K, s, T, kind
    )
    with pytest.raises(ValueError, match="numerical mismatch"):
        checker.verify(data, proxy, mc=False)


@pytest.mark.parametrize("target", ["statistics", "quad", "tail", "matrix"])
def test_modified_teacher_cannot_be_reaccepted_even_with_valid_json(target):
    builder, checker = modules()
    good = builder.build()
    bad = copy.deepcopy(good)
    if target == "statistics":
        bad["cases"][1]["statistics"]["forward"] += 0.01
    elif target == "quad":
        bad["cases"][1]["prices"][1]["call"]["q_quad"] += 0.1
    elif target == "tail":
        bad["cases"][1]["prices"][1]["call"]["q_tail_bound"] = 1.0
    else:
        bad["cases"] = list(reversed(bad["cases"]))
    with pytest.raises(ValueError, match="independent"):
        checker.verify(bad, reference=good, mc=False)


def test_executable_and_saved_controls_reject_wrong_models():
    builder, checker = modules()
    controls = checker.negative_controls(builder.build())
    assert len(controls) >= 8 and all(row["rejected"] for row in controls)
