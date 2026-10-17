"""Run the Japanese decomposition once, from a frozen configuration (design §2.4).

$PY run_japan.py --freeze          # after the gates: record commits and the hash
$PY run_japan.py --data-root /home/kazumasa/projects/macrokit/data --processes 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from collections.abc import Callable
from datetime import date
from functools import partial
from pathlib import Path

import numpy as np

from macrokit.store import connect
from macrokit.termstructure import acm, decompose, dns, shadow
from macrokit.termstructure.curve import ZeroPanel, fit_month_ends, zero_panel
from macrokit.termstructure.decompose import (
    Decomposition,
    interval,
    month_end_in,
    share_of,
    verdict,
)

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
GATES = HERE / "gates.json"
CODE_PATHS = ("macrokit/src", "macrokit/research/2026-10-jgb-term-premium/run_japan.py")


def canonical(config: dict) -> bytes:
    body = {k: v for k, v in config.items() if k != "sha256"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def config_hash(config: dict) -> str:
    return hashlib.sha256(canonical(config)).hexdigest()


def check_hash(config: dict) -> None:
    if config.get("sha256") != config_hash(config):
        raise ValueError(
            "config.json sha256 does not match its content; re-freeze is not allowed after results"
        )


def _to_json(value):
    """Plain Python values for json.dumps: numpy values are converted, non-finite floats are None."""
    if isinstance(value, dict):
        return {
            (k.item() if isinstance(k, np.generic) else k): _to_json(v) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [_to_json(v) for v in value]
    if isinstance(value, np.ndarray):
        return _to_json(value.tolist())
    if isinstance(value, np.generic):
        return _to_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _interval_or_none(samples, level: float) -> list[float] | None:
    """The central interval of the draws, or None when there are no draws."""
    if np.asarray(samples).size == 0:
        return None
    return list(interval(samples, level))


def _unpenalised(negloglik: float) -> bool:
    """False for a penalised optimum: the penalty is 1e12, so half of it is far above any fit."""
    return bool(np.isfinite(negloglik) and negloglik < 0.5 * shadow.PENALTY)


def _start_order(row: dict) -> float:
    """Sort key of a shadow start: ascending negloglik, with None and non-finite values last."""
    value = row["negloglik"]
    return value if value is not None and math.isfinite(value) else math.inf


def _attempt(fn: Callable[[], object]):
    """fn(), or its error text: a failed supplementary item must not lose the main results."""
    try:
        return fn()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=HERE, capture_output=True, text=True, check=True
    ).stdout.strip()


def _dirty(*paths: str) -> str:
    """Tracked files that differ from HEAD under ``paths`` (given from the repository root)."""
    top = [f":/{path}" for path in paths]
    return _git("status", "--porcelain", "--untracked-files=no", "--", *top)


def _code_unchanged(since: str, paths: tuple[str, ...] = CODE_PATHS) -> bool:
    top = _git("rev-parse", "--show-toplevel")
    return (
        subprocess.run(["git", "diff", "--quiet", since, "HEAD", "--", *paths], cwd=top).returncode
        == 0
    )


def _read_gates() -> tuple[dict, str]:
    """gates.json parsed, and the sha256 of the exact bytes that were parsed."""
    raw = GATES.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _check_controls(gates: dict) -> None:
    """Gates whose negative controls did not fail are uninformative: no run may rest on them."""
    if gates.get("controls_ok") is not True:
        raise SystemExit("gates.json controls_ok is not true; the gates are uninformative")


def _check_constants(cfg: dict) -> None:
    """Settings that the code reads from its own constants must match the configuration."""
    n_starts = (
        len(shadow.RHO_Q_STARTS) * len(shadow.SIGMA_DIAG_STARTS) * len(shadow.SIGMA_OFFDIAG_STARTS)
    )
    checks = {
        "verdict_band": tuple(cfg["verdict_band"]) == decompose.VERDICT_BAND,
        "acm.return_months": cfg["acm"]["return_months"] == acm.RETURN_MONTHS.tolist(),
        "acm.factor_months": cfg["acm"]["factor_months"] == "3..120 step 3"
        and acm.FACTOR_MONTHS.tolist() == list(range(3, 121, 3)),
        "shadow.starts": cfg["shadow"]["starts"] == 20 and n_starts == 20,
        "shadow.forward_months": cfg["shadow"]["forward_months"] == shadow.FORWARD_MONTHS.tolist(),
    }
    wrong = [field for field, ok in checks.items() if not ok]
    if wrong:
        raise SystemExit(f"config.json differs from the code constants: {', '.join(wrong)}")


def freeze() -> None:
    if _dirty("macrokit"):
        raise SystemExit("commit everything under macrokit/ before freezing")
    config = json.loads(CONFIG.read_text())
    if config.get("sha256") or (HERE / "results.json").exists():
        raise SystemExit("already frozen; a new configuration is a new study (design §2.4)")
    _check_constants(config)
    gates, gates_sha256 = _read_gates()
    _check_controls(gates)
    if not _code_unchanged(gates["code_commit"], ("macrokit/src",)):
        raise SystemExit("macrokit/src changed after the gates ran; re-run the gates first")
    config["code_commit"] = _git("rev-parse", "HEAD")
    config["gates_commit"] = gates["code_commit"]
    config["gates_sha256"] = gates_sha256  # the frozen hash covers the gate results
    config["sha256"] = config_hash(config)
    CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("frozen:", config["sha256"])


def _month(text: str) -> tuple[int, int]:
    year, month = text.split("-")[:2]
    return int(year), int(month)


def _estimate(
    panel: ZeroPanel, cfg: dict, processes: int, maturities: list[int], intervals: bool
) -> dict:
    """Point estimates (and optionally interval draws) for the four models.

    A shadow-rate fit that ends at a penalised optimum has no decomposition (None) and no
    draws; the other three models are unaffected.
    """
    seeds = cfg["seeds"]
    fit_a = acm.fit_acm(panel, k=cfg["acm"]["k"])
    bc = acm.kilian_correct(
        fit_a.factors,
        fit_a.var,
        cfg["bias_correction"]["n_boot"],
        np.random.default_rng(seeds["acm_bc"]),
    )
    fit_d = dns.fit_dns(panel, lam=cfg["dns"]["lambda"])
    forwards = shadow.panel_forwards(panel, np.array(cfg["shadow"]["forward_months"]))
    fit_s = shadow.fit_shadow(
        forwards,
        cfg["shadow"]["r_lower_pct"],
        shadow.default_starts(forwards),
        processes,
        cfg["shadow"]["maxiter"],
    )
    shadow_ok = _unpenalised(fit_s.negloglik)
    out: dict = {
        "decomposition": {},
        "draws": {},
        "fits": {"acm_bc_shrink": bc.shrink, "shadow": fit_s, "shadow_ok": shadow_ok},
    }
    for n in maturities:
        out["decomposition"][n] = {
            "acm": acm.decompose_acm(panel, fit_a, n),
            "acm_bc": acm.decompose_acm(panel, fit_a, n, bc.mu, bc.phi, model="acm_bc"),
            "shadow": shadow.decompose_shadow(fit_s, forwards, panel, n) if shadow_ok else None,
            "dns": dns.decompose_dns(panel, fit_d, n),
        }
    if intervals:
        n_boot, horizon = cfg["intervals"]["n_boot"], cfg["maturity_months"]
        out["draws"] = {
            "acm": acm.bootstrap_expected(
                fit_a, horizon, n_boot, np.random.default_rng(seeds["acm"])
            ),
            "acm_bc": acm.bootstrap_expected(
                fit_a,
                horizon,
                n_boot,
                np.random.default_rng(seeds["acm_bc"] + 1),
                correction_boot=cfg["bias_correction"]["n_boot"],
            ),
            "dns": dns.bootstrap_expected_dns(
                fit_d, horizon, n_boot, np.random.default_rng(seeds["dns"])
            ),
        }
        if shadow_ok:
            expected, rejected, floored = shadow.draw_expected(
                fit_s,
                forwards,
                horizon,
                cfg["intervals"]["n_draws"],
                np.random.default_rng(seeds["shadow"]),
            )
            out["draws"]["shadow"] = expected
            out["fits"]["shadow_draws"] = {"rejected": rejected, "floored_eigenvalues": floored}
        else:
            out["draws"]["shadow"] = np.empty((0, len(panel.dates)))
            out["fits"]["shadow_draws"] = None
    return out


def _shares(decs: dict, t0: date, t1: date, models: list[str]) -> dict:
    return {m: None if decs[m] is None else decs[m].share(t0, t1) for m in models}


def _maturity_shares(main_run: dict, n: int, t0: date, t1: date, models: list[str]) -> dict:
    return _shares(main_run["decomposition"][n], t0, t1, models)


def _t0_alt_shares(panel: ZeroPanel, cfg: dict, decs: dict, t1: date) -> dict:
    t0_alt = month_end_in(panel.dates, *_month(cfg["supplementary"]["t0_alt_month"]))
    return {"t0": t0_alt.isoformat(), "shares": _shares(decs, t0_alt, t1, cfg["models"])}


def _window_shares(
    panel: ZeroPanel, cfg: dict, processes: int, start: str, t0: date, t1: date
) -> dict:
    horizon = cfg["maturity_months"]
    sub = panel.window(date.fromisoformat(start), panel.dates[-1])
    run = _estimate(sub, cfg, processes, [horizon], intervals=False)
    return _shares(run["decomposition"][horizon], t0, t1, cfg["models"])


def _latest_shares(full: ZeroPanel, cfg: dict, processes: int, t0: date) -> dict:
    horizon = cfg["maturity_months"]
    latest = _estimate(full, cfg, processes, [horizon], intervals=False)
    return {
        "t1": full.dates[-1].isoformat(),
        "shares": _shares(latest["decomposition"][horizon], t0, full.dates[-1], cfg["models"]),
    }


def _acm_k3_share(panel: ZeroPanel, cfg: dict, t0: date, t1: date) -> float:
    k3 = acm.fit_acm(panel, k=3)
    return acm.decompose_acm(panel, k3, cfg["maturity_months"]).share(t0, t1)


def _long_acm_shares(panel: ZeroPanel, cfg: dict, t0: date, t1: date) -> dict:
    long_panel = panel.window(
        date.fromisoformat(cfg["supplementary"]["long_acm_start"]), panel.dates[-1]
    )
    long_fit = acm.fit_acm(
        long_panel,
        k=cfg["acm"]["k"],
        factor_months=acm.LONG_FACTOR_MONTHS,
        return_months=acm.LONG_RETURN_MONTHS,
    )
    return {
        f"maturity_{n}": acm.decompose_acm(long_panel, long_fit, n).share(t0, t1)
        for n in (120, 240, 360)
    }


def _write_results(results: dict) -> None:
    """Write beside the target and rename, so a reader never sees half a file."""
    tmp = HERE / "results.json.tmp"
    tmp.write_text(json.dumps(_to_json(results), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, HERE / "results.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--processes", type=int, default=20)
    args = parser.parse_args()
    if args.freeze:
        freeze()
        return
    if args.data_root is None:
        parser.error("--data-root is required for the run")
    if (HERE / "results.json").exists():
        raise SystemExit("results.json exists; the Japanese run happens once (design §2.4)")
    cfg = json.loads(CONFIG.read_text())
    check_hash(cfg)
    _check_constants(cfg)
    if not _code_unchanged(cfg["code_commit"]) or _dirty(*CODE_PATHS):
        raise SystemExit("code differs from the frozen commit")
    gates, gates_sha256 = _read_gates()
    _check_controls(gates)
    if gates["code_commit"] != cfg["gates_commit"] or gates_sha256 != cfg.get("gates_sha256"):
        raise SystemExit("gates.json changed after the freeze")
    models = [m for m in cfg["models"] if m in gates["passed_models"]]

    con = connect(args.data_root / "macrokit.duckdb")
    full = zero_panel(
        fit_month_ends(con, date.fromisoformat(cfg["estimation_start"]), date.today())
    )
    panel = full.window(full.dates[0], date.fromisoformat(cfg["estimation_end"]))
    t0 = month_end_in(panel.dates, *_month(cfg["t0_month"]))
    t1 = month_end_in(panel.dates, *_month(cfg["t1_month"]))
    i0, i1 = panel.dates.index(t0), panel.dates.index(t1)
    horizon = cfg["maturity_months"]

    main_run = _estimate(
        panel, cfg, args.processes, [horizon, *cfg["supplementary_maturities"]], intervals=True
    )
    decs = main_run["decomposition"][horizon]
    y = panel.column(horizon)
    used = [m for m in models if decs[m] is not None]
    results: dict = {
        "config_sha256": cfg["sha256"],
        "code_commit": cfg["code_commit"],
        "t0": t0.isoformat(),
        "t1": t1.isoformat(),
        "delta_yield_pct": float(y[i1] - y[i0]),
        "models_used": used,
        "models_excluded_after_estimation": [m for m in models if decs[m] is None],
        "main": {},
    }
    for m in cfg["models"]:
        if decs[m] is None:
            results["main"][m] = {
                "share": None,
                "interval": None,
                "contains_half": None,
                "delta_expected_pct": None,
                "passed_gates": m in models,
                "estimation_failed": True,
            }
            continue
        band = _interval_or_none(
            share_of(main_run["draws"][m], y, i0, i1), cfg["intervals"]["level"]
        )
        results["main"][m] = {
            "share": decs[m].share(t0, t1),
            "interval": band,
            "contains_half": None if band is None else band[0] <= 0.5 <= band[1],
            "delta_expected_pct": float(decs[m].expected_pct[i1] - decs[m].expected_pct[i0]),
            "passed_gates": m in models,
            "estimation_failed": False,
        }
    results["verdict"] = verdict({m: results["main"][m]["share"] for m in used})
    rw = Decomposition("random_walk", panel.dates, y, panel.column(1))
    results["brackets"] = {"constant_premium": 1.0, "random_walk": rw.share(t0, t1)}

    fit_s = main_run["fits"]["shadow"]
    forwards = shadow.panel_forwards(panel, np.array(cfg["shadow"]["forward_months"]))
    by_start = []
    for value, theta in zip(fit_s.start_negloglik, fit_s.start_theta, strict=True):
        row: dict = {"negloglik": float(value), "share": None}
        if _unpenalised(value):  # a penalised optimum has no filtered states
            try:
                states = shadow.filtered_states(theta, forwards, fit_s.r_lower)
                e = shadow.expected_short_average(theta, states, fit_s.r_lower, horizon)
                row["share"] = float(share_of(e, y, i0, i1))
            except ValueError as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
        by_start.append(row)
    results["shadow_starts"] = sorted(by_start, key=_start_order)
    results["shadow_draws"] = main_run["fits"].get("shadow_draws")
    results["acm_bc_shrink"] = main_run["fits"]["acm_bc_shrink"]

    # The main block is complete: write it before anything supplementary can fail.
    _write_results(results)
    print("MAIN RESULTS", flush=True)
    summary = _to_json({"verdict": results["verdict"], "main": results["main"]})
    print(json.dumps(summary, indent=2), flush=True)

    supp: dict = {}
    for n in cfg["supplementary_maturities"]:
        supp[f"maturity_{n}"] = _attempt(
            partial(_maturity_shares, main_run, n, t0, t1, cfg["models"])
        )
    supp["t0_alt"] = _attempt(partial(_t0_alt_shares, panel, cfg, decs, t1))
    for start in cfg["supplementary"]["windows"]:
        supp[f"window_{start}"] = _attempt(
            partial(_window_shares, panel, cfg, args.processes, start, t0, t1)
        )
    supp["t1_latest"] = _attempt(partial(_latest_shares, full, cfg, args.processes, t0))
    supp["acm_k3"] = _attempt(partial(_acm_k3_share, panel, cfg, t0, t1))
    supp["long_acm"] = _attempt(partial(_long_acm_shares, panel, cfg, t0, t1))
    results["supplementary"] = supp
    _write_results(results)
    print("supplementary results written")


if __name__ == "__main__":
    main()
