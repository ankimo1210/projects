"""Gates G1-G4 of the JGB term-premium re-test (design 2026-10-17 §5).

Computes no Japanese decomposition: G4 only checks the Japanese curve fits.

    $PY macrokit/research/2026-10-jgb-term-premium/gates.py \
        --data-root /home/kazumasa/projects/macrokit/data --processes 20
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import date
from pathlib import Path

import numpy as np

from macrokit.snapshot import latest_payload
from macrokit.sources import us_term
from macrokit.store import connect
from macrokit.termstructure import acm, dns, shadow, synthetic
from macrokit.termstructure.curve import ZeroPanel, fit_month_ends
from macrokit.termstructure.decompose import largest_rise_window, share_of

HERE = Path(__file__).resolve().parent
SEED = 20261017
G1_MONTHS = 20_000
G1_DRAWS = 10  # independent synthetic paths per DGP (spec §9, 2026-10-17)
WINDOW = 23  # end-July 2024 -> end-June 2026
TOL_SHARE, TOL_RMSE = 0.05, 0.15  # |mean(s_hat - s)| and median TP RMSE over the G1 draws
MODELS = ("acm", "acm_bc", "shadow", "dns")


def _commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, check=True
    ).stdout.strip()


def _rng(family: int, draw: int, stream: int = 0) -> np.random.Generator:
    """Fixed, distinct streams: family 1 affine, 2 DNS, 3 shadow; stream 1 = Kilian."""
    return np.random.default_rng([SEED, family, draw, stream])


def _draw_score(expected, true_expected, yields, i0, i1) -> dict:
    s_hat = float(share_of(expected, yields, i0, i1))
    s_true = float(share_of(true_expected, yields, i0, i1))
    rmse = float(np.sqrt(((expected - true_expected) ** 2).mean()))
    return {"share": s_hat, "true_share": s_true, "share_error": s_hat - s_true, "tp_rmse": rmse}


def _summary(draws: list[dict]) -> dict:
    """Design §5 G1: mean signed share error and median TP RMSE over the draws."""
    mean_error = float(np.mean([d["share_error"] for d in draws]))
    median_rmse = float(np.median([d["tp_rmse"] for d in draws]))
    return {
        "draws": draws,
        "mean_share_error": mean_error,
        "median_tp_rmse": median_rmse,
        "pass": abs(mean_error) <= TOL_SHARE and median_rmse <= TOL_RMSE,
    }


def g1(processes: int) -> dict:
    names = ("acm", "acm_bc", "acm_control", "dns", "dns_control", "shadow", "shadow_control")
    rows: dict[str, list[dict]] = {name: [] for name in names}
    seconds = []
    for r in range(G1_DRAWS):
        syn = synthetic.affine_dgp(G1_MONTHS, _rng(1, r))
        y = syn.panel.column(120)
        i0, i1 = largest_rise_window(y, WINDOW)
        fit = acm.fit_acm(syn.panel)
        corrected = acm.kilian_correct(fit.factors, fit.var, 1000, _rng(1, r, 1))
        bc = fit.expected(120, corrected.mu, corrected.phi)
        rows["acm"].append(_draw_score(fit.expected(120), syn.expected_pct, y, i0, i1))
        rows["acm_bc"].append(_draw_score(bc, syn.expected_pct, y, i0, i1))
        rows["acm_control"].append(_draw_score(syn.short_pct, syn.expected_pct, y, i0, i1))

        syn = synthetic.dns_dgp(G1_MONTHS, _rng(2, r))
        y = syn.panel.column(120)
        i0, i1 = largest_rise_window(y, WINDOW)
        e_dns = dns.fit_dns(syn.panel).expected(120)
        rows["dns"].append(_draw_score(e_dns, syn.expected_pct, y, i0, i1))
        rows["dns_control"].append(_draw_score(syn.short_pct, syn.expected_pct, y, i0, i1))

        sh = synthetic.shadow_dgp(G1_MONTHS, _rng(3, r), r_lower=0.0)
        i0, i1 = largest_rise_window(sh.yield_pct, WINDOW)
        started = time.perf_counter()
        starts = shadow.default_starts(sh.forwards)
        fit_sh = shadow.fit_shadow(sh.forwards, 0.0, starts, processes)
        states = shadow.filtered_states(fit_sh.theta, sh.forwards, 0.0)
        e_sh = shadow.expected_short_average(fit_sh.theta, states, 0.0, 120)
        seconds.append(round(time.perf_counter() - started, 1))
        rows["shadow"].append(_draw_score(e_sh, sh.expected_pct, sh.yield_pct, i0, i1))
        rows["shadow_control"].append(
            _draw_score(sh.short_pct, sh.expected_pct, sh.yield_pct, i0, i1)
        )
        print(f"G1 draw {r + 1}/{G1_DRAWS} done (shadow {seconds[-1]} s)", flush=True)
    out = {name: _summary(draws) for name, draws in rows.items()}
    out["shadow"]["seconds"] = seconds
    for model in ("acm", "dns", "shadow"):
        out[f"{model}_control"]["fails_as_required"] = not out[f"{model}_control"]["pass"]
    return out


def _us_panel(raw_root: Path, start: date, end: date, max_months: int) -> ZeroPanel:
    days = us_term.parse_gsw(latest_payload(raw_root, us_term.SOURCE, "gsw").read_bytes())
    ends = [d for d in us_term.month_end_days(days) if start <= d.obs_date <= end]
    months = np.arange(1, max_months + 1)
    yields = np.vstack([us_term.gsw_zero(d, months) for d in ends])
    return ZeroPanel(tuple(d.obs_date for d in ends), months, yields)


def _g2_once(panel: ZeroPanel, reference: dict) -> dict:
    def premium(p: ZeroPanel, k: int) -> np.ndarray:
        fit = acm.fit_acm(p, k=k)
        return fit.fitted_yield(120) - fit.fitted_yield(120, risk_neutral=True)

    keys = [(d.year, d.month) for d in panel.dates]
    have = [i for i, key in enumerate(keys) if key in reference]
    ref = np.array([reference[keys[i]]["ACMTP10"] for i in have])
    ours = premium(panel, 5)[have]
    i0, i1 = keys.index((2024, 7)), keys.index((2026, 6))
    delta_gap = abs(
        (ours[have.index(i1)] - ours[have.index(i0)])
        - (reference[(2026, 6)]["ACMTP10"] - reference[(2024, 7)]["ACMTP10"])
    )
    corr = float(np.corrcoef(ours, ref)[0, 1])
    rmse = float(np.sqrt(((ours - ref) ** 2).mean()))
    one_factor = float(np.corrcoef(premium(panel, 1)[have], ref)[0, 1])
    order = np.random.default_rng(SEED).permutation(len(panel.dates))
    shuffled = ZeroPanel(panel.dates, panel.months, panel.yields[order])
    by_date = dict(zip(order, premium(shuffled, 5), strict=True))
    shuffled_corr = float(np.corrcoef([by_date[i] for i in have], ref)[0, 1])
    return {
        "start": panel.dates[0].isoformat(),
        "corr": corr,
        "rmse": rmse,
        "delta_gap": float(delta_gap),
        "pass": corr >= 0.95 and rmse <= 0.25 and delta_gap <= 0.15,
        "control_one_factor_corr": one_factor,
        "control_shuffled_corr": shuffled_corr,
        "controls_fail_as_required": one_factor < 0.95 and shuffled_corr < 0.95,
    }


def g2(raw_root: Path) -> dict:
    reference = us_term.parse_acm(latest_payload(raw_root, us_term.SOURCE, "acm").read_bytes())
    first = _g2_once(_us_panel(raw_root, date(1961, 6, 1), date(2026, 6, 30), 120), reference)
    attempts = [first]
    if not first["pass"]:
        attempts.append(
            _g2_once(_us_panel(raw_root, date(1971, 8, 1), date(2026, 6, 30), 120), reference)
        )
    passed = [a for a in attempts if a["pass"] and a["controls_fail_as_required"]]
    return {"attempts": attempts, "pass": bool(passed)}


def g3(raw_root: Path, processes: int) -> dict:
    panel = _us_panel(raw_root, date(1990, 1, 1), date(2022, 2, 28), 121)
    forwards = shadow.panel_forwards(panel)
    fit = shadow.fit_shadow(forwards, 0.25, shadow.default_starts(forwards), processes)
    states = shadow.filtered_states(fit.theta, forwards, 0.25)
    gaussian = shadow.expected_gaussian_average(fit.theta, states, 120)
    low_gap = float(
        np.abs(shadow.expected_short_average(fit.theta, states, -10.0, 120) - gaussian).max()
    )
    zero_gap = float(
        np.abs(shadow.expected_short_average(fit.theta, states, 0.0, 120) - gaussian).max()
    )
    equality = {
        "max_gap_low_bound": low_gap,
        "pass": low_gap <= 0.01,
        "control_gap_zero_bound": zero_gap,
        "control_fails_as_required": zero_gap > 0.01,
    }
    path = latest_payload(raw_root, us_term.SOURCE, "wuxia")
    published = us_term.parse_wuxia(path.read_bytes()) if path else {}
    windows = ((date(2009, 1, 1), date(2015, 11, 30)), (date(2020, 4, 1), date(2022, 2, 28)))
    rate = shadow.shadow_rate(fit.theta, states)
    pairs = [
        (rate[i], published[(d.year, d.month)])
        for i, d in enumerate(panel.dates)
        if (d.year, d.month) in published and any(a <= d <= b for a, b in windows)
    ]
    comparison = None
    if pairs:
        ours, theirs = (np.array(v) for v in zip(*pairs, strict=True))
        corr = float(np.corrcoef(ours, theirs)[0, 1])
        comparison = {"months": len(pairs), "corr": corr, "pass": corr >= 0.9}
    passed = (
        equality["pass"]
        and equality["control_fails_as_required"]
        and (comparison is None or comparison["pass"])
    )
    return {
        "equality": equality,
        "wuxia": comparison,
        "negloglik_by_start": sorted(float(v) for v in fit.start_negloglik),
        "pass": passed,
    }


def g4(data_root: Path) -> dict:
    con = connect(data_root / "macrokit.duckdb")
    fits = fit_month_ends(con, date(1986, 8, 1), date(2026, 6, 30))
    errors = np.concatenate([np.abs(f.errors_bp) for f in fits])
    worst = [
        {"date": f.obs_date.isoformat(), "max_bp": float(np.abs(f.errors_bp).max())}
        for f in fits
        if np.abs(f.errors_bp).max() > 10
    ]
    missing = [f.obs_date.isoformat() for f in fits if f.overnight is None]
    median = float(np.median(errors))
    return {
        "months": len(fits),
        "first": fits[0].obs_date.isoformat(),
        "last": fits[-1].obs_date.isoformat(),
        "median_abs_error_bp": median,
        "months_over_10bp": worst,
        "months_without_overnight": missing,
        "pass": median <= 3.0 and not missing and len(fits) == 479,
    }


def passed_models(report: dict) -> list[str]:
    if not report["g4"]["pass"]:
        return []
    ok = {
        "acm": report["g1"]["acm"]["pass"] and report["g2"]["pass"],
        "acm_bc": report["g1"]["acm_bc"]["pass"] and report["g2"]["pass"],
        "shadow": report["g1"]["shadow"]["pass"] and report["g3"]["pass"],
        "dns": report["g1"]["dns"]["pass"],
    }
    return [m for m in MODELS if ok[m]]


def _plain(value):
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--processes", type=int, default=20)
    args = parser.parse_args()
    raw = args.data_root / "raw"
    report = {"code_commit": _commit(), "g4": g4(args.data_root)}
    print("G4", json.dumps(_plain(report["g4"]))[:300], flush=True)
    report["g2"] = g2(raw)
    print("G2", report["g2"]["pass"], flush=True)
    report["g3"] = g3(raw, args.processes)
    print("G3", report["g3"]["pass"], flush=True)
    report["g1"] = g1(args.processes)
    print("G1", {k: v.get("pass") for k, v in report["g1"].items()}, flush=True)
    report["passed_models"] = passed_models(report)
    (HERE / "gates.json").write_text(json.dumps(_plain(report), indent=2) + "\n", encoding="utf-8")
    print("passed:", report["passed_models"])


if __name__ == "__main__":
    main()
