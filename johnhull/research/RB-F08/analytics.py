"""RB-F08 pure error, coverage, paired-cost and expense-accounting statistics."""

from __future__ import annotations

import math

import numpy as np


def _values(values):
    a = np.asarray(values, dtype=float)
    if a.ndim != 1 or not len(a) or not np.isfinite(a).all():
        raise ValueError("finite nonempty original trial vector required")
    return a


def error_summary(prices: np.ndarray, truth: float) -> dict:
    """Use all independent outer runs for bias and RMSE; never remove failed values."""
    x = _values(prices)
    if not math.isfinite(truth):
        raise ValueError("finite truth required")
    mean = float(x.mean())
    bias = mean - truth
    mse = float(np.mean((x - truth) ** 2))
    variance = float(np.mean((x - mean) ** 2))
    return dict(
        trials=len(x),
        mean=mean,
        truth=float(truth),
        bias=bias,
        mse=mse,
        rmse=math.sqrt(mse),
        empirical_variance=variance,
        sample_variance=float(x.var(ddof=1)) if len(x) > 1 else None,
    )


def coverage_summary(intervals: np.ndarray, truth: float) -> dict:
    """Inclusive empirical hits and Wilson uncertainty over every original outer trial."""
    a = np.asarray(intervals, dtype=float)
    if (
        a.ndim != 2
        or a.shape[1] != 2
        or not len(a)
        or not np.isfinite(a).all()
        or np.any(a[:, 0] > a[:, 1])
        or not math.isfinite(truth)
    ):
        raise ValueError("finite ordered intervals and truth required")
    trials = len(a)
    hits = int(np.count_nonzero((a[:, 0] <= truth) & (truth <= a[:, 1])))
    probability = hits / trials
    z = 1.959963984540054
    denominator = 1 + z * z / trials
    center = (probability + z * z / (2 * trials)) / denominator
    half = (
        z
        * math.sqrt(probability * (1 - probability) / trials + z * z / (4 * trials * trials))
        / denominator
    )
    widths = a[:, 1] - a[:, 0]
    return dict(
        hits=hits,
        trials=trials,
        coverage=probability,
        wilson95=[max(0.0, center - half), min(1.0, center + half)],
        mean_width=float(widths.mean()),
        median_width=float(np.median(widths)),
        p95_width=float(np.quantile(widths, 0.95)),
        degenerate=int(np.count_nonzero(widths == 0)),
    )


def paired_ratio_bootstrap(mlmc_times, plain_times, *, seed, resamples=2000) -> dict:
    """Bootstrap the median paired run-cost ratio, retaining every run in each pair."""
    a, b = _values(mlmc_times), _values(plain_times)
    if a.shape != b.shape or np.any(a <= 0) or np.any(b <= 0):
        raise ValueError("matching positive paired cost observations required")
    if isinstance(resamples, bool) or not isinstance(resamples, (int, np.integer)) or resamples < 1:
        raise ValueError("positive integer bootstrap count required")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or not 0 <= seed < 2**32:
        raise ValueError("uint32 bootstrap seed required")
    ratio = a / b
    rng = np.random.default_rng(seed)
    sampled = np.median(ratio[rng.integers(0, len(ratio), size=(resamples, len(ratio)))], axis=1)
    return dict(
        trials=len(ratio),
        median_ratio=float(np.median(ratio)),
        interval95=np.quantile(sampled, [0.025, 0.975]).tolist(),
        seed=int(seed),
        resamples=int(resamples),
    )


def _seconds(value):
    if (
        not isinstance(value, (int, float, np.integer, np.floating))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("nonnegative finite expense seconds required")
    return float(value)


def cost_account(
    pilot: dict, runs: list[dict], *, amortizations=(1, 10, 100), method=None, epsilon=None
) -> dict:
    """Count unique offline expenses once, and show method-specific cold/amortized cost.

    An explicit expense has id, seconds, methods and optionally epsilons.
    Legacy fixtures provide all four pilot/calibration/allocation/freeze totals.
    Serialization and fresh review remain separate from online experiment costs.
    """
    if "expenses" in pilot:
        expenses = pilot["expenses"]
        if not isinstance(expenses, list) or not expenses:
            raise ValueError("nonempty explicit offline expense ledger required")
    else:
        names = ("pilot_s", "calibration_s", "allocation_s", "freeze_validation_s")
        if any(name not in pilot for name in names):
            raise ValueError("complete offline expense account required")
        expenses = [dict(expense_id=name, seconds=pilot[name], methods=["all"]) for name in names]
    unique = {}
    for item in expenses:
        if not isinstance(item.get("expense_id"), str) or not item["expense_id"]:
            raise ValueError("unique named expense_id required")
        amount = _seconds(item.get("seconds"))
        uses = item.get("methods", ["all"])
        if not isinstance(uses, list) or not uses:
            raise ValueError("expense method applicability required")
        previous = unique.get(item["expense_id"])
        if previous is not None:
            if not math.isclose(_seconds(previous["seconds"]), amount, rel_tol=0, abs_tol=1e-12):
                raise ValueError("duplicate expense_id has different amounts")
            if previous.get("methods", ["all"]) != uses or previous.get("epsilons") != item.get(
                "epsilons"
            ):
                raise ValueError("duplicate expense_id has different applicability")
        else:
            unique[item["expense_id"]] = item
    selected = []
    for identity, item in unique.items():
        uses = item.get("methods", ["all"])
        if method is not None and "all" not in uses and method not in uses:
            continue
        if (
            epsilon is not None
            and item.get("epsilons") is not None
            and epsilon not in item["epsilons"]
        ):
            continue
        selected.append(identity)
    selected_runs = [
        r
        for r in runs
        if (method is None or r.get("method") == method)
        and (epsilon is None or r.get("epsilon") == epsilon)
    ]
    if not selected_runs:
        raise ValueError("at least one original main run required")
    main = [_seconds(r.get("main_s")) for r in selected_runs]
    offline = math.fsum(_seconds(unique[x]["seconds"]) for x in selected)
    average = math.fsum(main) / len(main)
    amortized = {}
    for count in amortizations:
        if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 1:
            raise ValueError("positive integer amortization count required")
        amortized[str(count)] = offline / count + average
    extra = math.fsum(_seconds(pilot.get(x, 0.0)) for x in ("serialization_s", "fresh_review_s"))
    experiment = offline + math.fsum(main)
    return dict(
        expense_ids=selected,
        offline_s=offline,
        main_total_s=math.fsum(main),
        main_mean_s=average,
        experiment_s=experiment,
        research_total_s=experiment + extra,
        serialization_and_fresh_s=extra,
        cold_mean_s=offline + average,
        amortized_mean_s=amortized,
        trials=len(main),
        method=method,
        epsilon=epsilon,
    )


def _coupling_proof(record, arrays):
    proof = record["coupling_diagnostic"]
    fine = np.asarray(arrays[proof["fine_normals_key"]], dtype=float)
    coarse = np.asarray(arrays[proof["coarse_normals_key"]], dtype=float)
    if (
        fine.ndim != 2
        or fine.shape[0] < 2
        or fine.shape[1] < 2
        or fine.shape[1] % 2
        or not np.isfinite(fine).all()
        or coarse.shape != (fine.shape[0], fine.shape[1] // 2)
    ):
        raise ValueError("invalid coupling diagnostic dimensions")
    expected = fine.reshape(len(fine), -1, 2).sum(axis=2) / math.sqrt(2)
    if not np.allclose(coarse, expected, rtol=1e-12, atol=1e-12):
        raise ValueError("coupling Brownian aggregation differs")
    p = proof["parameters"]
    for normals, key in [(fine, "fine_payoffs_key"), (coarse, "coarse_payoffs_key")]:
        dt = p["maturity"] / normals.shape[1]
        values = []
        for row in normals:
            stock = float(p["spot"])
            for shock in row:
                stock *= (
                    1
                    + (p["rate"] - p.get("yield_rate", 0.0)) * dt
                    + p["sigma"] * math.sqrt(dt) * float(shock)
                )
            values.append(math.exp(-p["rate"] * p["maturity"]) * max(stock - p["strike"], 0.0))
        actual = np.asarray(arrays[proof[key]], dtype=float)
        if actual.shape != (len(fine),) or not np.allclose(actual, values, rtol=1e-11, atol=1e-12):
            raise ValueError("coupling Euler payoff differs from scalar recurrence")
    return True


def decision(record: dict, arrays: dict) -> dict:
    """Recompute speed/accuracy evidence from the fixed roster's original arrays.

    This produces a teaching candidate, not final research acceptance: artifact
    rendering and independent review remain separate required evidence.
    Saved decision flags are ignored. A failed Euler cell remains failed even
    when exact comparators have valid results stored alongside it.
    """
    coupling = _coupling_proof(record, arrays)
    expected_epsilons = record["epsilons"]
    cells = record["budget_cells"]
    if len(cells) != len(expected_epsilons) or [c["epsilon"] for c in cells] != expected_epsilons:
        raise ValueError("budget roster differs from fixed epsilons")
    count = record["main_repetitions"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 2:
        raise ValueError("main roster needs at least two independent runs")
    names = ("mlmc", "plain_euler", "exact_plain", "exact_cv")
    failed, summaries = {}, []
    supported = 0
    reasons = []
    for cell in cells:
        if cell["status"] != "valid":
            reason = cell.get("reason")
            if not isinstance(reason, str) or not reason:
                raise ValueError("failed budget requires a reason")
            failed[reason] = failed.get(reason, 0) + 1
            summaries.append(dict(epsilon=cell["epsilon"], status="failed", reason=reason))
            continue
        if set(cell["methods"]) != set(names):
            raise ValueError("method roster differs from all four comparators")
        errors, times = {}, {}
        for name in names:
            method = cell["methods"][name]
            prices = _values(arrays[method["prices_key"]])
            elapsed = _values(arrays[method["seconds_key"]])
            if len(prices) != count or len(elapsed) != count:
                raise ValueError("original run roster is incomplete")
            if np.any(elapsed <= 0):
                raise ValueError("positive original run seconds required")
            errors[name] = error_summary(prices, cell["truth"])
            times[name] = elapsed
        ratio = paired_ratio_bootstrap(
            times["mlmc"],
            times["plain_euler"],
            seed=cell["bootstrap_seed"],
            resamples=record["bootstrap_resamples"],
        )
        accurate = all(errors[name]["rmse"] <= cell["epsilon"] for name in ("mlmc", "plain_euler"))
        faster = ratio["median_ratio"] < 1 and ratio["interval95"][1] < 1
        speedup = bool(accurate and faster)
        supported += int(speedup)
        if not accurate:
            reasons.append(
                f"epsilon={cell['epsilon']}: Euler comparator empirical RMSE exceeds target"
            )
        exact_best = min(
            float(np.median(times["exact_plain"])), float(np.median(times["exact_cv"]))
        )
        if exact_best <= float(np.median(times["mlmc"])):
            reasons.append(f"epsilon={cell['epsilon']}: exact terminal comparator is faster")
        cost_accounts = {}
        if record.get("offline_expenses"):
            run_rows = [
                {"main_s": float(elapsed), "method": name, "epsilon": cell["epsilon"]}
                for name in names
                for elapsed in times[name]
            ]
            cost_accounts = {
                name: cost_account(
                    {"expenses": record["offline_expenses"]},
                    run_rows,
                    method=name,
                    epsilon=cell["epsilon"],
                )
                for name in names
            }
            exact_cold = (
                min(
                    cost_accounts[name]["cold_mean_s"]
                    for name in ("exact_plain", "exact_cv")
                    if errors[name]["rmse"] <= cell["epsilon"]
                )
                if any(
                    errors[name]["rmse"] <= cell["epsilon"] for name in ("exact_plain", "exact_cv")
                )
                else None
            )
            if exact_cold is not None and cost_accounts["mlmc"]["cold_mean_s"] >= exact_cold:
                reasons.append(
                    f"epsilon={cell['epsilon']}: cold pilot-inclusive cost loses to exact terminal"
                )
        summaries.append(
            dict(
                epsilon=cell["epsilon"],
                status="valid",
                errors=errors,
                cost_ratio=ratio,
                cost_accounts=cost_accounts,
                speedup_supported=speedup,
            )
        )
    speedup_supported = supported >= 2
    if not speedup_supported:
        reasons.append("fewer than two epsilon cells support Euler speed improvement")
    for reason in failed:
        reasons.append(f"failed Euler cell: {reason}")
    return dict(
        coupling_verified=coupling,
        teaching_candidate=bool(coupling and summaries),
        speedup_supported_vs_euler=speedup_supported,
        supported_epsilon_count=supported,
        failed_cells=failed,
        standard_accelerator_rejected=bool(reasons),
        rejection_reasons=reasons,
        cells=summaries,
    )
