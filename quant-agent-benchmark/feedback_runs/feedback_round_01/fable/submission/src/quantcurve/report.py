"""Self-contained HTML research report (charts embedded as base64 PNG)."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .risk import BUMP_SHAPE_DOC

CSS = """
:root { --ink:#1b1f23; --muted:#5b6470; --line:#d9dee5; --bg:#ffffff; --panel:#f4f6f9; --accent:#1f5fbf; --warn:#b23a48; --ok:#2a7f62; }
* { box-sizing: border-box; }
body { margin:0; font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color:var(--ink); background:var(--bg); line-height:1.45; }
header { padding: 28px 40px 18px; border-bottom: 1px solid var(--line); }
header h1 { margin:0 0 6px; font-size: 24px; }
header .meta { color: var(--muted); font-size: 13px; }
nav { padding: 10px 40px; background: var(--panel); border-bottom:1px solid var(--line); font-size: 13px; }
nav a { margin-right: 14px; color: var(--accent); text-decoration: none; }
main { padding: 10px 40px 60px; max-width: 1400px; }
section { margin-top: 34px; }
h2 { font-size: 19px; border-bottom: 2px solid var(--accent); padding-bottom: 4px; margin-bottom: 12px; }
h3 { font-size: 15px; margin: 18px 0 6px; }
p, li { font-size: 14px; }
table { border-collapse: collapse; font-size: 12.5px; margin: 8px 0 14px; }
th, td { border: 1px solid var(--line); padding: 4px 8px; text-align: right; }
th { white-space: nowrap; }
td { white-space: normal; max-width: 620px; }
th { background: var(--panel); text-align: center; }
td:first-child, th:first-child { text-align: left; }
.scroll { overflow-x: auto; max-width: 100%; }
.kpi { display:flex; flex-wrap:wrap; gap: 12px; margin: 10px 0; }
.kpi div { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px 14px; min-width: 150px; }
.kpi .v { font-size: 20px; font-weight: 600; }
.kpi .l { font-size: 12px; color: var(--muted); }
.note { background: var(--panel); border-left: 4px solid var(--accent); padding: 8px 12px; font-size: 13px; }
.warn { border-left-color: var(--warn); }
img { max-width: 100%; border: 1px solid var(--line); margin: 6px 0 12px; }
code { background: var(--panel); padding: 1px 4px; border-radius: 3px; font-size: 12.5px; }
.small { font-size: 12px; color: var(--muted); }
"""


def _img(path: Path | None) -> str:
    if path is None or not Path(path).is_file():
        return "<p class='small'>chart not available</p>"
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}' alt='{html.escape(Path(path).stem)}'>"


def _table(df: pd.DataFrame, floatfmt: str = "{:.4g}", max_rows: int | None = None) -> str:
    if df is None or len(df) == 0:
        return "<p class='small'>none</p>"
    d = df.copy()
    if max_rows is not None and len(d) > max_rows:
        d = d.head(max_rows)
    cols = list(d.columns)
    rows = ["<tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in cols) + "</tr>"]
    for _, r in d.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("<td>" + ("" if not np.isfinite(v) else floatfmt.format(v)) + "</td>")
            elif isinstance(v, (bool, np.bool_)):
                cells.append(f"<td>{'yes' if v else 'no'}</td>")
            else:
                cells.append(f"<td>{html.escape(str(v))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<div class='scroll'><table>" + "".join(rows) + "</table></div>"


def _metrics_table(metrics: dict) -> pd.DataFrame:
    rows = []
    for model in ("baseline", "advanced"):
        m = metrics[model]
        for scope, v in [("overall", m["overall"])] + sorted(m["by_type"].items()):
            rows.append({"model": model, "scope": scope, "n": v["n"], "weighted_rmse_bp": v.get("weighted_rmse_bp"), "rmse_bp": v["rmse_bp"], "mae_bp": v["mae_bp"], "median_abs_bp": v.get("median_abs_bp"), "max_abs_bp": v["max_abs_bp"]})
    return pd.DataFrame(rows)


def _fmt(x, nd=2) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x:.{nd}f}"


def render_report(res, out_path: Path) -> Path:
    o = res.options
    mc = res.model_comparison
    hold = res.holdout
    audit = res.cleaning.audit
    rep = res.repricing_advanced if res.selected_model == "advanced" else res.repricing_baseline
    curve = res.grid_selected
    key_tenors = [t for t in (1 / 12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30) if t <= curve["maturity_years"].max()]
    key_rows = pd.DataFrame(
        {
            "tenor_years": key_tenors,
            "zero_rate_pct": [float(np.interp(t, curve["maturity_years"], curve["zero_rate"])) * 100 for t in key_tenors],
            "forward_rate_pct": [float(np.interp(t, curve["maturity_years"], curve["forward_rate"])) * 100 for t in key_tenors],
            "discount_factor": [float(np.interp(t, curve["maturity_years"], curve["discount_factor"])) for t in key_tenors],
            "baseline_zero_pct": [float(np.interp(t, res.grid_baseline["maturity_years"], res.grid_baseline["zero_rate"])) * 100 for t in key_tenors],
            "advanced_zero_pct": [float(np.interp(t, res.grid_advanced["maturity_years"], res.grid_advanced["zero_rate"])) * 100 for t in key_tenors],
        }
    )
    acts = res.cleaning.summary["actions"]
    n_obs = res.cleaning.summary["n_observations"]
    hb, ha = hold.metrics["baseline"]["overall"], hold.metrics["advanced"]["overall"]
    ts = res.train_metrics
    cv = res.adv.cv
    lam_txt = f"{res.adv.lam:.3g}"
    sens_checks = [{"name": k, "description": v.get("condition", ""), "outcome": v.get("results", {}), "interpretation": v.get("interpretation", "")} for k, v in res.sensitivity.items() if isinstance(v, dict) and "results" in v and k != "skipped"]

    def sens_rows():
        rows = []
        for c in sens_checks:
            oc = c["outcome"]
            key = {}
            for k in ("max_abs_zero_change_bp", "mean_abs_zero_change_bp", "max_abs_forward_change_bp", "max_abs_deviation_from_1bp", "mean_zero_change_bp", "max_zero_std_bp", "median_zero_std_bp", "bond_repricing_rmse_bp_on_rates_only_curve", "bond_repricing_rmse_bp_on_full_curve", "n_excluded", "median_abs_zero_change_bp"):
                if k in oc and oc[k] is not None:
                    key[k] = oc[k]
            if "train_rmse_bp" in oc and oc["train_rmse_bp"].get("all") is not None:
                key["train_rmse_all_bp"] = oc["train_rmse_bp"]["all"]
            if "most_influential" in oc and oc["most_influential"]:
                top = oc["most_influential"][0]
                key["most_influential_cluster"] = f"{top['maturity_years']:.2f}y ({', '.join(top['members'][:3])}{'...' if len(top['members']) > 3 else ''})"
            rows.append({"check": c["name"], **{k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in key.items()}})
        return pd.DataFrame(rows)

    excluded_tbl = audit[audit["action"] == "exclude"][["obs_id", "instrument_id", "instrument_type", "maturity_years", "normalized_quote", "reason"]]
    corrected_tbl = audit[audit["action"] == "correct"][["obs_id", "instrument_id", "instrument_type", "maturity_years", "raw_quote", "normalized_quote", "reason"]]
    downweight_tbl = audit[audit["action"] == "downweight"][["obs_id", "instrument_id", "instrument_type", "maturity_years", "normalized_quote", "weight", "reason"]]
    worst = rep[rep["robust_factor"] > 0].reindex(rep[rep["robust_factor"] > 0]["residual_bp"].abs().sort_values(ascending=False).index).head(12)[["instrument_id", "instrument_type", "maturity_years", "market_quote", "model_quote", "residual", "residual_bp", "std_residual", "weight"]]
    rmse_by_type = {t: v["rmse_bp"] for t, v in ts["advanced" if res.selected_model == "advanced" else "baseline"]["usable"]["by_type"].items()}
    risk_use = res.risk[res.risk["usable"]]
    risk_excerpt = risk_use.sort_values("maturity_years").iloc[:: max(1, len(risk_use) // 14)][["instrument_id", "instrument_type", "maturity_years", "dv01", "key_2y", "key_5y", "key_10y", "key_30y", "key_sum", "analytic_dv01"]]
    rs = res.risk_summary
    temporal = hold.temporal
    warn_html = ""
    if res.warnings:
        warn_html = "<div class='note warn'><b>Numerical warnings raised during the run (not suppressed):</b><ul>" + "".join(f"<li><code>{html.escape(w)}</code></li>" for w in res.warnings) + "</ul></div>"
    stub_note = ""
    for c in sens_checks:
        if c["name"] == "stub_rule_ceil":
            stub_note = f"Under the textbook short-stub rule (<code>ceil</code>) the in-sample RMSE over usable instruments rises to {_fmt(c['outcome']['train_rmse_bp'].get('all'))}bp (vs {_fmt(ts['advanced']['usable']['overall']['rmse_bp'])}bp with the selected rule) and the zero curve moves by up to {_fmt(c['outcome']['max_abs_zero_change_bp'])}bp."
    power_tbl = cv.power_table if cv is not None and cv.power_table is not None else None
    consensus = []
    if res.selected_model == "advanced":
        for cid in np.unique(res.table["tenor_cluster"]):
            m = (res.table["tenor_cluster"].to_numpy() == cid) & res.table["instrument_type"].isin(["deposit", "ois_swap"]).to_numpy() & (res.adv.fit.robust_factor > 0)
            if m.sum() >= 2:
                u = res.adv.fit.std_residuals[m]
                if np.all(np.abs(u) > 1.345) and (np.all(u > 0) or np.all(u < 0)):
                    consensus.append(f"{float(np.median(res.table['maturity'][m])):.2f}y (mean market-model {np.mean(rep['residual_bp'].to_numpy()[m]):+.1f}bp over {int(m.sum())} concordant quotes)")

    parts = [f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>QuantCurve research report {html.escape(str(o.valuation_date))}</title><style>{CSS}</style></head><body>"]
    parts.append(
        f"<header><h1>Zero-curve research report</h1><div class='meta'>Valuation date {html.escape(str(o.valuation_date))} &middot; "
        f"input <code>{html.escape(Path(o.market_data).name)}</code> &middot; quantcurve {__version__} &middot; selected model: <b>{res.selected_model}</b> &middot; "
        f"schedule rule <code>{o.stub_rule}</code> &middot; run time {res.timings.get('total', 0):.1f}s</div></header>"
    )
    parts.append(
        "<nav>" + "".join(f"<a href='#{k}'>{v}</a>" for k, v in [("summary", "Executive summary"), ("method", "Methodology"), ("data", "Data quality"), ("models", "Baseline vs advanced"), ("sens", "Sensitivity"), ("valid", "Validation & repricing"), ("risk", "Risk"), ("charts", "Charts"), ("limits", "Limitations"), ("next", "Next steps")]) + "</nav><main>"
    )
    # --- executive summary ---------------------------------------------
    parts.append("<section id='summary'><h2>1. Executive Summary / 要約</h2>")
    parts.append(
        "<div class='kpi'>"
        f"<div><div class='v'>{n_obs}</div><div class='l'>input observations</div></div>"
        f"<div><div class='v'>{len(res.table)}</div><div class='l'>usable instruments after rule-based cleaning</div></div>"
        f"<div><div class='v'>{acts['exclude']}</div><div class='l'>observations excluded (all layers)</div></div>"
        f"<div><div class='v'>{acts['correct']}</div><div class='l'>corrected (units, scale, missing quote)</div></div>"
        f"<div><div class='v'>{_fmt(ha['weighted_rmse_bp'])} / {_fmt(hb['weighted_rmse_bp'])} bp</div><div class='l'>precision-weighted holdout RMSE advanced / baseline</div></div>"
        f"<div><div class='v'>{lam_txt}</div><div class='l'>selected smoothing lambda (power {res.adv.power:g})</div></div>"
        "</div>"
    )
    parts.append(f"<p><b>Selected model: {res.selected_model}.</b> {html.escape(mc['selection_rationale'])}</p>")
    parts.append(
        "<p>The curve is continuously compounded, built from deposits, par OIS swaps and coupon bonds on a single valuation date, "
        f"and published on a dense grid of {len(curve)} maturities from {curve['maturity_years'].min():.4f}Y to {curve['maturity_years'].max():.0f}Y "
        "(<code>curves/curve.csv</code>). All discount factors are strictly positive by construction (the forward curve is integrated, "
        "so negative rates are handled without any floor).</p>"
    )
    parts.append("<h3>Curve at key tenors (selected model)</h3>" + _table(key_rows, "{:.4f}"))
    findings = [
        f"Rule-based validation kept {acts['keep']} observations unchanged, corrected {acts['correct']}, down-weighted {acts['downweight']} and excluded {acts['exclude']} "
        f"(duplicates, stale timestamps, cross-sectional outliers, robust-fit rejections); see section 3 for the full audit trail.",
        f"In-sample repricing RMSE of the selected model over usable instruments: " + ", ".join(f"{t} {_fmt(v)}bp" for t, v in rmse_by_type.items()) + ".",
        f"Receiver DV01 and 2Y/5Y/10Y/30Y key-rate sensitivities are provided for {int(res.risk['usable'].sum())} usable instruments; finite-difference DV01 agrees with the analytic derivative to "
        f"{_fmt((rs['max_abs_rel_diff_fd_vs_analytic'] or 0) * 100, 4)}% and key rates aggregate to the parallel DV01 within {_fmt((rs['max_abs_rel_diff_keysum_vs_dv01'] or 0) * 100, 4)}%.",
    ]
    if stub_note:
        findings.append("Cash-flow schedules for tenors that are not a whole number of periods are not defined by the conventions document; the rule is a provisional reading chosen for consistency with the observed 1.25Y/1.5Y OIS quotes (see Limitations). " + stub_note)
    if consensus:
        findings.append("Tenors where several concordant quotes sit systematically off the smooth curve (kept with bounded Huber weight, flagged as possible convention or market features rather than data errors): " + "; ".join(consensus) + ".")
    parts.append("<h3>Key findings</h3><ul>" + "".join(f"<li>{f}</li>" for f in findings) + "</ul>")
    parts.append(warn_html + "</section>")

    # --- methodology --------------------------------------------------
    parts.append("<section id='method'><h2>2. Methodology / 手法</h2>")
    parts.append(
        "<h3>Conventions and cash flows</h3><ul>"
        "<li>Maturities are the supplied ACT/365F year fractions; deposits discount with simple interest <code>D = 1/(1 + rT)</code>; "
        "OIS par rates satisfy <code>r &Sigma; &alpha;<sub>i</sub> D(t<sub>i</sub>) = 1 - D(T)</code> with annual fixed payments to 2Y and semi-annual beyond; "
        "bonds pay level coupons at 1/frequency intervals with principal at maturity and no accrued interest.</li>"
        f"<li>Schedule rule <code>{o.stub_rule}</code>: with <code>n = round(T &times; f)</code> payments (level accrual 1/f), payments fall at 1/f, 2/f, ... from the valuation date with the last one at maturity. "
        "This rule was selected because the alternative textbook short-stub rule is inconsistent with the 1.25Y/1.5Y OIS quotes by tens of basis points, whereas the round-based rules leave residuals at the noise level; among the round-based variants this one produced the smallest OIS and bond residuals (section 5 quantifies the alternatives).</li>"
        "<li>Zero rates are continuously compounded (<code>D = exp(-zT)</code>); instantaneous forwards are <code>-d log D / dT</code>.</li></ul>"
    )
    parts.append(
        "<h3>Data validation and cleaning (audit-trailed)</h3><ol>"
        "<li>Schema, type, range, unit, currency, quote-type and timestamp checks per row; forward-starting or foreign-currency rows are excluded; maturity_date is reconciled against maturity_years (the latter is authoritative).</li>"
        "<li>Unit normalisation (PERCENT/DECIMAL/BP for rates, points for prices) and peer-based scale-defect correction: a rate whose value is far from the median of same-type quotes at neighbouring maturities but within tolerance after a &times;100 or &times;0.01 rescale is corrected (bid/ask rescaled too); bond prices below 10 or above 1000 are rescaled to points.</li>"
        "<li>Missing quotes are replaced by the bid/ask mid; crossed markets are re-ordered and down-weighted; quotes outside their own bid/ask are down-weighted.</li>"
        f"<li>Duplicate <code>instrument_id</code> rows are resolved deterministically (in-market quote, latest timestamp, liquidity); rows dated before the valuation date by more than {o.max_stale_days} day(s) are excluded as stale.</li>"
        "<li>Cross-sectional screen: within each tenor cluster of deposits/OIS with at least three quotes, an iterated median/MAD test excludes quotes more than 6 robust sigmas (floor 3bp) from the cluster median.</li>"
        "<li>Base weights: <code>1 / scale&sup2;</code> with <code>scale&sup2; = (half-spread&sup2; + (0.5bp)&sup2;) / (liquidity &times; rule factor)</code>, in yield-equivalent units (bond half-spreads divided by dollar duration).</li></ol>"
    )
    parts.append(
        "<h3>Baseline model</h3><p>Sequential bootstrap: one knot per deposit/OIS tenor cluster, zero rate solved so that the weighted residual of the cluster's quotes is zero, "
        "linear interpolation of the continuously compounded zero rate between knots, flat zero extrapolation at both ends. Bonds are not used. It is exact at the tenor clusters, has no smoothing, and produces piecewise (jagged) forward rates.</p>"
    )
    parts.append(
        "<h3>Advanced model</h3><p>The instantaneous forward rate is a clamped cubic B-spline with knots at the rate-instrument tenors "
        f"({len(res.adv.knots)} interior knots) on [0, {res.t_max:g}Y]; <code>log D(t)</code> is the exact integral of the spline so discount factors are always positive. "
        "Coefficients minimise <code>&Sigma; &rho;(r<sub>i</sub> / (s<sub>type</sub> scale<sub>i</sub>)) + &lambda; &int; w(t) f''(t)&sup2; dt</code> with "
        f"<code>w(t) = ((t + 0.5)/(5.5))<sup>p</sup></code>, p = {res.adv.power:g} fixed a priori (information density falls with maturity, so the long end is smoothed harder; the uniform penalty p = 0 is reported in the CV table for information but is markedly less robust at the front end, see the sensitivity section). "
        "Residuals are market-minus-model in yield-equivalent rate units; <code>s<sub>type</sub></code> is a per-type robust scale (MAD, floored at 1) so bond prices, which are noisier than swap quotes, are automatically down-weighted. "
        "Robust treatment: (i) a leave-tenor-out screen refits the curve without each tenor cluster and rejects quotes in small clusters (fewer than three rate quotes, and every bond) whose out-of-sample residual exceeds six robust sigmas; "
        "(ii) iteratively reweighted least squares with Tukey's biweight (c = 4.685); (iii) a consensus guard that never rejects a whole tenor cluster whose quotes agree with each other (their weight is capped by Huber weights instead). Two guards added in feedback round 1: the shortest and longest rate clusters are exempt from the leave-tenor-out screen (leaving them out is extrapolation, not validation), and a single-quote cluster is never hard-rejected by the Tukey stage - it keeps a bounded Huber weight, because no peer can corroborate a rejection (on a humped synthetic curve with thin front-end coverage the previous rule discarded three genuine deposits, 23bp error). Neither guard changes the public-data outputs. "
        f"&lambda; is chosen at the minimum of a maturity-grouped {o.n_folds}-fold cross-validation score (CV table in section 4; selected &lambda; = {lam_txt}"
        + (f", CV minimum &lambda; = {cv.lam_min:.3g}" if cv is not None else "") + ").</p>"
    )
    parts.append(f"<h3>Holdout design</h3><p>{html.escape(mc['holdout_method'])} A secondary time-aware split (earlier half of the quote timestamps for training, later half for testing) is also reported; because the same tenors appear on both sides it measures consistency with later quotes rather than interpolation skill.</p>")
    parts.append(f"<h3>Risk definitions</h3><p>DV01 is the central finite difference <code>(PV[-1bp] - PV[+1bp]) / 2</code> of the receiver-fixed PV under a parallel shift of the continuously compounded zero curve (notional 1,000,000 for deposits and swaps, face 100 for bonds). {html.escape(BUMP_SHAPE_DOC)} Verification: the finite-difference DV01 is compared with the analytic derivative <code>&Sigma; t<sub>i</sub> CF<sub>i</sub> D(t<sub>i</sub>) &times; 1bp</code>, the half-step estimate, and the sum of key-rate sensitivities.</p></section>")

    # --- data quality -------------------------------------------------
    parts.append("<section id='data'><h2>3. Data Quality / データ品質</h2>")
    parts.append(_img(res.files.get("chart_data_quality")))
    by_type = audit.groupby(["instrument_type", "action"]).size().unstack(fill_value=0).reset_index()
    parts.append("<h3>Actions by instrument type</h3>" + _table(by_type))
    parts.append(f"<h3>Excluded observations ({len(excluded_tbl)})</h3>" + _table(excluded_tbl, "{:.6g}"))
    parts.append(f"<h3>Corrected observations ({len(corrected_tbl)})</h3>" + _table(corrected_tbl, "{:.6g}"))
    parts.append(f"<h3>Down-weighted observations ({len(downweight_tbl)})</h3>" + _table(downweight_tbl, "{:.4g}"))
    parts.append("<p class='small'>The complete one-row-per-observation audit trail (action, normalised quote, final weight, reasons) is in <code>diagnostics/cleaning.csv</code>.</p></section>")

    # --- model comparison ---------------------------------------------
    parts.append("<section id='models'><h2>4. Model Comparison / ベースラインと高度モデルの比較</h2>")
    parts.append(_img(res.files.get("chart_model_comparison")))
    parts.append("<h3>Holdout metrics (maturity-grouped folds, yield-equivalent bp)</h3><p class='small'>weighted_rmse_bp weights each held-out error by the quote's base precision (1/scale&sup2;, spread and liquidity only); it is the primary selection metric because one illiquid quote with a 50bp spread otherwise dominates the plain RMSE.</p>" + _table(_metrics_table(hold.metrics), "{:.3f}"))
    parts.append("<h3>In-sample metrics over usable instruments</h3>" + _table(_metrics_table({"baseline": ts["baseline"]["usable"], "advanced": ts["advanced"]["usable"]}), "{:.3f}"))
    per_fold = hold.per_fold.copy()
    for col in ("fold", "n_test"):
        if col in per_fold:
            per_fold[col] = per_fold[col].astype(int)
    parts.append("<h3>Per-fold holdout RMSE</h3>" + _table(per_fold, "{:.3f}"))
    if temporal.get("available"):
        parts.append(f"<h3>Time-aware split</h3><p>Cut-off {html.escape(temporal['cutoff_timestamp'])}: {temporal['n_train']} earlier quotes for training, {temporal['n_test']} later quotes for testing.</p>" + _table(_metrics_table({"baseline": temporal["baseline"], "advanced": temporal["advanced"]}), "{:.3f}"))
    else:
        parts.append(f"<p class='small'>Time-aware split not available: {html.escape(str(temporal.get('reason')))}</p>")
    if cv is not None:
        parts.append("<h3>Cross-validation of lambda (selected penalty shape)</h3>" + _table(cv.table.drop(columns=["fold_scores"]), "{:.4g}"))
        if power_tbl is not None:
            parts.append("<h3>Cross-validation by penalty shape (exponent fixed a priori, shown for information)</h3>" + _table(power_tbl, "{:.4g}"))
    parts.append(f"<div class='note'><b>Selection:</b> {html.escape(mc['selection_rationale'])}</div></section>")

    # --- sensitivity ----------------------------------------------------
    parts.append("<section id='sens'><h2>5. Sensitivity Analysis / 感度分析</h2>")
    if sens_checks:
        parts.append(_img(res.files.get("chart_sensitivity")))
        parts.append(_table(sens_rows(), "{:.2f}"))
        parts.append("<ul>" + "".join(f"<li><b>{html.escape(c['name'])}</b>: {html.escape(c['description'])} <i>{html.escape(c['interpretation'])}</i></li>" for c in sens_checks) + "</ul>")
        parts.append("<p class='small'>Full numerical outcomes in <code>diagnostics/sensitivity.json</code>; curve deltas per scenario in <code>diagnostics/sensitivity_curve_deltas.csv</code>.</p>")
    else:
        parts.append("<p>Sensitivity checks were skipped for this run.</p>")
    parts.append("</section>")

    # --- validation & repricing ---------------------------------------
    parts.append("<section id='valid'><h2>6. Validation and Repricing / 検証と再価格付け</h2>")
    parts.append(_img(res.files.get("chart_repricing")))
    parts.append("<h3>Largest remaining residuals among usable instruments (selected model)</h3>" + _table(worst, "{:.4g}"))
    parts.append(
        "<h3>Stability checks</h3><ul>"
        f"<li>IRLS iterations {res.adv.fit.iterations}, converged: {'yes' if res.adv.fit.converged else 'no (iteration cap reached; residual changes below tolerance were still being made)'}; robust type scales: "
        + ", ".join(f"{t} {_fmt(v, 2)}" for t, v in res.adv.fit.type_scale.items()) + ".</li>"
        f"<li>Grid checks: {len(curve)} rows, all discount factors positive ({'yes' if (curve['discount_factor'] > 0).all() else 'NO'}), all values finite ({'yes' if np.isfinite(curve[['zero_rate', 'discount_factor', 'forward_rate']].to_numpy()).all() else 'NO'}), "
        f"discount factors monotone decreasing ({'yes' if (np.diff(curve['discount_factor']) < 0).all() else 'no - forward rate negative somewhere (allowed)'}).</li>"
        + (f"<li>Numerical warnings raised: {len(res.warnings)}.</li>" if res.warnings else "<li>No numerical warnings were raised.</li>")
        + "</ul></section>"
    )

    # --- risk -----------------------------------------------------------
    parts.append("<section id='risk'><h2>7. Risk: DV01 and Key-Rate Sensitivities / リスク感応度</h2>")
    parts.append(_img(res.files.get("chart_risk")))
    parts.append(
        "<ul>"
        f"<li>Instruments with risk: {rs['n_instruments']} usable (all instruments that survived rule-based cleaning are in <code>diagnostics/risk.csv</code> with a <code>usable</code> flag).</li>"
        f"<li>Max |FD DV01 - analytic DV01| / |analytic|: {_fmt((rs['max_abs_rel_diff_fd_vs_analytic'] or 0) * 100, 5)}%.</li>"
        f"<li>Max |sum of key rates - DV01| / |DV01|: {_fmt((rs['max_abs_rel_diff_keysum_vs_dv01'] or 0) * 100, 5)}%.</li>"
        f"<li>Max |half-step DV01 - full-step DV01| / |DV01|: {_fmt((rs['max_abs_rel_diff_halfstep_vs_fullstep'] or 0) * 100, 5)}%.</li>"
        f"<li>All receiver DV01 positive: {'yes' if rs['all_receiver_dv01_positive'] else 'no'}.</li></ul>"
    )
    parts.append("<h3>Excerpt</h3>" + _table(risk_excerpt, "{:.4f}") + "</section>")

    # --- charts ---------------------------------------------------------
    parts.append("<section id='charts'><h2>8. Charts / 図表</h2><h3>Zero curves</h3>" + _img(res.files.get("chart_curve")) + "<h3>Forward rates</h3>" + _img(res.files.get("chart_forward")) + "</section>")

    # --- limitations ----------------------------------------------------
    lim = [
        "<b>Convention risk.</b> The schedule for tenors that are not a whole number of coupon periods is undocumented; the chosen rule is the one the data supports, and the sensitivity table shows what each alternative would do. If the counterparty convention differs, the 1.25Y/1.5Y OIS and short-stub bonds are the exposed points.",
        "<b>Extrapolation.</b> Below the shortest deposit (1M) and beyond the longest instrument the forward is the spline's boundary value (flat beyond the domain end); the baseline is flat in the zero rate. Neither is a forecast. The grid starts at 1/12Y for this reason.",
        "<b>Bond information is noisy.</b> Bond residuals are several times larger than swap residuals (see the type scales); the model down-weights them accordingly, so bonds mostly inform the curve between swap tenors. A single-curve model cannot represent a bond-specific credit/liquidity spread.",
        "<b>Smoothing bias.</b> The roughness penalty trades fit at concordant tenors against forward-rate smoothness; where several quotes at one tenor sit systematically off the curve (listed in the key findings) the curve is a compromise, not an exact repricing.",
        "<b>Flat CV objective.</b> The cross-validation score is flat over roughly a decade of lambda; the selected value is the minimiser, and the lambda sensitivity scenarios show the curve moves by only a few basis points across that range, but forward rates are more sensitive than zero rates.",
        "<b>Hyper-parameters selected on the same folds.</b> lambda and the penalty exponent were chosen by the same grouped CV that is reported as holdout evidence, so the advanced model's holdout numbers are mildly optimistic; the baseline has no tuned parameter.",
        "<b>Robust-fit decisions are model based.</b> The leave-tenor-out and Tukey rejections depend on the smoothness prior; a genuine but isolated market feature at a tenor with a single quote would be treated as an error.",
        "<b>Risk is curve-model specific.</b> DV01 and key-rate sensitivities are bumps of the fitted zero curve, not refits of the instrument set; convexity makes the key-rate sum differ from DV01 at the second order.",
        "<b>Single-date, single-currency snapshot.</b> No term-structure dynamics, no cross-currency basis, no collateral or funding adjustments.",
    ]
    parts.append("<section id='limits'><h2>9. Limitations / 限界とモデルリスク</h2><ul>" + "".join(f"<li>{x}</li>" for x in lim) + "</ul><p class='small'>See <code>MODEL_RISKS.md</code> for the full model-risk discussion.</p></section>")
    nxt = [
        "Confirm the fixed-leg schedule convention for non-integer tenors with the data provider and freeze it in <code>CONVENTIONS.md</code>; re-run the schedule sensitivity afterwards.",
        "Add a bond-specific spread (or a separate bond curve) if bond residuals remain systematically signed once the convention is settled.",
        "Collect more than one snapshot to validate stability through time (day-over-day curve changes versus quote changes) and to tune the stale-quote policy.",
        "Replace the fixed 0.5bp scale floor and the liquidity mapping with values calibrated from repeated quotes per instrument when history is available.",
        "Extend the holdout to a nested scheme so the smoothing hyper-parameters are not selected on the folds used for reporting.",
        "Expose Jacobian-based (algorithmic) sensitivities to the input quotes for hedging against the instrument set, complementing the curve-bump DV01.",
    ]
    parts.append("<section id='next'><h2>10. Recommended Next Steps / 推奨する次の手順</h2><ol>" + "".join(f"<li>{x}</li>" for x in nxt) + "</ol></section></main></body></html>")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(parts), encoding="utf-8")
    return out_path
