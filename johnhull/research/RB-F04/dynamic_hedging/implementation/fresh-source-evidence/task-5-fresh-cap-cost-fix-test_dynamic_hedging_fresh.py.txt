"""Scoped independent fresh-reference tests; no formal-pilot claims."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "johnhull/research/RB-F04/dynamic_hedging"
spec = importlib.util.spec_from_file_location(
    "independent_fresh_reference", DIRECTORY / "reference_methods.py"
)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

P = dict(
    spot=100.0, rate=0.03, dividend_yield=0.0, v0=0.04, kappa=2.0, theta=0.04, xi=0.0, rho=-0.7
)


class ConstantSurface:
    def evaluate(self, time, spots):
        values = np.asarray(spots)
        return {
            "variance": np.full(values.shape, 0.04),
            "status": np.full(values.shape, "interior", dtype="U96"),
        }


class OneFailureSurface(ConstantSurface):
    def evaluate(self, time, spots):
        out = super().evaluate(time, spots)
        out["status"][0] = "unsupported_test_path"
        return out


def calendar(date=11 / 12, level=24):
    times = np.linspace(date, 1.0, round((1 - date) * level) + 1)
    indices = np.flatnonzero(np.isclose(times, 1.0))
    return times, indices


def price(**kwargs):
    times, fixings = calendar()
    return ref.direct_asian_price(
        P,
        ConstantSurface(),
        model="local",
        calendar_times=times,
        fixing_indices=fixings,
        spot=100.0,
        state=1.0,
        memory_sum=1100.0,
        memory_count=11,
        seed=31,
        n_paths=32,
        **kwargs,
    )


def test_low_level_real_price_independent_one_fixing_analytic():
    times, indices = calendar(level=1536)
    raw = ref.direct_asian_price(
        P,
        ConstantSurface(),
        model="local",
        calendar_times=times,
        fixing_indices=indices,
        spot=100.0,
        state=1.0,
        memory_sum=1100.0,
        memory_count=11,
        seed=31,
        n_paths=32768,
    )
    from scipy.special import ndtr

    t = 1 / 12
    d1 = (0.03 * t + 0.5 * 0.04 * t) / np.sqrt(0.04 * t)
    expected = (100 * ndtr(d1) - 100 * np.exp(-0.03 * t) * ndtr(d1 - np.sqrt(0.04 * t))) / 12
    assert raw["mean"] == pytest.approx(expected, abs=5 * raw["standard_error"])
    assert raw["original_path_count"] == 32768
    assert raw["statistical_status"] == "measured"


def test_one_unsupported_path_keeps_success_raw_but_whole_n_unknown():
    times, indices = calendar()
    raw = ref.direct_asian_price(
        P,
        OneFailureSurface(),
        model="local",
        calendar_times=times,
        fixing_indices=indices,
        spot=100.0,
        state=1.0,
        memory_sum=1100.0,
        memory_count=11,
        seed=31,
        n_paths=32,
    )
    assert np.isnan(raw["samples"][0])
    assert np.all(np.isfinite(raw["samples"][1:]))
    assert raw["path_status"][0] == "unsupported_test_path"
    assert raw["first_failure_date"][0] == pytest.approx((times[0] + times[1]) / 2)
    assert np.isnan(raw["mean"])
    assert raw["statistical_status"] == "unknown_support"
    assert raw["descriptive_only"]["finite_path_count"] == 31


def test_zero_events_preserve_raw_zero_without_precision_claim():
    times, indices = calendar()
    raw = ref.direct_asian_price(
        P,
        ConstantSurface(),
        model="local",
        calendar_times=times,
        fixing_indices=indices,
        spot=1.0,
        state=1.0,
        memory_sum=0.0,
        memory_count=11,
        seed=31,
        n_paths=32,
    )
    assert np.all(raw["samples"] == 0)
    assert raw["standard_error"] == 0
    assert raw["statistical_status"] == "unknown_underresolved"


def test_supplied_driver_reproduces_own_payoff_and_no_global_rng_mutation():
    times, _indices = calendar()
    normals = np.random.default_rng(7).normal(size=(32, len(times) - 1, 2))
    before = np.random.get_state()
    raw = price(normals=normals)
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])
    terminal = 100 * np.exp(
        np.sum(
            (0.03 - 0.5 * 0.04) * np.diff(times)
            + np.sqrt(0.04 * np.diff(times)) * normals[:, :, 0],
            axis=1,
        )
    )
    expected = np.exp(-0.03 / 12) * np.maximum((1100 + terminal) / 12 - 100, 0)
    np.testing.assert_allclose(raw["samples"], expected, atol=1e-13)


def test_driver_pairing_keeps_fine_and_coarse_brownian_totals():
    fine = np.random.default_rng(1).normal(size=(32, 6, 2))
    coarse = ref.coarsen_normals(fine)
    np.testing.assert_allclose(coarse.sum(axis=1) * np.sqrt(2), fine.sum(axis=1))


def test_full_call_curve_keeps_ill_conditioned_unique_root():
    nodes = np.array([1e-5, 0.02, 0.04, 0.5])
    fit = ref.fit_independent_quote(nodes, nodes * 0.3, 0.006, model="heston", spot=80.0)
    assert fit["solver_status"] == "unique_root"
    assert fit["state"] == pytest.approx(0.02)
    assert fit["Ctheta"] == pytest.approx(0.3)
    assert fit["condition_number"] == pytest.approx(0.01 / (0.04 * 0.3))
    assert fit["operational_status"] == "ill_conditioned"
    np.testing.assert_allclose(fit["full_domain_roots"], [0.02])


def test_full_domain_multiple_and_continuum_roots_are_not_unique():
    nodes = np.array([1e-5, 0.01, 0.04, 0.5])
    prices = (nodes - 0.02) * (nodes - 0.2)
    fit = ref.fit_independent_quote(nodes, prices, 0.0, model="heston", spot=100.0)
    assert fit["solver_status"] == "nonunique"
    assert len(fit["full_domain_roots"]) == 2
    continuum = ref.fit_independent_quote(nodes, np.ones(4), 1.0, model="heston", spot=100.0)
    assert continuum["solver_status"] == "nonunique"
    assert np.any(np.isnan(continuum["raw_roots"]))


def test_missing_full_domain_or_nan_curve_never_clips_to_good_patch():
    with pytest.raises(ValueError, match="full"):
        ref.fit_independent_quote(
            np.array([0.01, 0.02, 0.04, 0.08]), np.arange(4), 1.0, model="heston", spot=100.0
        )
    result = ref.fit_independent_quote(
        np.array([1e-5, 0.02, 0.04, 0.5]),
        np.array([1.0, 2.0, np.nan, 4.0]),
        2.0,
        model="heston",
        spot=100.0,
    )
    assert result["solver_status"] == "unsupported_reference"


def test_real_call_table_deterministic_heston_limit():
    table = ref.independent_call_table(
        P,
        None,
        model="heston",
        dates=[11 / 12],
        query_spots=[99.96, 99.98, 99.99, 100.0, 100.01, 100.02, 100.04],
        state_nodes=[1e-5, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5],
        controls={"upper": 100.0},
    )
    assert table["prices"].shape == (3, 1, 7, 9)
    assert np.all(np.isfinite(table["prices"]))
    assert table["original_bounds"] == [1e-5, 0.5]
    assert table["refinement_kinds"] == ["base", "cutoff", "quadrature"]
    assert len(table["integration_receipts"]) == 3 * 7 * 9


def test_premium_rejects_reduced_n_grid_or_wrong_reserved_seed():
    seed = int(np.random.SeedSequence([2026100904, 8, 0]).generate_state(1)[0])
    for kwargs in [dict(n_paths=32), dict(steps_per_year=768), dict(seed=7)]:
        with pytest.raises(ValueError, match=r"65536|1536|reserved"):
            ref.premium_reference(P, **({"seed": seed} | kwargs))


def test_fresh_entrypoint_exists_without_import_time_rng_or_training():
    spec = importlib.util.spec_from_file_location("fresh_runner", DIRECTORY / "run_fresh.py")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    assert callable(fresh.run_fresh)


def table_and_quote():
    table = ref.independent_call_table(
        P,
        None,
        model="heston",
        dates=[11 / 12],
        query_spots=[99.96, 99.98, 99.99, 100.0, 100.01, 100.02, 100.04],
        state_nodes=[1e-5, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5],
        controls={"upper": 100.0},
    )
    return table, float(table["prices"][-1, 0, 3, 4])


def oracle(**kwargs):
    table, quote = table_and_quote()
    return ref.quote_positions_oracle(
        P,
        None,
        model="heston",
        date=11 / 12,
        spot=100.0,
        quote=quote,
        memory_sum=1100.0,
        memory_count=11,
        seed=7,
        n_paths=64,
        call_table=table,
        steps_per_year=24,
        chunk_paths=32,
        **kwargs,
    )


def test_oracle_raw_ordering_refits_each_query_and_all_covariance_recomputable():
    raw = oracle()
    assert raw["payoff_samples"].shape == (13, 64)
    assert raw["scheme_refinement"]["payoff_samples"].shape == (2, 13, 64)
    assert len(raw["query_fits"]) == 13
    assert raw["query_ids"] == [
        "base",
        "S+.1",
        "S-.1",
        "S+..5",
        "S-..5",
        "S+.2",
        "S-.2",
        "Q+.1",
        "Q-.1",
        "Q+..5",
        "Q-..5",
        "Q+.2",
        "Q-.2",
    ]
    for j, w in enumerate([1.0, 0.5, 2.0]):
        expected = np.column_stack(
            [
                (raw["payoff_samples"][1 + 2 * j] - raw["payoff_samples"][2 + 2 * j])
                / (2 * 0.02 * w),
                (raw["payoff_samples"][7 + 2 * j] - raw["payoff_samples"][8 + 2 * j])
                / (2 * 1e-4 * w),
            ]
        )
        np.testing.assert_allclose(raw["width_position_samples"][j], expected)
    np.testing.assert_allclose(raw["samples"][:, 1:], raw["width_position_samples"][1])
    np.testing.assert_allclose(raw["covariance"], np.cov(raw["samples"], rowvar=False) / 64)
    np.testing.assert_allclose(raw["block_means"], raw["samples"].reshape(16, 4, 3).mean(axis=1))
    paired = raw["scheme_refinement"]
    np.testing.assert_allclose(
        paired["paired_difference_samples"], paired["samples"][1] - paired["samples"][0]
    )
    assert raw["query_fits"][1]["state"] != raw["query_fits"][0]["state"]
    assert all(fit["full_domain_bounds"] == [1e-5, 0.5] for fit in raw["query_fits"])
    assert all(job["path_steps"] <= 1_000_000_000 for job in raw["expenses"])
    assert raw["financial_qualification"] == "unknown"


def test_fine_coarse_scheme_couple_same_supplied_paths():
    normals = np.random.default_rng(9).normal(size=(64, 2, 2))
    raw = oracle(normals=normals)
    assert len(raw["driver_map"]) == 2
    assert all(v["driver_source"] == "supplied" for v in raw["driver_map"])
    assert raw["path_indices"].tolist() == list(range(64))
    assert raw["scheme_refinement"]["samples"].shape == (2, 64, 3)
    assert np.any(raw["scheme_refinement"]["paired_difference_samples"] != 0)


@pytest.mark.parametrize(
    "memory,date,A,branch", [(11, 11 / 12, 1200.0, "linear"), (12, 1.0, 1212.0, "settled")]
)
def test_exact_input_branches_do_not_fit_or_draw(monkeypatch, memory, date, A, branch):
    def forbidden(*args, **kwargs):
        raise AssertionError("exact branch must not calibrate or open RNG")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(ref, "fit_independent_quote", forbidden)
    raw = ref.quote_positions_oracle(
        P,
        None,
        model="heston",
        date=date,
        spot=80.0,
        quote=0.001,
        memory_sum=A,
        memory_count=memory,
        seed=7,
        n_paths=16,
        call_table=None,
        steps_per_year=24,
        chunk_paths=16,
    )
    assert raw["exact_branch"] == branch
    assert raw["statistical_status"] == "exact_input_identity"
    assert not raw["driver_map"]
    assert np.all(raw["samples"][:, 2] == 0)
    expected_delta = np.exp(-0.03 / 12) * np.exp(0.03 / 12) / 12 if memory == 11 else 0.0
    assert raw["mean"][1] == pytest.approx(expected_delta, abs=1e-10)


def test_chunk_memory_limit_rejects_giant_cube_before_rng(monkeypatch):
    monkeypatch.setattr(
        np.random, "default_rng", lambda *args: pytest.fail("must refuse before RNG")
    )
    with pytest.raises(ValueError, match="256 MiB"):
        list(ref._driver_chunks(65536, 1536, 7, 65536))


def test_legacy_state_reference_normal_api_and_unknown_raw_are_preserved():
    times, indices = calendar()
    kwargs = dict(
        model="local",
        calendar_times=times,
        fixing_indices=indices,
        spot=100.0,
        state=1.0,
        memory_sum=1100.0,
        memory_count=11,
        seed=31,
        n_paths=32,
    )
    old = ref.direct_conditional_asian(P, ConstantSurface(), **kwargs)
    base = ref.direct_asian_price(P, ConstantSurface(), **kwargs)
    np.testing.assert_allclose(old["samples"][:, 0], base["samples"])
    assert old["payoff_samples"].shape == (13, 32)
    unknown = ref.direct_conditional_asian(P, OneFailureSurface(), **kwargs)
    assert np.isnan(unknown["mean"]).all()
    assert np.isnan(unknown["samples"][0]).all()
    assert np.isfinite(unknown["samples"][1:]).all()


def fresh_module(monkeypatch):
    monkeypatch.syspath_prepend(str(DIRECTORY))
    spec = importlib.util.spec_from_file_location("fresh_runner", DIRECTORY / "run_fresh.py")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    return fresh


def test_production_teacher_fresh_keeps_chunks_raw_and_independent_uncertainty(monkeypatch):
    fresh = fresh_module(monkeypatch)
    import run_reference
    from hullkit._heston_local_surface import HestonParameters

    params = HestonParameters(**P)
    n = 32
    seed = int(np.random.SeedSequence([2026100904, 10, 0]).generate_state(1)[0])
    normals = np.random.default_rng(3).normal(size=(n, 768, 2))
    original = run_reference.teacher_restart(
        "heston",
        params,
        None,
        normals,
        np.arange(769) / 768,
        start_index=704,
        spot=100.0,
        state=0.04,
        thresholds=np.linspace(0, 24, 33),
    )
    row = dict(
        id="restart0",
        original_n=n,
        model="heston",
        memory_count=11,
        date=11 / 12,
        spot=100.0,
        chunk_paths=16,
        seed=seed,
        original_teacher=original,
        original_record_identity="raw-original-case",
    )
    raw = fresh._production_teacher_replay(params, None, row)
    assert raw["original_path_count"] == n
    assert len(raw["chunks"]) == 2
    assert raw["comparison"]["method"] == "independent_reserved_stream_all_original_paths"
    assert raw["comparison"]["financial_qualification"] == "unknown"
    assert raw["comparison"]["difference"].shape == (6,)
    assert raw["chunks"][0]["replay"]["primitives"]["original_path_count"] == 16
    assert raw["chunks"][1]["path_range"] == [16, 32]
    assert raw["chunks"][0]["driver"]["reserved_parent_seed"] == seed
    with pytest.raises(ValueError, match="anchor"):
        fresh._production_teacher_replay(params, None, row | {"spot": 80.0})


def test_fresh_refuses_unlocked_or_missing_binding_before_any_rng(monkeypatch):
    fresh = fresh_module(monkeypatch)
    monkeypatch.setattr(
        np.random, "default_rng", lambda *args: pytest.fail("invalid fresh must not draw")
    )
    with pytest.raises(ValueError, match="pretest"):
        fresh.run_fresh(
            plan={},
            frozen={},
            candidate={},
            source={},
            original_artifact_identity={},
            parameters=P,
            surface=None,
        )


def test_local_full_calendar_call_table_preserves_independent_pde_levels():
    table = ref.independent_call_table(
        P,
        ConstantSurface(),
        model="local",
        dates=[11 / 12],
        query_spots=[100.0],
        state_nodes=[0.25, 0.5, 1.0, 4.0],
        controls={"space_nodes": 129, "time_steps": 96, "log_half_width": 1.5},
    )
    assert table["prices"].shape == (4, 1, 1, 4)
    assert len(table["pde_receipts"]) == 16
    assert table["refinement_kinds"] == ["base", "space", "time", "domain"]
    assert np.isfinite(table["prices"]).all()
    from scipy.special import ndtr

    t = 1.25 - 11 / 12
    d1 = (0.03 + 0.5 * 0.04) * np.sqrt(t / 0.04)
    expected = 100 * ndtr(d1) - 100 * np.exp(-0.03 * t) * ndtr(d1 - np.sqrt(0.04 * t))
    assert table["prices"][1, 0, 0, 2] == pytest.approx(expected, abs=0.025)
    assert table["financial_qualification"] == "unchecked"


def test_positive_cir_direct_reference_matches_independent_cf_one_fixing():
    parameters = P | {"xi": 0.3}
    times, indices = calendar(level=1536)
    raw = ref.direct_asian_price(
        parameters,
        None,
        model="heston",
        calendar_times=times,
        fixing_indices=indices,
        spot=100.0,
        state=0.04,
        memory_sum=1100.0,
        memory_count=11,
        seed=51,
        n_paths=16384,
    )
    expected = ref.independent_heston_call([100.0], 1 / 12, parameters)[0] / 12
    assert raw["mean"] == pytest.approx(expected, abs=5 * raw["standard_error"] + 0.003)
    assert raw["supported_path_mask"].all()


def test_oracle_zero_payoff_remains_unknown_underresolved_with_raw_se_zero():
    table, quote = table_and_quote()
    raw = ref.quote_positions_oracle(
        P,
        None,
        model="heston",
        date=11 / 12,
        spot=100.0,
        quote=quote,
        memory_sum=0.0,
        memory_count=11,
        seed=7,
        n_paths=64,
        call_table=table,
        steps_per_year=24,
        chunk_paths=32,
    )
    assert raw["statistical_status"] == "unknown_underresolved"
    assert raw["standard_errors"][0] == 0
    assert raw["financial_qualification"] == "unknown"
    assert np.all(raw["samples"][:, 0] == 0)


def test_fresh_refuses_fabricated_candidate_before_source_or_rng(monkeypatch):
    fresh = fresh_module(monkeypatch)
    monkeypatch.setattr(np.random, "default_rng", lambda *args: pytest.fail("must not draw"))
    with pytest.raises(ValueError, match="exact original"):
        fresh.run_fresh(
            plan={"schema": "rb-f04-fresh-plan-v1", "cases": [{"id": "bad"}]},
            frozen={},
            candidate={"original_candidate": {}},
            source={},
            original_artifact_identity="fake",
            parameters=P,
            surface=None,
        )


def test_real_low_quote_conditioning_failure_preserves_root_and_original_raw_n():
    parameters = P | {"xi": 0.3}
    spots = [79.96, 79.98, 79.99, 80.0, 80.01, 80.02, 80.04]
    table = ref.independent_call_table(
        parameters,
        None,
        model="heston",
        dates=[11 / 12],
        query_spots=spots,
        state_nodes=[1e-5, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5],
        controls={"upper": 250.0},
    )
    quote = float(table["prices"][-1, 0, 3, 3])
    raw = ref.quote_positions_oracle(
        parameters,
        None,
        model="heston",
        date=11 / 12,
        spot=80.0,
        quote=quote,
        memory_sum=1100.0,
        memory_count=11,
        seed=7,
        n_paths=16,
        call_table=table,
        steps_per_year=24,
        chunk_paths=16,
    )
    fit = raw["query_fits"][0]
    assert fit["solver_status"] == "unique_root"
    assert fit["state"] == pytest.approx(0.02, abs=1e-8)
    assert fit["condition_number"] > 0.25
    assert fit["operational_status"] == "ill_conditioned"
    assert np.isfinite(raw["payoff_samples"][0]).all()
    assert raw["N"] == 16
    assert raw["operational_status"] == "unknown"
    assert raw["financial_qualification"] == "unknown"
    assert raw["call_refinements"]["state_derivative"] == pytest.approx(0.30937758, abs=2e-6)


def bound_fresh_fixture(monkeypatch):
    """Synthetic metadata closure plus real small reference math; not formal approval."""
    fresh = fresh_module(monkeypatch)
    import run_reference

    spec = importlib.util.spec_from_file_location(
        "execution_test_helpers", ROOT / "deep_hedge_price/tests/test_dynamic_hedging_execution.py"
    )
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    f = helpers.execution_fixture()
    source = run_reference.execution_source_identity()["protocol_source"]
    f["source"] = source
    from hullkit._heston_local_surface import HestonParameters

    params = HestonParameters(**(P | {"xi": 0.3}))
    n = 1024
    normals = np.random.default_rng(3).normal(size=(n, 768, 2))
    original = run_reference.teacher_restart(
        "heston",
        params,
        None,
        normals,
        np.arange(769) / 768,
        start_index=704,
        spot=100.0,
        state=0.04,
        thresholds=np.linspace(0, 24, 33),
    )
    quote = float(ref.independent_heston_call([100.0], 1.25 - 11 / 12, P | {"xi": 0.3})[0])
    seed = f["candidate"]["original_candidate"]["seeds"]["fresh"][0]
    row = dict(
        id="restart0",
        model="heston",
        date=11 / 12,
        spot=100.0,
        quote=quote,
        memory_sum=1100.0,
        memory_count=11,
        stream_slot=0,
        seed=seed,
        original_n=n,
        steps_per_year=1536,
        spot_bump=0.02,
        quote_bump=1e-4,
        chunk_paths=1024,
        state_nodes=[1e-5, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5],
        call_controls={"upper": 250.0},
        original_record_identity={"record": "test-only-original", "sha256": "b" * 64},
        original_teacher=original,
        wall_caps={"call_table": 300.0, "oracle": 300.0, "teacher_replay": 300.0},
    )
    identity = {"sha256": "a" * 64, "record": "test-only-original-artifact"}
    plan = dict(
        schema="rb-f04-fresh-plan-v1",
        cases=[row],
        required_case_ids=["restart0"],
        original_artifact_identity=identity,
        source_sha256=fresh._canonical_digest(source),
        surface_sha256=run_reference.payload_digest(None),
        wall_cap_seconds=900.0,
    )
    f["selection"]["fresh_plan_sha256"] = run_reference.payload_digest(plan)
    helpers.reseal(f)
    frozen = helpers.freeze(f)
    return fresh, dict(
        plan=plan,
        frozen=frozen,
        candidate=f["candidate"],
        source=source,
        original_artifact_identity=identity,
        parameters=params,
        surface=None,
    )


def test_bound_fresh_producer_runs_all_locked_records_with_raw_teacher_and_oracle(monkeypatch):
    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    result = fresh.run_fresh(**kwargs)
    assert result["scope"] == "all_locked_selected_restarts"
    assert result["financial_qualification"] == "unknown"
    assert len(result["records"]) == 1
    record = result["records"][0]
    assert record["raw"]["payoff_samples"].shape == (13, 1024)
    assert record["teacher_replay"]["original_path_count"] == 1024
    assert record["teacher_replay"]["comparison"]["financial_qualification"] == "unknown"
    assert result["plan_sha256"] == kwargs["frozen"]["selection"]["fresh_plan_sha256"]
    assert result["original_artifact_identity"] == kwargs["original_artifact_identity"]
    assert result["cost"]["wall_seconds"] > 0


@pytest.mark.parametrize("field", ["plan", "artifact", "source", "parameters", "surface"])
def test_bound_fresh_refuses_stale_or_misbound_inputs_before_streams(monkeypatch, field):
    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    if field == "plan":
        kwargs["plan"]["cases"][0]["spot"] = 80.0
    elif field == "artifact":
        kwargs["original_artifact_identity"] = {"sha256": "c" * 64}
    elif field == "source":
        kwargs["source"] = kwargs["source"] | {"unexpected.py": "d" * 64}
    elif field == "parameters":
        kwargs["parameters"] = P
    else:
        kwargs["surface"] = ConstantSurface()
    monkeypatch.setattr(
        np.random, "default_rng", lambda *args: pytest.fail("misbound fresh must not draw")
    )
    with pytest.raises((ValueError, AttributeError)):
        fresh.run_fresh(**kwargs)


def test_oracle_compact_per_path_support_is_lossless_and_whole_original_n_unknown():
    class MonteCarloFailure(ConstantSurface):
        def evaluate(self, time, spots):
            raw = super().evaluate(time, spots)
            if np.asarray(spots).shape == (32,):
                raw["status"][0] = "unsupported_mc_path"
            return raw

    table = ref.independent_call_table(
        P,
        MonteCarloFailure(),
        model="local",
        dates=[11 / 12],
        query_spots=[99.96, 99.98, 99.99, 100.0, 100.01, 100.02, 100.04],
        state_nodes=[0.25, 0.5, 1.0, 2.0, 4.0],
        controls={"space_nodes": 65, "time_steps": 24, "log_half_width": 1.5},
    )
    quote = float(table["prices"][-1, 0, 3, 2])
    raw = ref.quote_positions_oracle(
        P,
        MonteCarloFailure(),
        model="local",
        date=11 / 12,
        spot=100.0,
        quote=quote,
        memory_sum=1100.0,
        memory_count=11,
        seed=7,
        n_paths=64,
        call_table=table,
        steps_per_year=24,
        chunk_paths=32,
    )
    assert raw["path_status_encoding"] == "uint16_dictionary"
    assert raw["path_status"].dtype == np.uint16
    decoded = raw["path_status_labels"][raw["path_status"]]
    assert np.all(decoded[:, [0, 32]] == "unsupported_mc_path")
    assert np.all(decoded[:, 1:32] == "supported")
    assert np.isnan(raw["payoff_samples"][:, [0, 32]]).all()
    assert np.isfinite(raw["payoff_samples"][:, 1:32]).all()
    assert raw["statistical_status"] == "unknown_support"
    assert np.isnan(raw["mean"]).all()
    assert raw["original_path_count"] == 64
    assert np.isfinite(raw["first_failure_date"][:, [0, 32]]).all()


def test_oracle_cap_retains_original_shapes_and_rejects_before_fresh_stream(monkeypatch):
    table, quote = table_and_quote()
    monkeypatch.setattr(np.random, "default_rng", lambda *args: pytest.fail("cap must stop stream"))
    raw = ref.quote_positions_oracle(
        P,
        None,
        model="heston",
        date=11 / 12,
        spot=100.0,
        quote=quote,
        memory_sum=1100.0,
        memory_count=11,
        seed=7,
        n_paths=64,
        call_table=table,
        steps_per_year=24,
        chunk_paths=32,
        wall_cap_seconds=1e-9,
    )
    assert raw["payoff_samples"].shape == (13, 64)
    assert np.isnan(raw["payoff_samples"]).all()
    assert raw["original_path_count"] == 64
    assert raw["cap_evidence"]["cap_reached"]
    assert raw["cap_evidence"]["overrun_seconds"] > 0
    assert np.all(raw["cap_evidence"]["unexecuted_query_path_counts"] == 64)
    assert np.all(raw["path_status_labels"][raw["path_status"]] == "unmeasured_cap")
    assert raw["financial_qualification"] == "unknown"
    assert not raw["driver_map"]


def test_strict_premium_cap_keeps_original_n_as_unmeasured_not_fake_toy(monkeypatch):
    seed = int(np.random.SeedSequence([2026100904, 8, 0]).generate_state(1)[0])
    monkeypatch.setattr(
        np.random, "default_rng", lambda *args: pytest.fail("expired premium must not draw")
    )
    raw = ref.premium_reference(P | {"xi": 0.3}, seed=seed, wall_cap_seconds=1e-9)
    assert raw["samples"].shape == (2, 65536)
    assert raw["original_path_count"] == 65536
    assert np.isnan(raw["samples"]).all()
    assert np.isnan(raw["value"])
    assert raw["steps_per_year"] == 1536
    assert raw["cap_evidence"]["cap_reached"]
    assert np.all(raw["cap_evidence"]["unexecuted_query_path_counts"] == 65536)
    assert raw["financial_qualification"] == "unknown"
    assert raw["statistical_status"] == "unknown_support"
    assert not raw["driver_map"]


def test_cap_between_query_jobs_preserves_completed_coarse_raw_path_prefix(monkeypatch):
    import time

    table, quote = table_and_quote()
    clock = [0.0]
    direct = ref.direct_asian_price

    def one_job(*args, **kwargs):
        result = direct(*args, **kwargs)
        clock[0] = 1.1
        return result

    with monkeypatch.context() as patch:
        patch.setattr(time, "perf_counter", lambda: clock[0])
        patch.setattr(ref, "direct_asian_price", one_job)
        raw = ref.quote_positions_oracle(
            P,
            None,
            model="heston",
            date=11 / 12,
            spot=100.0,
            quote=quote,
            memory_sum=1100.0,
            memory_count=11,
            seed=7,
            n_paths=64,
            call_table=table,
            steps_per_year=24,
            chunk_paths=32,
            wall_cap_seconds=1.0,
        )
    paired = raw["scheme_refinement"]
    assert np.isfinite(paired["payoff_samples"][0, 0, :32]).all()
    assert np.isnan(paired["payoff_samples"][0, 0, 32:]).all()
    assert np.isnan(raw["payoff_samples"]).all()
    assert raw["cap_evidence"]["cap_reached"]
    assert raw["cap_evidence"]["unexecuted_query_path_counts"][0, 0] == 32
    assert len(raw["driver_map"]) == 1
    assert raw["original_path_count"] == 64
    assert raw["financial_qualification"] == "unknown"


def test_review_i1_typed_field_parameters_are_bound_before_solver_or_rng(monkeypatch):
    monkeypatch.syspath_prepend(str(DIRECTORY))
    import run_reference
    from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid

    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    parameters = kwargs["parameters"]
    times, z = np.array([0.01, 1.25]), np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    values = np.tile(np.array([0.03, 0.035, 0.04, 0.045, 0.05]), (2, 1))
    field = LocalVarianceGrid(times, z, values, parameters)
    changed = LocalVarianceGrid(
        times, z, values, HestonParameters(**(P | {"xi": 0.3, "spot": 110.0}))
    )
    kwargs["surface"] = changed
    kwargs["plan"]["surface_sha256"] = run_reference.payload_digest(
        fresh._surface_descriptor(field)
    )
    helpers_spec = importlib.util.spec_from_file_location(
        "execution_review_helpers",
        ROOT / "deep_hedge_price/tests/test_dynamic_hedging_execution.py",
    )
    helper = importlib.util.module_from_spec(helpers_spec)
    helpers_spec.loader.exec_module(helper)
    f = dict(
        candidate=kwargs["candidate"],
        source=kwargs["source"],
        pilot=kwargs["frozen"]["pilot"],
        review=kwargs["frozen"]["review"],
        selection=kwargs["frozen"]["selection"],
        domains=kwargs["frozen"]["domains"],
    )
    f["selection"]["fresh_plan_sha256"] = run_reference.payload_digest(kwargs["plan"])
    helper.reseal(f)
    kwargs["frozen"] = helper.freeze(f)
    assert (
        field.evaluate(11 / 12, 100.0)["variance"] != changed.evaluate(11 / 12, 100.0)["variance"]
    )
    import reference_methods

    monkeypatch.setattr(
        reference_methods,
        "independent_call_table",
        lambda *args, **kwargs: pytest.fail("unbound field reached solver"),
    )
    monkeypatch.setattr(
        np.random, "default_rng", lambda *args: pytest.fail("unbound field reached RNG")
    )
    with pytest.raises(ValueError, match=r"field|surface|parameters"):
        fresh.run_fresh(**kwargs)


def test_review_i2_unique_near_lower_bound_preserves_full_oracle_when_central_reference_unavailable():
    from scipy.interpolate import CubicSpline

    parameters = P | {"xi": 0.3}
    table = ref.independent_call_table(
        parameters,
        None,
        model="heston",
        dates=[11 / 12],
        query_spots=[99.96, 99.98, 99.99, 100.0, 100.01, 100.02, 100.04],
        state_nodes=[1e-5, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5],
        controls={"upper": 250.0},
    )
    quote = float(CubicSpline(table["state_nodes"], table["prices"][-1, 0, 3])(0.0001))
    raw = ref.quote_positions_oracle(
        parameters,
        None,
        model="heston",
        date=11 / 12,
        spot=100.0,
        quote=quote,
        memory_sum=1100.0,
        memory_count=11,
        seed=7,
        n_paths=64,
        call_table=table,
        steps_per_year=24,
        chunk_paths=32,
    )
    assert raw["query_fits"][0]["solver_status"] == "unique_root"
    assert raw["query_fits"][0]["state"] == pytest.approx(0.0001, abs=1e-9)
    assert raw["payoff_samples"].shape == (13, 64)
    assert np.isfinite(raw["payoff_samples"][0]).all()
    for fit, samples in zip(raw["query_fits"], raw["payoff_samples"], strict=True):
        assert (
            np.isfinite(samples).all()
            if fit["solver_status"] == "unique_root"
            else np.isnan(samples).all()
        )
    assert raw["call_refinements"] is None
    assert raw["call_refinement_status"]["status"] == "unavailable_derivative_boundary"
    assert raw["call_refinement_status"]["fixed_state_bump"] == 0.0001
    assert raw["financial_qualification"] == "unknown"


def test_saved_fresh_checker_entrypoint_exists_without_solver_import_time():
    spec = importlib.util.spec_from_file_location(
        "fresh_saved_checker", DIRECTORY / "check_fresh.py"
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    assert callable(checker.check_fresh)


def saved_checker(monkeypatch):
    monkeypatch.syspath_prepend(str(DIRECTORY))
    spec = importlib.util.spec_from_file_location(
        "fresh_saved_checker", DIRECTORY / "check_fresh.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_saved_fresh_checker_recomputes_real_raw_without_rng_solver_or_teacher(monkeypatch):
    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    raw = fresh.run_fresh(**kwargs)
    checker = saved_checker(monkeypatch)

    def forbidden(*args, **kwargs):
        pytest.fail("saved checking must not regenerate paths/prices/teacher/fit")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(ref, "independent_heston_call", forbidden)
    monkeypatch.setattr(ref, "pde_call", forbidden)
    monkeypatch.setattr(ref, "direct_asian_price", forbidden)
    import run_reference

    monkeypatch.setattr(run_reference, "teacher_restart", forbidden)
    checked = checker.check_fresh(raw, expected_plan=kwargs.pop("plan"), **kwargs)
    assert checked["financial_qualification"] == "unknown"
    assert checked["original_case_count"] == 1
    case = checked["cases"][0]
    assert case["original_n"] == 1024
    assert case["oracle"]["block_means"].shape == (16, 3)
    assert case["teacher"]["original_n"] == 1024
    assert case["gates"]["asian_price_error"]["outcome"] == "unknown"
    assert case["gates"]["stock_position_error"]["outcome"] == "unknown"
    assert case["gates"]["call_position_error"]["outcome"] == "unknown"
    assert case["teacher_threshold_status"] == "unavailable_original_threshold"
    assert np.isfinite(case["independent_scheme_error_envelope"]).all()
    assert "premium_missing" in checked["unresolved"]


@pytest.mark.parametrize(
    "field",
    [
        "price_mean",
        "widths",
        "root",
        "bracket",
        "teacher_label",
        "clock",
        "expense",
        "refinement_root",
    ],
)
def test_saved_fresh_checker_rejects_resealed_semantic_tampering(monkeypatch, field):
    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    raw = fresh.run_fresh(**kwargs)
    record = raw["records"][0]
    if field == "price_mean":
        record["raw"]["mean"][0] += 1.0
    elif field == "widths":
        record["raw"]["width_position_samples"][0, 0, 0] += 1.0
    elif field == "root":
        record["raw"]["query_fits"][0]["state"] += 0.001
    elif field == "bracket":
        record["raw"]["query_fits"][0]["bracket_residuals"][0, 0] += 1.0
    elif field == "teacher_label":
        record["teacher_replay"]["chunks"][0]["replay"]["labels"]["f"][0] += 1.0
    elif field == "clock":
        record["jobs"][0]["wall_seconds"] += 1.0
    elif field == "expense":
        record["raw"]["expenses"].pop()
    elif field == "refinement_root":
        record["raw"]["query_fits"][0]["refinement_fits"][0]["residual"] += 1.0
    import run_reference

    raw["raw_sha256"] = run_reference.payload_digest(
        {k: v for k, v in raw.items() if k != "raw_sha256"}
    )
    checker = saved_checker(monkeypatch)
    with pytest.raises(ValueError):
        checker.check_fresh(raw, expected_plan=kwargs.pop("plan"), **kwargs)


def test_expired_teacher_cap_keeps_full_original_paths_without_draw(monkeypatch):
    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("expired teacher may not draw")
    )
    row = kwargs["plan"]["cases"][0]
    result = fresh._production_teacher_replay(kwargs["parameters"], None, row, wall_cap_seconds=0.0)
    assert result["executed_path_count"] == 0
    assert result["unexecuted_path_count"] == 1024
    assert result["primitive_samples"].shape == (1024, 6)
    assert np.isnan(result["primitive_samples"]).all()
    assert result["global_labels"] is None
    assert result["cap_evidence"]["cap_reached"]
    assert result["cost"]["overrun_seconds"] >= 0.0


def test_expired_call_table_retains_full_cell_roster_without_solver(monkeypatch):
    monkeypatch.setattr(
        ref, "independent_heston_call", lambda *a, **k: pytest.fail("expired table may not solve")
    )
    raw = ref.independent_call_table(
        P,
        None,
        model="heston",
        dates=[11 / 12],
        query_spots=[100.0],
        state_nodes=[1e-5, 0.01, 0.04, 0.5],
        controls={"upper": 250.0},
        wall_cap_seconds=0.0,
    )
    assert raw["prices"].shape == (3, 1, 1, 4)
    assert np.isnan(raw["prices"]).all()
    assert raw["cap_evidence"]["planned_cells"] == 12
    assert raw["cap_evidence"]["completed_cells"] == 0
    assert raw["cap_evidence"]["cap_reached"]


def rebind_fresh_plan(kwargs):
    import run_reference

    spec = importlib.util.spec_from_file_location(
        "execution_test_helpers_cap",
        ROOT / "deep_hedge_price/tests/test_dynamic_hedging_execution.py",
    )
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    frozen = kwargs["frozen"]
    frozen["selection"]["fresh_plan_sha256"] = run_reference.payload_digest(kwargs["plan"])
    helpers.reseal(frozen)
    kwargs["frozen"] = helpers.freeze(frozen)


def test_phase_deadline_closes_all_locked_original_cases_and_saved_checker(monkeypatch):
    import copy

    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    plan = kwargs["plan"]
    extra = copy.deepcopy(plan["cases"][0])
    extra["id"] = "restart1"
    extra["stream_slot"] = 1
    extra["seed"] = kwargs["candidate"]["original_candidate"]["seeds"]["fresh"][1]
    plan["cases"].append(extra)
    plan["required_case_ids"].append("restart1")
    plan["wall_cap_seconds"] = 1e-9
    rebind_fresh_plan(kwargs)
    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("expired phase must not draw")
    )
    monkeypatch.setattr(
        ref, "independent_heston_call", lambda *a, **k: pytest.fail("expired phase must not solve")
    )
    raw = fresh.run_fresh(**kwargs)
    assert len(raw["records"]) == 2
    for record in raw["records"]:
        assert record["raw"]["payoff_samples"].shape == (13, 1024)
        assert np.isnan(record["raw"]["payoff_samples"]).all()
        assert record["teacher_replay"]["unexecuted_path_count"] == 1024
        assert [j["id"] for j in record["jobs"]] == ["call_table", "oracle", "teacher_replay"]
        assert all(j["effective_wall_cap_seconds"] == 0 for j in record["jobs"])
    checker = saved_checker(monkeypatch)
    checked = checker.check_fresh(raw, expected_plan=kwargs.pop("plan"), **kwargs)
    assert checked["original_case_count"] == 2
    assert checked["financial_qualification"] == "unknown"
    assert all(
        case["gates"]["quote_condition_number"]["outcome"] == "unknown" for case in checked["cases"]
    )


def test_saved_premium_cap_keeps_original_denominator_and_price_unknown(monkeypatch):
    seed = int(np.random.SeedSequence([2026100904, 8, 0]).generate_state(1)[0])
    raw = ref.premium_reference(P | {"xi": 0.3}, seed=seed, wall_cap_seconds=0.0)
    checker = saved_checker(monkeypatch)
    from deep_hedge_price import _dynamic_hedging_execution as execution

    monkeypatch.setattr(
        np.random, "default_rng", lambda *a, **k: pytest.fail("saved premium cannot draw")
    )
    checked = checker._premium(raw, execution.execution_candidate())
    assert checked["original_n"] == 65536
    assert checked["value"] is None
    assert checked["standard_error"] is None
    assert checked["financial_qualification"] == "unknown"


def test_saved_i2_boundary_cannot_claim_measured_derivative_reference(monkeypatch):
    from hullkit._heston_local_surface import HestonParameters

    params = HestonParameters(**(P | {"xi": 0.3}))
    nodes = [1e-5, 0.0001, 0.001, 0.005, 0.01, 0.04, 0.16, 0.5]
    spots = [99.96, 99.98, 99.99, 100.0, 100.01, 100.02, 100.04]
    table = ref.independent_call_table(
        params,
        None,
        model="heston",
        dates=[11 / 12],
        query_spots=spots,
        state_nodes=nodes,
        controls={"upper": 250.0},
    )
    quote = float(
        ref.independent_heston_call([100.0], 1.25 - 11 / 12, P | {"xi": 0.3, "v0": 0.0001})[0]
    )
    raw = ref.quote_positions_oracle(
        params,
        None,
        model="heston",
        date=11 / 12,
        spot=100.0,
        quote=quote,
        memory_sum=1100.0,
        memory_count=11,
        seed=7,
        n_paths=64,
        call_table=table,
        steps_per_year=24,
        chunk_paths=32,
    )
    checker = saved_checker(monkeypatch)
    row = dict(model="heston", date=11 / 12, spot=100.0, quote=quote, spot_bump=0.02)
    result = checker._refinement(raw, row, raw["query_fits"][0], params)
    assert result is None
    raw["call_refinement_status"]["status"] = "measured"
    with pytest.raises(ValueError, match="boundary"):
        checker._refinement(raw, row, raw["query_fits"][0], params)


def test_saved_local_pde_field_and_teacher_recompute_without_generation(monkeypatch):
    fresh, kwargs = bound_fresh_fixture(monkeypatch)
    import run_reference
    from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid
    from scipy.special import ndtr

    params = HestonParameters(**(P | {"xi": 0.3}))
    surface = LocalVarianceGrid(
        times=np.array([0.001, 1.25]),
        z_nodes=np.array([-2.0, 0.0, 2.0]),
        values=np.full((2, 3), 0.04),
        parameters=params,
    )
    row = kwargs["plan"]["cases"][0]
    normals = np.random.default_rng(4).normal(size=(1024, 768, 2))
    row["original_teacher"] = run_reference.teacher_restart(
        "local",
        params,
        surface,
        normals,
        np.arange(769) / 768,
        start_index=704,
        spot=100.0,
        state=1.0,
        thresholds=np.linspace(0, 24, 33),
    )
    row["model"] = "local"
    row["state_nodes"] = [0.25, 0.5, 1.0, 2.0, 4.0]
    row["call_controls"] = {"space_nodes": 81, "time_steps": 96, "log_half_width": 1.8}
    tau = 1.25 - 11 / 12
    d1 = (0.03 + 0.5 * 0.04) * tau / (0.2 * np.sqrt(tau))
    d2 = d1 - 0.2 * np.sqrt(tau)
    row["quote"] = 100 * ndtr(d1) - 100 * np.exp(-0.03 * tau) * ndtr(d2)
    kwargs["surface"] = surface
    kwargs["plan"]["surface_sha256"] = run_reference.payload_digest(
        fresh._surface_descriptor(surface)
    )
    rebind_fresh_plan(kwargs)
    raw = fresh.run_fresh(**kwargs)
    checker = saved_checker(monkeypatch)

    def forbidden(*args, **kw):
        pytest.fail("saved local checking cannot solve/regenerate")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(ref, "pde_call", forbidden)
    monkeypatch.setattr(run_reference, "teacher_restart", forbidden)
    checked = checker.check_fresh(raw, expected_plan=kwargs.pop("plan"), **kwargs)
    assert checked["cases"][0]["oracle"]["fits"][0]["solver_status"] == "unique_root"
    assert checked["financial_qualification"] == "unknown"


def test_call_table_cap_between_actual_solves_keeps_raw_first_cell_and_recomputes(monkeypatch):
    import time

    table_row = dict(
        model="heston",
        date=11 / 12,
        spot=100.0,
        spot_bump=0.02,
        state_nodes=[1e-5, 0.01, 0.04, 0.5],
        call_controls={"upper": 250.0},
    )
    clock = [0.0]
    solve = ref.independent_heston_call

    def first_solve(*args, **kwargs):
        result = solve(*args, **kwargs)
        clock[0] = 1.1
        return result

    with monkeypatch.context() as patch:
        patch.setattr(time, "perf_counter", lambda: clock[0])
        patch.setattr(ref, "independent_heston_call", first_solve)
        raw = ref.independent_call_table(
            P,
            None,
            model="heston",
            dates=[11 / 12],
            query_spots=[99.96, 99.98, 99.99, 100.0, 100.01, 100.02, 100.04],
            state_nodes=table_row["state_nodes"],
            controls=table_row["call_controls"],
            wall_cap_seconds=1.0,
        )
    assert raw["cap_evidence"]["completed_cells"] == 1
    assert raw["cap_evidence"]["unexecuted_cell_count"] == 83
    checker = saved_checker(monkeypatch)
    from hullkit._heston_local_surface import HestonParameters

    rebuilt = checker._table(raw, table_row, HestonParameters(**P), None)
    assert np.isfinite(rebuilt).sum() == 1
    raw["cap_evidence"]["completed_cells"] = 2
    with pytest.raises(ValueError, match="completed cells"):
        checker._table(raw, table_row, HestonParameters(**P), None)


def test_saved_actual_nonconverged_cf_keeps_raw_estimate_and_unknown(monkeypatch):
    p = P | {"xi": 0.3, "spot": 80.0, "v0": 0.02}
    receipt = ref.independent_heston_call(
        [100.0], 1 / 3, p, upper=250.0, quadrature_limit=1, return_receipt=True
    )
    assert receipt["status"] == "unknown"
    assert np.isfinite(receipt["raw_prices"]).all()
    checker = saved_checker(monkeypatch)
    monkeypatch.setattr(
        ref, "independent_heston_call", lambda *a, **k: pytest.fail("saved failed CF cannot rerun")
    )
    value, error = checker._cf_value(receipt, 1 / 3, p)
    assert np.isnan(value)
    assert error > 0
    receipt["price"] = receipt["raw_prices"].copy()
    with pytest.raises(ValueError, match="nonconvergence"):
        checker._cf_value(receipt, 1 / 3, p)


@pytest.mark.parametrize("entrypoint", ["producer", "checker"])
def test_cli_loads_actual_bundle_receipt_tuple_before_guard(monkeypatch, tmp_path, entrypoint):
    import sys

    fresh = fresh_module(monkeypatch)
    import run_reference

    inputs = tmp_path / "inputs"
    payload = dict(
        plan={},
        frozen={},
        candidate={},
        source={},
        original_artifact_identity={"test": "invalid"},
        parameters=P | {"xi": 0.3},
        surface=None,
        payload={},
    )
    run_reference.save_bundle(inputs, payload)
    monkeypatch.setattr(
        sys, "argv", ["fresh", "--inputs", str(inputs), "--output", str(tmp_path / "output")]
    )
    monkeypatch.setattr(
        np.random,
        "default_rng",
        lambda *a, **k: pytest.fail("CLI invalid pretest plan cannot draw"),
    )
    module = fresh if entrypoint == "producer" else saved_checker(monkeypatch)
    with pytest.raises(ValueError, match="pretest"):
        module.main()


@pytest.fixture(scope="module")
def cap_cost_fresh_raw():
    patch = pytest.MonkeyPatch()
    fresh, kwargs = bound_fresh_fixture(patch)
    raw = fresh.run_fresh(**kwargs)
    checker = saved_checker(patch)
    yield checker, raw, kwargs
    patch.undo()


@pytest.mark.parametrize(
    "kind",
    [
        "oracle_budget",
        "table_budget",
        "teacher_budget",
        "oracle_missing_cap",
        "raw_start_outside_job",
        "child_deadline",
        "child_wall_interval",
        "child_cpu_interval",
    ],
)
def test_review_i3_caps_bind_fixed_job_and_real_child_intervals(cap_cost_fresh_raw, kind):
    import copy

    import run_reference

    checker, base, kwargs = cap_cost_fresh_raw
    bad = copy.deepcopy(base)
    record = bad["records"][0]
    if kind == "oracle_budget":
        record["raw"]["cap_evidence"]["cap_seconds"] = 150.0
    elif kind == "table_budget":
        record["raw"]["call_table"]["cap_evidence"]["cap_seconds"] = 150.0
    elif kind == "teacher_budget":
        record["teacher_replay"]["cap_evidence"]["cap_seconds"] = 150.0
    elif kind == "oracle_missing_cap":
        record["raw"]["cap_evidence"] = None
    elif kind == "raw_start_outside_job":
        cap = record["raw"]["cap_evidence"]
        elapsed = cap["wall_seconds"]
        cap["clock"]["wall_start"] = record["jobs"][1]["clock"]["wall_start"] - 1.0
        cap["clock"]["wall_stop"] = cap["clock"]["wall_start"] + elapsed
    elif kind == "child_deadline":
        record["raw"]["expenses"][1]["deadline_wall"] += 100.0
    elif kind == "child_wall_interval":
        expense = record["raw"]["expenses"][1]
        start = record["jobs"][1]["clock"]["wall_stop"] + 1.0
        expense["clock"]["wall_start"] = start
        expense["clock"]["wall_stop"] = start + expense["wall_seconds"]
    elif kind == "child_cpu_interval":
        expense = record["raw"]["expenses"][1]
        start = record["jobs"][1]["clock"]["cpu_stop"] + 1.0
        expense["clock"]["cpu_start"] = start
        expense["clock"]["cpu_stop"] = start + expense["cpu_seconds"]
    bad["raw_sha256"] = run_reference.payload_digest(
        {k: v for k, v in bad.items() if k != "raw_sha256"}
    )
    with pytest.raises(ValueError):
        checker.check_fresh(
            bad, expected_plan=kwargs["plan"], **{k: v for k, v in kwargs.items() if k != "plan"}
        )


@pytest.mark.parametrize(
    "scope",
    ["phase", "job", "oracle_driver", "oracle_query", "table", "teacher_chunk", "teacher_total"],
)
def test_review_i4_all_actual_costs_require_measured_cpu(cap_cost_fresh_raw, scope):
    import copy

    import run_reference

    checker, base, kwargs = cap_cost_fresh_raw
    bad = copy.deepcopy(base)
    record = bad["records"][0]
    if scope == "phase":
        cost = bad["cost"]
    elif scope == "job":
        cost = record["jobs"][1]
    elif scope == "oracle_driver":
        cost = record["raw"]["driver_map"][0]
    elif scope == "oracle_query":
        cost = record["raw"]["expenses"][2]
    elif scope == "table":
        cost = record["raw"]["call_table"]["expenses"][0]
    elif scope == "teacher_chunk":
        cost = record["teacher_replay"]["expenses"][0]
    elif scope == "teacher_total":
        cost = record["teacher_replay"]["cost"]
    cost["clock"].pop("cpu_start")
    cost["clock"].pop("cpu_stop")
    cost["cpu_seconds"] = np.nan
    if scope == "oracle_driver":
        driver_expense = next(
            e for e in record["raw"]["expenses"] if e["scope"] == "independent_oracle_driver"
        )
        driver_expense["clock"] = copy.deepcopy(cost["clock"])
        driver_expense["cpu_seconds"] = np.nan
    bad["raw_sha256"] = run_reference.payload_digest(
        {k: v for k, v in bad.items() if k != "raw_sha256"}
    )
    with pytest.raises(ValueError):
        checker.check_fresh(
            bad, expected_plan=kwargs["plan"], **{k: v for k, v in kwargs.items() if k != "plan"}
        )


@pytest.mark.parametrize(
    "kind",
    [
        "missing_start",
        "missing_stop",
        "missing_elapsed",
        "nan_start",
        "nan_stop",
        "nan_elapsed",
        "negative_start",
        "negative_elapsed",
        "reversed",
    ],
)
def test_review_i4_actual_cpu_is_finite_nonnegative_measurement(monkeypatch, kind):
    checker = saved_checker(monkeypatch)
    row = {
        "clock": {"wall_start": 5.0, "wall_stop": 6.0, "cpu_start": 2.0, "cpu_stop": 2.5},
        "wall_seconds": 1.0,
        "cpu_seconds": 0.5,
        "deadline_wall": 7.0,
        "overrun_seconds": 0.0,
    }
    if kind == "missing_start":
        row["clock"].pop("cpu_start")
    elif kind == "missing_stop":
        row["clock"].pop("cpu_stop")
    elif kind == "missing_elapsed":
        row.pop("cpu_seconds")
    elif kind == "nan_start":
        row["clock"]["cpu_start"] = np.nan
    elif kind == "nan_stop":
        row["clock"]["cpu_stop"] = np.nan
    elif kind == "nan_elapsed":
        row["cpu_seconds"] = np.nan
    elif kind == "negative_start":
        row["clock"]["cpu_start"] = -1.0
        row["clock"]["cpu_stop"] = 0.0
        row["cpu_seconds"] = 1.0
    elif kind == "negative_elapsed":
        row["cpu_seconds"] = -0.5
    elif kind == "reversed":
        row["clock"]["cpu_start"], row["clock"]["cpu_stop"] = 2.5, 2.0
    with pytest.raises(ValueError, match="CPU"):
        checker._clock(row, "actual cost")


def test_review_wall_only_cap_is_explicitly_separate_from_actual_cpu_cost(monkeypatch):
    checker = saved_checker(monkeypatch)
    cap = {
        "cap_seconds": 1.0,
        "budget_wall_start": 5.0,
        "deadline_wall": 6.0,
        "clock": {"wall_start": 5.1, "wall_stop": 5.5},
        "wall_seconds": 0.4,
        "overrun_seconds": 0.0,
        "cap_reached": False,
        "financial_qualification": "unknown",
    }
    checker._cap(cap)
    with pytest.raises(ValueError, match="CPU"):
        checker._clock(cap, "actual cost")


def test_review_expired_remaining_budget_still_binds_original_actual_job(monkeypatch):
    checker = saved_checker(monkeypatch)
    job = {
        "effective_wall_cap_seconds": 0.0,
        "deadline_wall": 6.0,
        "clock": {"wall_start": 6.0, "wall_stop": 7.0, "cpu_start": 1.0, "cpu_stop": 2.0},
        "wall_seconds": 1.0,
        "cpu_seconds": 1.0,
        "overrun_seconds": 1.0,
    }
    cap = {
        "cap_seconds": 0.0,
        "budget_wall_start": 6.0,
        "deadline_wall": 6.0,
        "clock": {"wall_start": 6.1, "wall_stop": 6.9},
        "wall_seconds": 0.8,
        "overrun_seconds": 0.9,
        "cap_reached": True,
        "financial_qualification": "unknown",
    }
    checker._bind_job_cap({"cap_evidence": cap, "expenses": []}, job, "expired oracle")
