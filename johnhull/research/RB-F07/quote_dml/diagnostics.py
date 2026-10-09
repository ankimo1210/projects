"""Raw-draw MC diagnostics, independent moments and fixed six-SE checks.

One IID normal stream is shared across conditions; a separate seeded stream
is the pilot. Each condition's IID standard error is valid, but conditions
are correlated and are not used for cross-condition significance claims.
Rare-event cases are recorded without an ordinary six-SE success claim.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from hullkit import _quote_dml_teachers as teacher

_SPEC = importlib.util.spec_from_file_location(
    "quote_dml_diagnostic_reference", Path(__file__).with_name("reference_methods.py")
)
reference = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(reference)

METHODS = ("lrm", "conditional", "naive_pathwise", "discount_omitted")
SMOKE_PATHS = 2048


def _validate_mc_protocol(protocol):
    fixed = {
        "paths": 65536,
        "seed": 1107,
        "pilot_seed": 6017,
        "rare_event_min_count": 20,
        "se_multiplier": 6,
    }
    try:
        if protocol["schema_version"] != 1 or any(
            protocol["mc"][key] != value for key, value in fixed.items()
        ):
            raise ValueError("MC protocol changed; a new reviewed protocol version is required")
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid fixed MC protocol: {exc}") from exc


def _cases(protocol):
    nominal = [(s, t) for s in protocol["mc"]["spots"] for t in protocol["mc"]["maturities"]]
    return [*nominal, (80.0, 0.05)]


def _stream_statistics(sample):
    prices = (sample["payoff"], sample["conditional_price"], sample["payoff"], sample["payoff"])
    rows = [
        np.column_stack([price, sample[method]])
        for price, method in zip(prices, METHODS, strict=True)
    ]
    root_n = np.sqrt(len(rows[0]))
    return {
        "mean": np.array([values.mean(axis=0) for values in rows]),
        "se": np.array([values.std(axis=0, ddof=1) / root_n for values in rows]),
        "second": np.array([(values**2).mean(axis=0) for values in rows]),
        "second_se": np.array([(values**2).std(axis=0, ddof=1) / root_n for values in rows]),
        "hits": int(np.count_nonzero(sample["payoff"])),
    }


def _assert_close(actual, expected, name, *, atol=1e-10, rtol=1e-9):
    actual, expected = np.asarray(actual), np.asarray(expected)
    if actual.shape != expected.shape:
        raise ValueError(f"MC diagnostic shape mismatch: {name}")
    if actual.dtype.kind in "bUS" or expected.dtype.kind in "bUS":
        matches = np.array_equal(actual, expected)
    else:
        matches = np.isfinite(actual).all() and np.allclose(actual, expected, atol=atol, rtol=rtol)
    if not matches:
        raise ValueError(f"MC diagnostic numeric mismatch: {name}")


def _calculate(protocol, z, pilot_z, smoke):
    q = np.asarray(protocol["curve"]["base_quotes"], dtype=float)
    market = teacher.prepare_market(q)
    strike, sigma = protocol["contract"]["strike"], protocol["contract"]["sigma"]
    cases = _cases(protocol)
    records = []
    for spot, maturity in cases:
        exact = teacher.analytic(market, spot, maturity, strike=strike, sigma=sigma)
        independent = reference.digital_moments(q, spot, maturity, strike=strike, sigma=sigma)
        conditioned = reference.conditioning_moments(q, spot, maturity, strike=strike, sigma=sigma)
        exact_mean = np.r_[exact["price"], exact["g_quote"]]
        reference_mean = np.r_[independent["price"], independent["g_quote"]]
        _assert_close(exact_mean, reference_mean, "analytic_vs_independent_density")
        _assert_close(
            np.r_[conditioned["price"], conditioned["g_quote"]],
            reference_mean,
            "conditional_integral_vs_density",
        )
        lrm_second = (
            teacher.lrm_variance(market, spot, maturity, strike=strike, sigma=sigma)
            + exact["g_quote"] ** 2
        )
        _assert_close(lrm_second, independent["lrm_second_moment"], "lrm_second_vs_density")
        main = _stream_statistics(
            teacher.samples(market, spot, maturity, z, strike=strike, sigma=sigma)
        )
        pilot = _stream_statistics(
            teacher.samples(market, spot, maturity, pilot_z, strike=strike, sigma=sigma)
        )
        expected = np.vstack(
            [
                reference_mean,
                reference_mean,
                np.r_[independent["price"], independent["naive_pathwise_mean"]],
                np.r_[independent["price"], independent["discount_omitted_mean"]],
            ]
        )
        probability = independent["hit_probability"]
        hits, misses = len(z) * probability, len(z) * (1 - probability)
        rare = min(hits, misses) < protocol["mc"]["rare_event_min_count"]
        records.append(
            {
                "spot": spot,
                "maturity": maturity,
                "mean": main["mean"],
                "se": main["se"],
                "second": main["second"],
                "second_se": main["second_se"],
                "observed_hits": main["hits"],
                "pilot_mean": pilot["mean"],
                "pilot_se": pilot["se"],
                "pilot_second": pilot["second"],
                "pilot_second_se": pilot["second_se"],
                "pilot_observed_hits": pilot["hits"],
                "exact_mean": exact_mean,
                "method_expected": expected,
                "lrm_second": lrm_second,
                "conditional_second": conditioned["second_moment"],
                "negative_bias": expected[2:, 1:] - reference_mean[None, 1:],
                "expected_hits": hits,
                "expected_misses": misses,
                "rare": rare,
                "assessed": not rare,
            }
        )
    arrays = {f"mc_{key}": np.array([row[key] for row in records]) for key in records[0]}
    arrays.update(
        mc_z=np.asarray(z, dtype=float).copy(),
        mc_pilot_z=np.asarray(pilot_z, dtype=float).copy(),
        mc_smoke=np.array(bool(smoke)),
        mc_method=np.array(METHODS),
        mc_seed=np.array(protocol["mc"]["seed"]),
        mc_pilot_seed=np.array(protocol["mc"]["pilot_seed"]),
        mc_se_multiplier=np.array(protocol["mc"]["se_multiplier"], dtype=float),
        mc_draws_shared=np.array(True),
    )
    return arrays


def make_diagnostics(protocol, *, smoke=False):
    """Generate twelve nominal cases and one rare case, with no model training.

    Main paths use seed 1107, pilot paths seed 6017 in the fixed protocol.
    Smoke has 2048 paths; full diagnostics use the declared 65536 paths.
    The four methods retain seven columns: price, spot delta, q5 Greeks.
    """
    _validate_mc_protocol(protocol)
    paths = SMOKE_PATHS if smoke else int(protocol["mc"]["paths"])
    z = np.random.default_rng(protocol["mc"]["seed"]).standard_normal(paths)
    pilot_z = np.random.default_rng(protocol["mc"]["pilot_seed"]).standard_normal(paths)
    return _calculate(protocol, z, pilot_z, smoke)


def _assess_stream(arrays, protocol, *, pilot=False):
    prefix = "mc_pilot_" if pilot else "mc_"
    paths = len(arrays["mc_pilot_z"] if pilot else arrays["mc_z"])
    regular = ~arrays["mc_rare"]
    observed = arrays[f"{prefix}observed_hits"][regular]
    if np.any((observed == 0) | (observed == paths)):
        raise ValueError(
            "regular MC case has zero observed hits or misses; six-SE assessment is invalid"
        )
    mean, se = arrays[f"{prefix}mean"][regular], arrays[f"{prefix}se"][regular]
    expected = arrays["mc_method_expected"][regular]
    tolerance = protocol["mc"]["se_multiplier"] * se + 1e-10 + 1e-9 * np.abs(expected)
    if np.any(np.abs(mean - expected) > tolerance):
        raise ValueError(f"{prefix}regular means exceed the predeclared six-SE criterion")
    # Zero SE in later inactive quote buckets or naive spot is mathematical.
    # Zero payoff SE is not valid evidence in an otherwise regular case.
    if np.any(se[:, 0, 0] <= 0):
        raise ValueError("regular payoff has zero SE; no ordinary MC success claim")
    for method, reference_second in (
        (0, arrays["mc_lrm_second"][regular]),
        (1, arrays["mc_conditional_second"][regular]),
    ):
        second = arrays[f"{prefix}second"][regular, method, 1:]
        second_se = arrays[f"{prefix}second_se"][regular, method, 1:]
        tolerance = (
            protocol["mc"]["se_multiplier"] * second_se + 1e-10 + 1e-9 * np.abs(reference_second)
        )
        if np.any(np.abs(second - reference_second) > tolerance):
            raise ValueError(f"{prefix}score/conditional second moments exceed six SE")


def check_diagnostics(arrays, protocol):
    """Recompute from raw draws, independent moments and unchanged six-SE rules.

    Pilot data cannot widen the criterion. Rare cases remain unassessed by
    ordinary MC confidence checks, including cases with zero hits/SE. The
    negative controls are checked against their biased theoretical means;
    this validation does not declare them correct digital-Greek estimators.
    Other experiment keys may coexist in arrays and are ignored here.
    """
    try:
        _validate_mc_protocol(protocol)
        smoke = bool(np.asarray(arrays["mc_smoke"]).item())
        paths = SMOKE_PATHS if smoke else int(protocol["mc"]["paths"])
        if protocol["mc"]["se_multiplier"] != 6:
            raise ValueError("pilot cannot widen the fixed six-SE criterion")
        z, pilot_z = np.asarray(arrays["mc_z"]), np.asarray(arrays["mc_pilot_z"])
        if z.shape != (paths,) or pilot_z.shape != (paths,):
            raise ValueError("saved diagnostic paths disagree with protocol")
        _assert_close(
            z,
            np.random.default_rng(protocol["mc"]["seed"]).standard_normal(paths),
            "main_seeded_draws",
            atol=1e-12,
            rtol=1e-10,
        )
        _assert_close(
            pilot_z,
            np.random.default_rng(protocol["mc"]["pilot_seed"]).standard_normal(paths),
            "pilot_seeded_draws",
            atol=1e-12,
            rtol=1e-10,
        )
        recomputed = _calculate(protocol, z, pilot_z, smoke)
        for key, expected in recomputed.items():
            if key not in arrays:
                raise ValueError(f"missing MC evidence: {key}")
            _assert_close(arrays[key], expected, key)
        _assess_stream(recomputed, protocol)
        _assess_stream(recomputed, protocol, pilot=True)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError(f"invalid MC evidence: {exc}") from exc
