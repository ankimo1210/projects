"""Static chart and self-contained HTML report generation."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INK = "#17202A"
BLUE = "#1D5D8F"
GOLD = "#C58B22"
ORANGE = "#D96B27"
OLIVE = "#6B7D38"
GRID = "#D9E1E8"


def _style_axes(ax: Any) -> None:
    ax.set_facecolor("#FFFFFF")
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.75)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#AAB7C4")
    ax.spines["bottom"].set_color("#AAB7C4")
    ax.tick_params(colors="#4F5D6B")
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(9)


def make_charts(
    curve_grid: pd.DataFrame,
    repricing: pd.DataFrame,
    comparison: dict[str, Any],
    output_dir: str | Path,
) -> list[str]:
    """Write four evidence charts and return their relative filenames."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "normal"})
    files: list[str] = []

    fig, axes = plt.subplots(2, 1, figsize=(10, 7.4), sharex=True, constrained_layout=True)
    ax = axes[0]
    ax.plot(curve_grid["maturity_years"], curve_grid["zero_rate"] * 100, color=BLUE, linewidth=2.0)
    ax.axhline(0.0, color="#67727E", linewidth=0.8)
    ax.set_ylabel("Zero rate (%)")
    ax.set_title("Continuously compounded zero curve", loc="left", color=INK, fontsize=13)
    _style_axes(ax)
    ax = axes[1]
    ax.plot(curve_grid["maturity_years"], curve_grid["discount_factor"], color=OLIVE, linewidth=2.0)
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Discount factor")
    ax.set_ylim(bottom=0)
    _style_axes(ax)
    fig.savefig(target / "curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    files.append("curve.png")

    fig, ax = plt.subplots(figsize=(10, 4.7), constrained_layout=True)
    ax.plot(curve_grid["maturity_years"], curve_grid["forward_rate"] * 100, color=GOLD, linewidth=2.0)
    ax.axhline(0.0, color="#67727E", linewidth=0.8)
    ax.set_title("Instantaneous continuously compounded forward rate", loc="left", color=INK, fontsize=13)
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Forward rate (%)")
    _style_axes(ax)
    fig.savefig(target / "forward_rate.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    files.append("forward_rate.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1.2, 1]}, constrained_layout=True)
    ax = axes[0]
    palette = {"deposit": BLUE, "ois_swap": ORANGE, "bond": OLIVE}
    for typ, group in repricing.groupby("instrument_type", sort=True):
        ax.scatter(group["market_quote"], group["model_quote"], s=22, alpha=0.72, label=typ, color=palette.get(typ, BLUE), edgecolors="white", linewidths=0.3)
    if not repricing.empty:
        lo = float(min(repricing["market_quote"].min(), repricing["model_quote"].min()))
        hi = float(max(repricing["market_quote"].max(), repricing["model_quote"].max()))
        pad = 0.03 * max(hi - lo, 1.0)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="#67727E", linestyle="--", linewidth=1, label="45°")
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(lo - pad, hi + pad)
    ax.set_title("Market versus model quote", loc="left", color=INK, fontsize=13)
    ax.set_xlabel("Market quote (normalized units)")
    ax.set_ylabel("Model quote (normalized units)")
    ax.legend(frameon=False, fontsize=8)
    _style_axes(ax)
    ax = axes[1]
    if not repricing.empty:
        for typ, group in repricing.groupby("instrument_type", sort=True):
            ax.scatter(group["maturity_years"], group["standardized_residual"], s=22, alpha=0.72, label=typ, color=palette.get(typ, BLUE), edgecolors="white", linewidths=0.3)
    ax.axhline(0.0, color="#67727E", linewidth=0.8)
    ax.set_title("Residual by maturity", loc="left", color=INK, fontsize=13)
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Standardized residual")
    _style_axes(ax)
    fig.savefig(target / "repricing.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    files.append("repricing.png")

    labels = ["Baseline\ntrain", "Advanced\ntrain", "Baseline\nholdout", "Advanced\nholdout"]
    values = [
        comparison["baseline"]["train"].get("weighted_standardized_rmse"),
        comparison["advanced"]["train"].get("weighted_standardized_rmse"),
        comparison["baseline"]["holdout"].get("weighted_standardized_rmse"),
        comparison["advanced"]["holdout"].get("weighted_standardized_rmse"),
    ]
    values = [float(v) if v is not None and np.isfinite(v) else np.nan for v in values]
    colors = [BLUE, ORANGE, BLUE, ORANGE]
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
    x = np.arange(len(labels))
    bars = ax.bar(x, np.nan_to_num(values, nan=0.0), color=colors, width=0.62)
    for bar, value in zip(bars, values):
        if np.isfinite(value):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}", ha="center", va="bottom", fontsize=9, color=INK)
        else:
            ax.text(bar.get_x() + bar.get_width() / 2, 0, "n/a", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Weighted standardized RMSE (lower is better)")
    ax.set_title("Baseline versus advanced validation error", loc="left", color=INK, fontsize=13)
    _style_axes(ax)
    fig.savefig(target / "model_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    files.append("model_comparison.png")
    return files


def _img_data(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if not np.isfinite(number):
        return "n/a"
    return f"{number:.{digits}f}"


def _table(headers: list[str], rows: list[list[Any]], cls: str = "") -> str:
    head = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = "".join("<tr>" + "".join(f"<td>{value if isinstance(value, str) and value.startswith('<') else html.escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write_report(
    report_path: str | Path,
    chart_dir: str | Path,
    quality: dict[str, Any],
    comparison: dict[str, Any],
    holdout_definition: dict[str, Any],
    sensitivity: dict[str, Any],
    selected_model: str,
    repricing: pd.DataFrame,
    risk: pd.DataFrame,
    curve_grid: pd.DataFrame,
) -> None:
    """Write a single-file technical report with charts embedded as data URIs."""
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    charts = Path(chart_dir)
    action_counts = quality.get("actions", {})
    selected_holdout = comparison[selected_model]["holdout"]
    baseline_holdout = comparison["baseline"]["holdout"]
    improvement = None
    if baseline_holdout.get("weighted_standardized_rmse") and selected_holdout.get("weighted_standardized_rmse"):
        improvement = 1.0 - selected_holdout["weighted_standardized_rmse"] / baseline_holdout["weighted_standardized_rmse"]
    type_rows = []
    for typ in ("deposit", "ois_swap", "bond"):
        group = repricing.loc[repricing["instrument_type"] == typ]
        if group.empty:
            continue
        type_rows.append([typ, len(group), _fmt(np.sqrt(np.mean(group["residual"] ** 2)), 6), _fmt(np.mean(np.abs(group["residual"])), 6)])
    segment_rows = []
    segment_metrics = comparison.get("segment_metrics", {})
    for segment in sorted(set(segment_metrics.get("baseline", {}).get("holdout", {})) | set(segment_metrics.get("advanced", {}).get("holdout", {}))):
        before = segment_metrics.get("baseline", {}).get("holdout", {}).get(segment, {})
        after = segment_metrics.get("advanced", {}).get("holdout", {}).get(segment, {})
        segment_rows.append([
            segment,
            before.get("n", 0),
            _fmt(before.get("weighted_standardized_rmse"), 3),
            after.get("n", 0),
            _fmt(after.get("weighted_standardized_rmse"), 3),
        ])
    sens_rows = []
    for name, result in sensitivity.items():
        sens_rows.append([name, _fmt(result.get("max_abs_zero_shift_bp"), 3), _fmt(result.get("zero_30y_shift_bp"), 3), html.escape(str(result.get("interpretation", "")))])
    risk_rows = []
    if not risk.empty:
        for _, row in risk.sort_values("dv01", ascending=False).head(8).iterrows():
            risk_rows.append([row["instrument_id"], _fmt(row["dv01"], 4), _fmt(row["key_2y"], 4), _fmt(row["key_5y"], 4), _fmt(row["key_10y"], 4), _fmt(row["key_30y"], 4)])
    img_curve = _img_data(charts / "curve.png")
    img_forward = _img_data(charts / "forward_rate.png")
    img_repricing = _img_data(charts / "repricing.png")
    img_comparison = _img_data(charts / "model_comparison.png")
    max_fd_error = float(risk["dv01_fd_relative_error"].max()) if not risk.empty else np.nan
    max_key_error = float(risk["key_sum_relative_error"].max()) if not risk.empty else np.nan
    zero_min = float(curve_grid["zero_rate"].min() * 100)
    zero_max = float(curve_grid["zero_rate"].max() * 100)
    forward_min = float(curve_grid["forward_rate"].min() * 100)
    forward_max = float(curve_grid["forward_rate"].max() * 100)
    report_title = "USD Zero-Curve Research — 15 January 2026"
    html_text = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="color-scheme" content="light dark"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{report_title}</title>
<style>
:root {{ color-scheme: light dark; --bg:#f7f9fb; --card:#fff; --ink:#17202a; --muted:#5b6875; --line:#d9e1e8; --accent:#1d5d8f; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#111820; --card:#18232e; --ink:#edf2f7; --muted:#b6c2cf; --line:#344453; --accent:#6fb5e8; }} }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }} main {{ max-width:1120px; margin:0 auto; padding:36px 24px 72px; }} h1 {{ font-size:clamp(28px,4vw,44px); line-height:1.12; margin:0 0 8px; letter-spacing:-.03em; }} h2 {{ margin:38px 0 10px; font-size:24px; letter-spacing:-.02em; }} h3 {{ margin:22px 0 8px; font-size:17px; }} p {{ max-width:900px; }} .eyebrow {{ color:var(--accent); font-weight:700; letter-spacing:.08em; text-transform:uppercase; font-size:12px; }} .summary {{ background:var(--card); border:1px solid var(--line); border-left:5px solid var(--accent); padding:18px 22px; border-radius:10px; margin:20px 0 26px; }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }} .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }} .metric {{ font-size:25px; font-weight:700; margin-top:3px; }} .muted {{ color:var(--muted); }} figure {{ margin:18px 0 8px; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }} figure img {{ display:block; width:100%; height:auto; }} figcaption {{ color:var(--muted); font-size:13px; padding:9px 4px 0; }} .table-wrap {{ overflow-x:auto; margin:12px 0 18px; }} table {{ border-collapse:collapse; width:100%; min-width:560px; background:var(--card); border:1px solid var(--line); }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; }} th {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }} code {{ background:rgba(128,145,160,.14); border-radius:4px; padding:2px 5px; }} .note {{ color:var(--muted); font-size:13px; }} ul {{ max-width:900px; }} .footer {{ margin-top:44px; color:var(--muted); border-top:1px solid var(--line); padding-top:14px; font-size:12px; }}
</style></head><body><main>
<div class="eyebrow">Technical research report · USD · ACT/365F</div><h1>{report_title}</h1>
<section class="summary"><h2 style="margin-top:0">Executive Summary（エグゼクティブ要約） / Technical Summary（技術要約）</h2>
<p><strong>Preferred estimator: {html.escape(selected_model)}.</strong> It is selected using a whole-maturity visible holdout rather than a random row split. The selected model has weighted standardized holdout RMSE <strong>{_fmt(selected_holdout.get("weighted_standardized_rmse"),3)}</strong> versus <strong>{_fmt(baseline_holdout.get("weighted_standardized_rmse"),3)}</strong> for the baseline{f", an improvement of {improvement:.1%}" if improvement is not None else ""}.</p>
<p>The curve is positive-discount-factor by construction, supports negative zero and forward rates, and reprices {len(repricing)} usable observations across deposits, OIS swaps, and bonds. The visible data contain intentional defects; deterministic unit/midpoint/bid-ask repairs are audited, while gross same-maturity outliers are excluded.</p>
<p><strong>Use implication:</strong> the fit is suitable for research diagnostics and scenario risk on this synthetic snapshot, but the long end remains sensitive to sparse, low-liquidity bond quotes and extrapolation assumptions.</p>
</section>
<div class="grid"><div class="card"><div class="muted">Usable observations</div><div class="metric">{quality.get("usable_rows", "n/a")}</div><div class="muted">of {quality.get("input_rows", "n/a")} input rows</div></div><div class="card"><div class="muted">Holdout clusters</div><div class="metric">{holdout_definition.get("holdout_instruments", "n/a")}</div><div class="muted">whole maturity clusters</div></div><div class="card"><div class="muted">Zero-rate range</div><div class="metric">{zero_min:.2f}% to {zero_max:.2f}%</div><div class="muted">1M–30Y grid</div></div><div class="card"><div class="muted">Risk FD check</div><div class="metric">{max_fd_error:.2e}</div><div class="muted">max relative error</div></div></div>

<h2>Key Findings（主な発見）</h2>
<p><strong>The preferred curve is smooth enough to interpolate through the sparse tenor structure while preserving instrument-level evidence.</strong> The lower panel shows discount factors remain strictly positive; the forward curve is derived from <code>−d log(D)/dT</code> analytically within each piecewise-linear zero-rate segment, not fitted as a separate object. Negative values would be permitted by the parameterization even though this snapshot's central curve is positive.</p>
<h2>Charts（チャート）</h2>
<p>The charts below show the fitted zero curve, positive discount factors, analytical instantaneous forwards, model-versus-market repricing, and the visible baseline/advanced comparison. Percentages are chart display units; machine-readable files retain the documented decimal or price-point units.</p>
<figure><img src="{img_curve}" alt="Zero rates and discount factors from one month to 30 years"><figcaption>Zero rates are continuously compounded annual decimals in the machine-readable curve file; the chart displays percentages. Discount factors use exp(−zT).</figcaption></figure>
<p><strong>The forward curve is an implied local rate, so it is more sensitive to knot curvature than the zero curve.</strong> This is the main reason to inspect forward-rate spikes before using the long end for pricing or hedging.</p>
<figure><img src="{img_forward}" alt="Instantaneous continuously compounded forward rate"><figcaption>Instantaneous forward rate on the dense output grid. Within each segment it uses the analytical derivative of the piecewise-linear zero curve; at interior knots it uses the deterministic midpoint of the left/right derivative.</figcaption></figure>

<h2>Scope, Data, and Metric Definitions（対象・データ・指標定義）</h2>
<p>The source is the supplied <code>market_data/market_observations.csv</code>, valued on 15 January 2026 in USD with a two-calendar-day settlement lag. Input rates are percentage points and are normalized to annual decimals for fitting; bond coupons are decimals and clean prices are points per 100 face value.</p>
<p>Deposits use <code>D(T)=1/(1+rT)</code>. OIS swaps use annual fixed payments through 2Y and semiannual payments thereafter, with <code>r Σ αᵢD(tᵢ)=1−D(T)</code>. Bonds use level coupons at the documented payment frequency plus principal at maturity. The reported risk is receiver-fixed PV sensitivity to a central ±1bp parallel zero-rate bump; 2Y/5Y/10Y/30Y key rates use partition-of-unity triangular local bump shapes.</p>

<h2>Data Quality（データ品質と監査処理）</h2>
<p><strong>Data cleaning is observable rather than silent.</strong> Every input row appears in <code>diagnostics/cleaning.csv</code>. The action counts are keep={action_counts.get("keep",0)}, correct={action_counts.get("correct",0)}, downweight={action_counts.get("downweight",0)}, and exclude={action_counts.get("exclude",0)}. Corrections cover decimal-fraction scale errors, missing quote midpoint recovery from a valid bid/ask, and crossed bid/ask reordering. Duplicates retain the highest-priority fresh non-backup observation. Stale and low-liquidity rows remain usable but receive lower weights. Same-maturity rate prints that are grossly inconsistent with at least two peers are excluded because there is no defensible deterministic correction.</p>
{_table(["Check","Count"], [["Input rows", quality.get("input_rows",0)], ["Missing quote values", quality.get("missing_quote_values",0)], ["Crossed bid/ask", quality.get("crossed_bid_ask",0)], ["Duplicate instrument rows", quality.get("duplicate_instrument_ids",0)], ["Unit corrections", quality.get("unit_corrections",0)], ["Peer outlier exclusions", quality.get("peer_outlier_exclusions",0)], ["Stale rows", quality.get("stale_rows",0)], ["Low-liquidity rows", quality.get("low_liquidity_rows",0)]], "audit")}

<h2>Methodology（方法論：基準モデルとロバスト正則化）</h2>
<p><strong>Baseline:</strong> weighted-median deposits and OIS swaps are bootstrapped in increasing maturity order. Missing intermediate cash-flow dates are evaluated by log-linear interpolation of discount factors; the resulting zero rates are linearly interpolated and held flat in zero-rate terms beyond the last anchor.</p>
<p><strong>Advanced:</strong> all usable deposits, OIS swaps, and bonds are fitted simultaneously with piecewise-linear continuous zero rates on a fixed 1M–30Y knot grid. The objective is quote residual divided by a conservative bid/ask uncertainty scale, weighted by liquidity and spread; a curvature penalty regularizes the zero-rate slope. Four deterministic iterations update Huber-like robust residual weights. Parameter bounds are wide enough for negative rates, while <code>D(T)=exp(−z(T)T)</code> guarantees positive discount factors. Instantaneous forwards are then constructed analytically from the fitted zero segments.</p>
<p>The holdout is maturity-aware: entire clusters nearest 2Y, 5Y, 10Y, 20Y, and 30Y are excluded from fitting, so multiple quotes sharing a maturity cannot leak between train and validation. {html.escape(str(holdout_definition.get("method", "")))}.</p>

<h2>Model Comparison（基準モデルと高度モデルの比較）</h2>
<p><strong>The selected model is determined by visible holdout evidence.</strong> Lower standardized error means the model is closer relative to the observed bid/ask uncertainty and the conservative type-specific floor. The adoption gate is fixed at advanced holdout RMSE ≤ baseline holdout RMSE × 1.05; it was not widened after seeing this round's results.</p>
{_table(["Model","Train n","Train std RMSE","Holdout n","Holdout std RMSE","Raw RMSE by type"], [[name, comparison[name]["train"].get("n",0), _fmt(comparison[name]["train"].get("weighted_standardized_rmse"),3), comparison[name]["holdout"].get("n",0), _fmt(comparison[name]["holdout"].get("weighted_standardized_rmse"),3), "; ".join(f"{k}: {_fmt(v,6)}" for k,v in comparison[name]["holdout"].get("raw_rmse",{}).items())] for name in ("baseline","advanced")], "comparison")}
<figure><img src="{img_comparison}" alt="Baseline and advanced train and holdout standardized RMSE"><figcaption>Weighted standardized quote residuals; the holdout consists of whole maturity clusters and is not a random observation split.</figcaption></figure>
<p>Segment checks are reported separately so an overall average cannot conceal a product or tenor deterioration. The table uses the same bid/ask-and-floor standardized RMSE as the overall holdout score; cells with too few observations are kept as `n/a` rather than inferred.</p>
{_table(["Segment","Baseline n","Baseline std RMSE","Advanced n","Advanced std RMSE"], segment_rows, "segments")}

<h2>Validation and Repricing（検証・再価格付け・安定性）</h2>
<p><strong>Repricing diagnostics stay in normalized market units and are available per instrument.</strong> The scatter and residual panels below make both cross-sectional fit and maturity-local issues visible. Price residuals for bonds are points; rate residuals for deposits and swaps are annual decimals.</p>
<figure><img src="{img_repricing}" alt="Market versus model quote and standardized residual by maturity"><figcaption>Left: market versus model quotes, colored by instrument type. Right: residual divided by its conservative bid/ask uncertainty scale, so rate and price instruments are comparable. See <code>diagnostics/repricing.csv</code> for exact rows.</figcaption></figure>
{_table(["Type","Usable n","RMSE","MAE"], type_rows, "repricing")}
<p>Finite-difference risk verification has maximum relative error <code>{max_fd_error:.2e}</code>. The four key-rate sensitivities sum to parallel DV01 with maximum relative error <code>{max_key_error:.2e}</code> because their bump basis forms a partition of unity over the curve domain. A sample of the largest receiver-fixed DV01 instruments follows; the full result is in <code>diagnostics/risk.csv</code>.</p>
{_table(["Instrument","DV01","Key 2Y","Key 5Y","Key 10Y","Key 30Y"], risk_rows, "risk")}

<h2>Sensitivity Analysis（感度分析）</h2>
<p><strong>The long end is the least certain part of the result.</strong> The following refits perturb observable inputs or the regularization choice. Values are maximum absolute changes in the dense-grid zero rate in basis points versus the selected fit.</p>
{_table(["Scenario","Max zero shift (bp)","30Y zero shift (bp)","Interpretation"], sens_rows, "sensitivity")}

<h2>Limitations（限界・不確実性・モデルリスク）</h2>
<ul><li>The sample is a synthetic single-date snapshot with no independent historical window; stability is tested by visible refits, not by time-series backtesting.</li><li>Bond cash-flow stubs follow the supplied year-fraction and level-coupon conventions; actual-market accrued interest, business-day adjustment, collateral, and payment-date calendars are outside scope.</li><li>The long end has sparse and low-liquidity observations. Constant-zero extrapolation beyond the last fitted knot is deterministic, not an economic forecast.</li><li>Piecewise-linear zero segments imply structural forward-rate jumps at knots; analytical construction removes grid finite-difference noise but does not make the forward economically smooth.</li><li>Robust weights reduce sensitivity to bad prints but can hide a genuine regime break if used without dealer or curve governance review.</li><li>Risk is local to the selected curve and quote set. It is not a full re-hedging or stochastic P&amp;L distribution.</li></ul>

<h2>Recommended Next Steps（推奨する次の手順）</h2>
<ul><li>Replace the synthetic visible holdout with a rolling date-aware history and monitor repricing residuals by venue and instrument type.</li><li>Set governance thresholds for excluded outliers, stale data, and quote-width inflation before production use.</li><li>Compare this regularized estimator with a monotone-forward or spline-in-forward implementation and require out-of-sample stability at key-rate tenors.</li><li>For trading use, validate collateral, calendar, settlement, day-count, accrued-interest, and instrument-specific risk conventions against the authoritative source system.</li></ul>

<h2>Further Questions（未解決の問い）</h2>
<p>How much of the long-end shape is driven by bonds versus OIS? Does a rolling window preserve the same robust exclusions? Are key-rate buckets better defined using market-standard interpolation nodes than the requested partition-of-unity basis? These questions should be answered before treating the curve as a production market-data service.</p>
<div class="footer">Generated deterministically from the supplied benchmark input. Machine-readable outputs: <code>curves/curve.csv</code>, <code>diagnostics/cleaning.csv</code>, <code>diagnostics/repricing.csv</code>, <code>diagnostics/risk.csv</code>, <code>diagnostics/segment_metrics.csv</code>, <code>diagnostics/model_comparison.json</code>, and <code>diagnostics/sensitivity.json</code>.</div>
</main></body></html>"""
    path.write_text(html_text, encoding="utf-8")
