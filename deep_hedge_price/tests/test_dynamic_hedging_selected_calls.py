"""Saved 18-state call boundary and original unknown-status preservation."""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from hullkit._dynamic_hedging_surfaces import evaluate_call, fit_quote_state
from scipy.interpolate import CubicSpline


def load_checker():
    path = (
        Path(__file__).resolve().parents[2]
        / "johnhull/research/RB-F04/dynamic_hedging/check_selected_calls.py"
    )
    if not path.exists():
        raise AssertionError("selected call checker missing")
    spec = importlib.util.spec_from_file_location("selected_calls_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def evidence():
    dates = np.array([0.0, 1 / 12, 0.25, 0.5, 0.75, 11 / 12])
    spots = np.array([80.0, 100.0, 120.0, 140.0])
    arrays, caches = {}, {}
    parameters = dict(
        spot=100.0, rate=0.03, dividend_yield=0.0, v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7
    )
    for model, states, scale in [
        ("heston", np.array([0.005, 0.02, 0.04, 0.08, 0.2]), 80.0),
        ("local", np.array([0.25, 1.0, 2.0, 4.0]), 3.0),
    ]:
        values = 5.0 + 0.6 * (spots[:, None] - 80.0) + scale * states[None, :]
        cache = dict(
            model=model,
            dates=dates,
            spot_nodes=spots,
            state_nodes=states,
            values=np.tile(values, (6, 1, 1)),
            support_mask=np.ones((6, 4, len(states)), bool),
            rate=0.03,
            dividend_yield=0.0,
            strike=100.0,
            maturity=1.25,
        )
        caches[model] = cache
        for name in ["dates", "spot_nodes", "state_nodes", "values", "support_mask"]:
            arrays[model + "." + name] = cache[name].copy()
    arrays["independent_local_base.log_spots"] = np.log(spots)
    arrays["independent_local_base.values"] = np.tile(5.0 + 0.6 * (spots - 80.0) + 3.0, (6, 1))
    rows = []
    for j, t in enumerate(dates):
        for scenario, (s, v) in enumerate(
            zip(
                [99.95, 100.0, 100.05] if t == 0 else [80.0, 100.0, 120.0],
                [0.02, 0.04, 0.08],
                strict=True,
            )
        ):
            q = 5.0 + 0.6 * (s - 80.0) + 80.0 * v
            point = dict(
                date=float(t), scenario=scenario, spot=s, heston_state=v, quote=q, models={}
            )
            for model in ["heston", "local"]:
                fit = fit_quote_state(
                    caches[model], j, s, q, state_scale=0.04 if model == "heston" else 1.0
                )
                traded = evaluate_call(caches[model], j, s, fit["state"])
                point["models"][model] = {
                    key: float(fit[key]) for key in ["state", "condition", "residual"]
                }
                point["models"][model].update(
                    status=str(fit["status"]),
                    reason=str(fit["reason"]),
                    call_price=float(traded["value"]),
                    call_spot_derivative=float(traded["spot_derivative"]),
                    call_state_derivative=float(traded["state_derivative"]),
                )
            point["models"]["heston"]["price_error_at_true_v"] = float(
                evaluate_call(caches["heston"], j, s, v)["value"] - q
            )
            base = evaluate_call(caches["local"], j, s, 1.0)["value"]
            independent = float(
                CubicSpline(np.log(spots), arrays["independent_local_base.values"][j])(np.log(s))
            )
            point["models"]["local"].update(
                base_price_error=float(base - independent), base_independent_price=independent
            )
            rows.append(point)
    return dict(parameters=parameters, original_states=18, rows=rows), arrays


def test_saved_selected_calls_recompute_all18_without_rng(evidence, monkeypatch):
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: (_ for _ in ()).throw(AssertionError("RNG"))
    )
    result = load_checker().check_selected_calls(*evidence)
    assert result["original_states"] == 18
    assert result["integrity"] == "pass"
    assert result["formal_pilot_qualification"] == "unknown"


@pytest.mark.parametrize("target", ["erase_state", "raw_cache", "fit_status", "base_error"])
def test_saved_selected_calls_reject_original_evidence_tampering(evidence, target):
    metadata, arrays = copy.deepcopy(evidence)
    if target == "erase_state":
        metadata["rows"].pop()
    elif target == "raw_cache":
        arrays["heston.values"][:, 1, :] += 0.1
    elif target == "fit_status":
        metadata["rows"][0]["models"]["heston"]["status"] = "unknown"
    else:
        metadata["rows"][-1]["models"]["local"]["base_price_error"] = 1.0
    with pytest.raises(ValueError):
        load_checker().check_selected_calls(metadata, arrays)
