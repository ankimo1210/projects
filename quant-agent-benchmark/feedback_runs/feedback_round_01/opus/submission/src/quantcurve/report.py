"""Self-contained HTML research report.

Charts are embedded as base64 data URIs so the file can be opened from disk,
e-mailed or archived without any accompanying assets and without network access.
"""

from __future__ import annotations

import base64
import html
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .workflow import WorkflowResult

__all__ = ["render_report", "write_report"]


_CSS = """
:root{
  --ink:#161a20; --body:#333a45; --muted:#69707d; --line:#e3e7ee; --rule:#cfd6e0;
  --bg:#ffffff; --panel:#f7f9fc; --accent:#1f4e79; --accent-2:#c2622d;
  --good:#2f6f4f; --bad:#a02c2c;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--body);font:15px/1.65 var(--sans);
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px 96px}
header.masthead{border-bottom:2px solid var(--ink);margin-bottom:36px;padding:44px 0 20px}
h1{font-size:30px;line-height:1.2;margin:0 0 8px;color:var(--ink);letter-spacing:-.015em}
.sub{color:var(--muted);font-size:14px;margin:0}
h2{font-size:20px;color:var(--ink);margin:44px 0 4px;letter-spacing:-.01em;
  padding-top:18px;border-top:1px solid var(--line)}
h3{font-size:15px;color:var(--ink);margin:26px 0 6px;letter-spacing:.02em;
  text-transform:uppercase;font-weight:600}
p{margin:10px 0}
ul,ol{margin:10px 0;padding-left:22px}
li{margin:5px 0}
code,.mono{font-family:var(--mono);font-size:.9em}
.lede{font-size:17px;color:var(--ink)}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  margin:20px 0}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.tile .k{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
.tile .v{font-size:22px;color:var(--ink);font-family:var(--mono);margin-top:4px;
  letter-spacing:-.02em}
.jp{font-weight:500;font-size:.72em;color:var(--muted);margin-left:.5em;letter-spacing:.02em}
.tile .n{font-size:12px;color:var(--muted);margin-top:3px;overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13.5px}
.scroll{overflow-x:auto}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);
  white-space:nowrap}
th:first-child,td:first-child{text-align:left}
/* A long free-text column (the cleaning reason) must wrap in place rather than
   push itself off the right edge of the horizontal scroller, where nobody
   reads it. */
th.text,td.text{white-space:normal;text-align:left;min-width:260px}
thead th{color:var(--muted);font-weight:600;font-size:11.5px;letter-spacing:.05em;
  text-transform:uppercase;border-bottom:1px solid var(--rule)}
tbody tr:hover{background:var(--panel)}
td.num{font-family:var(--mono)}
figure{margin:22px 0}
figure img{width:100%;height:auto;border:1px solid var(--line);border-radius:8px;
  display:block;background:#fff}
figcaption{color:var(--muted);font-size:12.5px;margin-top:7px}
.note{border-left:3px solid var(--accent);background:var(--panel);padding:12px 16px;
  margin:18px 0;border-radius:0 6px 6px 0}
.warn{border-left-color:var(--accent-2)}
.pill{display:inline-block;font-family:var(--mono);font-size:11px;padding:2px 8px;
  border-radius:999px;border:1px solid var(--rule);color:var(--muted)}
.pill.on{background:#e8f0e9;border-color:#bcd6c3;color:var(--good)}
.pill.off{background:#f6e7e7;border-color:#e0bebe;color:var(--bad)}
.toc{columns:2;column-gap:32px;font-size:14px;margin:14px 0 0}
footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--muted);font-size:12.5px}
@media (max-width:640px){.toc{columns:1}h1{font-size:24px}}
"""


def _fmt(value, digits: int = 4, dash: str = "n/a") -> str:
    if value is None:
        return dash
    try:
        number = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if not np.isfinite(number):
        return dash
    return f"{number:,.{digits}f}"


def _tile(key: str, value: str, note: str = "") -> str:
    note_html = f'<div class="n">{html.escape(note)}</div>' if note else ""
    return (
        f'<div class="tile"><div class="k">{html.escape(key)}</div>'
        f'<div class="v">{value}</div>{note_html}</div>'
    )


#: Columns rendered as wrapping free text rather than a single nowrap line.
TEXT_COLUMNS = frozenset({"reason", "description", "rationale", "note", "notes"})


def _table(frame: pd.DataFrame, digits: dict[str, int] | None = None) -> str:
    digits = digits or {}
    head = "".join(
        f'<th{" class=\"text\"" if c in TEXT_COLUMNS else ""}>{html.escape(str(c))}</th>'
        for c in frame.columns
    )
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in frame.columns:
            value = row[column]
            if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(
                value, bool
            ):
                cells.append(f'<td class="num">{_fmt(value, digits.get(column, 4))}</td>')
            elif column in TEXT_COLUMNS:
                cells.append(f'<td class="text">{html.escape(str(value))}</td>')
            else:
                cells.append(f"<td>{html.escape(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="scroll"><table><thead><tr>'
        + head
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _figure(charts: dict[str, bytes], name: str, caption: str) -> str:
    if name not in charts:
        return ""
    encoded = base64.b64encode(charts[name]).decode("ascii")
    return (
        f'<figure><img alt="{html.escape(caption)}" '
        f'src="data:image/png;base64,{encoded}">'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def _metric_table(payload: dict) -> pd.DataFrame:
    rows = []
    for model in ("baseline", "advanced"):
        block = payload[model]
        for sample, key in (
            ("train", "train_metrics"),
            ("holdout", "holdout_metrics"),
            ("full sample", "full_sample_metrics"),
        ):
            metrics = block.get(key) or {}
            if not metrics:
                continue
            rows.append(
                {
                    "model": model,
                    "sample": sample,
                    "n": metrics.get("n_instruments", np.nan),
                    "weighted RMSE (bp)": metrics.get("weighted_rmse_bp", np.nan),
                    "RMSE (bp)": metrics.get("rmse_bp", np.nan),
                    "MAE (bp)": metrics.get("mae_bp", np.nan),
                    "median |r| (bp)": metrics.get("median_abs_bp", np.nan),
                    "max |r| (bp)": metrics.get("max_abs_bp", np.nan),
                }
            )
    return pd.DataFrame(rows)


def _residual_summary(result: WorkflowResult) -> pd.DataFrame:
    frame = result.repricing
    rows = []
    for kind in ("deposit", "ois_swap", "bond"):
        subset = frame[frame["instrument_type"] == kind]
        if subset.empty:
            continue
        weights = subset["weight"].to_numpy()
        residual = subset["residual_bp"].to_numpy()
        rows.append(
            {
                "instrument type": kind,
                "n": len(subset),
                "median weight": float(np.median(weights)),
                "weighted RMSE (bp)": float(
                    np.sqrt(np.sum(weights * residual**2) / np.sum(weights))
                )
                if weights.sum() > 0
                else float("nan"),
                "median |r| (bp)": float(np.median(np.abs(residual))),
                "max |r| (bp)": float(np.max(np.abs(residual))),
                "estimated model error (bp)": result.model_error_bp.get(kind, float("nan")),
            }
        )
    return pd.DataFrame(rows)


def render_report(
    result: WorkflowResult, charts: dict[str, bytes], compact: bool = False
) -> str:
    payload = result.model_comparison
    selected = payload["model_selected"]
    selected_block = payload[selected]
    other = "baseline" if selected == "advanced" else "advanced"
    audit = result.cleaning.audit
    grid = result.grid
    curve = result.curve_table
    # Provenance is stamped with the *market snapshot* time, not the wall clock:
    # the CLI is required to be deterministic, and "when this file happened to be
    # regenerated" is both non-reproducible and less informative than "which
    # market this curve was built from". The file's mtime still records the run.
    generated = result.market_snapshot or "unknown"

    tenors = [0.25, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
    zero = [float(result.curve.zero(np.array([t]))[0]) * 100 for t in tenors]
    forward = [float(result.curve.forward(np.array([t]))[0]) * 100 for t in tenors]
    discount = [float(result.curve.discount(np.array([t]))[0]) for t in tenors]
    curve_table = pd.DataFrame(
        {
            "tenor (Y)": tenors,
            "zero rate (%)": zero,
            "instantaneous forward (%)": forward,
            "discount factor": discount,
        }
    )

    holdout = payload["holdout"]
    admissible = payload[selected]["forward_admissibility"]
    other_adm = payload[other]["forward_admissibility"]
    sens = result.sensitivity.get("checks", [])
    risk = result.risk
    worst_key = float(np.max(np.abs(risk["key_sum_relative_error"]))) if len(risk) else 0.0
    worst_dv01 = (
        float(np.max(np.abs(risk["dv01_analytic_relative_error"]))) if len(risk) else 0.0
    )

    excluded = audit[audit["action"] == "exclude"]
    corrected = audit[audit["action"] == "correct"]
    downweighted = audit[audit["action"] == "downweight"]

    summary_tiles = "".join(
        [
            _tile("Observations", f"{len(audit)}", "rows in the input file"),
            _tile(
                "Calibrating instruments",
                f"{len(result.instruments)}",
                f"{len(excluded)} excluded, {len(corrected)} corrected",
            ),
            _tile(
                "Published model",
                html.escape(selected),
                html.escape(selected_block["name"].replace("_", " ")),
            ),
            _tile(
                "Holdout weighted RMSE",
                _fmt(
                    (payload[selected].get("holdout_metrics") or {}).get(
                        "weighted_rmse_bp"
                    ),
                    2,
                )
                + " bp",
                f"{holdout['n_holdout']} instruments withheld",
            ),
            _tile("Zero rate 10Y", _fmt(zero[4], 3) + " %", "continuously compounded"),
            _tile("Zero rate 30Y", _fmt(zero[6], 3) + " %", "continuously compounded"),
        ]
    )

    residual_summary = _residual_summary(result)
    residual_line = ", ".join(
        f"{row['weighted RMSE (bp)']:.2f}bp for the "
        f"{row['instrument type'].replace('ois_swap', 'OIS swap')}s "
        f"(n={int(row['n'])})"
        for _, row in residual_summary.iterrows()
    ) or "not available"

    sections: list[str] = []

    sections.append(
        f"""
<h2 id="summary">1. Executive Summary <span class="jp">エグゼクティブサマリー</span></h2>
<p class="lede">A continuously compounded zero curve was estimated from
{len(audit)} quotes on {audit['instrument_id'].nunique()} instruments &mdash; deposits,
par OIS swaps and coupon bonds &mdash; as of {result.valuation_date.date().isoformat()}.
The published curve is the <strong>{html.escape(selected)}</strong> estimator
({html.escape(selected_block['name'])}).</p>
<div class="grid">{summary_tiles}</div>
<p><strong>Why this model.</strong> {html.escape(payload['selection_rationale'])}</p>
<p><strong>What the data required.</strong> {len(corrected)} observations were
repaired (unit rescaling, quotes reconstructed from the two-way market, crossed
markets un-crossed), {len(downweighted)} were downweighted for width or
illiquidity and {len(excluded)} were excluded (stale snapshots, superseded
duplicates and gross outliers). Every decision is recorded row by row in
<code>diagnostics/cleaning.csv</code>.</p>
<p><strong>How much to trust it.</strong> Weighted repricing RMSE, in
yield-equivalent basis points, is {residual_line}; the bond figure is the same
size as the bonds' own measured idiosyncratic spread and is a property of the
instruments rather than an error in the curve. Discount factors are strictly
positive across the whole grid.
The sensitivity suite below shows the largest control-driven shift is
{_fmt(max((c['value'] for c in sens if np.isfinite(c['value'])), default=float('nan')), 2)} bp;
the difference between the two candidate estimators reaches
{_fmt(next((c['value'] for c in sens if c['name'] == 'model_choice_dispersion'), float('nan')), 2)} bp,
which is the honest width of the modelling choice.</p>
"""
    )

    sections.append(
        f"""
<h2 id="method">2. Methodology <span class="jp">手法</span></h2>
<h3>Conventions</h3>
<p>Every convention stated in the supplied <code>CONVENTIONS.md</code> is
followed exactly, and nothing beyond it is assumed. Zero rates are continuously
compounded with
<code>D(T)=exp(-zT)</code>; deposits use simple interest
<code>D(T)=1/(1+rT)</code>; OIS fixed legs pay annually through 2Y and
semiannually thereafter with accrual <code>1/frequency</code>; bonds pay level
coupons at <code>1/frequency</code> intervals on face 100 with no accrued
interest. The document is silent on one point that matters: how many periods a
non-integer maturity has. Schedules are generated backwards from maturity using
<code>n = round(T x frequency)</code>, and that rule was <em>inferred from the
quotes</em> rather than assumed &mdash; it is the only one that simultaneously
reproduces the 1.25Y annual-pay OIS quote (one period) and the 2.44Y semiannual
bond quote (five periods).
<code>ceil</code> misprices the first by roughly 50 bp and <code>floor</code>
misprices the second by roughly 60 bp.</p>

<h3>Curve representation</h3>
<p>Both estimators are defined through the <em>instantaneous forward rate</em>
and discount factors follow as <code>D(T)=exp(-&#8747;f)</code>. That construction
makes negative zero and forward rates perfectly representable while discount
factors remain strictly positive by construction &mdash; the requirement is satisfied
structurally rather than by clipping. Outside the calibrated maturity range the
forward is held flat, which is the standard extrapolation and the only one that
adds no unsupported curvature.</p>

<h3>Baseline: {html.escape(payload['baseline']['name'])}</h3>
<p>{html.escape(payload['baseline']['description'])}. Economically identical
quotes are averaged into one consensus pillar with the calibration weights;
pillars closer than 0.10Y are merged because an exact bootstrap cannot support
two nearly coincident maturities. {payload['baseline']['n_pillars']} pillars were
used.</p>

<h3>Advanced: {html.escape(payload['advanced']['name'])}</h3>
<p>{html.escape(payload['advanced']['description'])}. The objective is a
weighted sum of squared yield-equivalent repricing residuals plus
<code>&#955;&#8747;(T/1Y)<sup>p</sup> f''(T)<sup>2</sup> dT</code>. The
maturity-dependent factor matters: an unweighted roughness penalty
over-penalises the money-market end, where curvature naturally scales like
1/T<sup>2</sup> and where the data are densest. Both <code>&#955;</code> and
<code>p</code> are selected by maturity-blocked cross-validation on the training
sample only, so the holdout number reported below stays honest. The selected
values are <code>&#955;={payload['advanced']['smoothing_lambda']:g}</code> and
<code>p={payload['advanced']['penalty_maturity_power']:g}</code> on
{payload['advanced']['n_knots']} knots placed at the benchmark rate maturities.</p>

<h3>Weights and robustness</h3>
<p>Each quote carries an uncertainty
<code>&#963;<sub>i</sub><sup>2</sup> = &#963;<sub>quote,i</sub><sup>2</sup> +
&#963;<sub>model,type</sub><sup>2</sup></code>. The first term is the half
bid/ask width converted to yield-equivalent basis points and inflated by
illiquidity; the second is estimated from the residual dispersion of a
preliminary robust fit, separately per instrument type. That second term is what
keeps coupon bonds in their place: their two-way markets are tight, but no single
OIS-consistent discount curve can absorb their idiosyncratic spreads, and the
estimated model error
({", ".join(f"{k}: {v:.2f} bp" for k, v in sorted(result.model_error_bp.items()))})
says so quantitatively. Data-quality penalties multiply the weight for repaired,
crossed, wide or illiquid quotes. Robustness is then iterative: a convex Huber
warm-up (which cannot settle on the wrong cluster of quotes) followed by Tukey
biweight reweighting with a frozen robust scale.</p>
"""
    )

    dq_rows = pd.DataFrame(
        [
            {"finding": k.replace("_", " "), "observations": v}
            for k, v in sorted(result.validation_summary.items(), key=lambda kv: -kv[1])
            if v > 0
        ]
    )
    example_rows = audit[audit["action"] != "keep"].copy()
    example_rows = example_rows.sort_values(
        ["action", "obs_id"], kind="stable"
    ).loc[:, ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]]
    shown = example_rows if compact is False else example_rows.head(20)

    sections.append(
        f"""
<h2 id="data">3. Data Quality <span class="jp">データ品質</span></h2>
<p>The file is realistic and imperfect. Validation runs before any decision is
taken and only records what it sees; the cleaning stage then turns findings into
one of four audited actions.</p>
{_table(dq_rows, {"observations": 0}) if len(dq_rows) else "<p>No validation flags were raised.</p>"}
<h3>What was done about it</h3>
<ul>
<li><strong>Unit errors.</strong> A quote is rescaled by a power of 100 only when
that rescaling moves it an order of magnitude closer to a robust reference built
from its nearest maturity peers of the same type. Using a <em>local</em>
reference rather than a whole-sample one is deliberate: on a steep curve a 1M
rate can legitimately sit two orders of magnitude below a 30Y rate.</li>
<li><strong>Missing quotes.</strong> Reconstructed from the bid/ask mid where a
two-way market exists, and excluded otherwise.</li>
<li><strong>Crossed markets.</strong> Bid and ask are swapped and the observation
is penalised, not discarded &mdash; the mid is still informative.</li>
<li><strong>Stale snapshots.</strong> Staleness is measured <em>relative to the
most recent timestamp in the file</em> rather than against the valuation date, so
a uniformly time-shifted data set is not wiped out.</li>
<li><strong>Duplicates.</strong> Ranked by freshness, then source, then spread;
the survivor is named in the audit trail of every superseded row.</li>
<li><strong>Gross outliers.</strong> Flagged against a deliberately flexible
robust reference fit, and measured against each quote's own pillar consensus (a
shorth, which a contaminated minority cannot move) rather than against the fitted
curve. Three 7Y swaps that agree with each other to a third of a basis point are
not three bad prints, however far a smoothed curve sits from them. Exclusion
needs <em>two</em> conditions: more than 4.7 robust sigma <em>and</em> at least
5bp from those neighbours in yield-equivalent terms. The second gate is not
decoration &mdash; a flexible reference drives the robust scale below half a
basis point, and without an absolute floor a quote 2bp from its peers reads as a
forty-sigma event. No maturity neighbourhood is ever emptied completely, and at
most a quarter of the sample can be removed.</li>
</ul>
{_figure(charts, "data_quality.png",
         "Cleaning decisions and the validation findings behind them.")}
<h3>Every non-trivial decision</h3>
{_table(shown, {"normalized_quote": 6, "weight": 4})}
"""
    )

    sections.append(
        f"""
<h2 id="comparison">4. Model Comparison <span class="jp">モデル比較</span></h2>
<p><strong>Holdout design.</strong> {html.escape(holdout['method'])}. A random
split would be worthless here: four venues quote the same 10Y pillar and several
bonds mature within days of a benchmark swap, so a random split leaks
near-identical instruments across train and validation and measures quote
dispersion instead of curve quality. Blocks move as a unit, and the first and
last blocks are never withheld so the training set always spans the full maturity
range &mdash; the metric therefore measures interpolation, not extrapolation policy.
{holdout['n_train']} instruments trained, {holdout['n_holdout']} withheld across
{len(holdout['holdout_block_indices'])} blocks.</p>
{_table(_metric_table(payload), {"n": 0, "weighted RMSE (bp)": 3, "RMSE (bp)": 3,
                                 "MAE (bp)": 3, "median |r| (bp)": 3, "max |r| (bp)": 3})}
<div class="note">
<p><strong>Selection rule (fixed before the numbers were looked at).</strong>
{html.escape(payload['selection_rule'])}.</p>
<p><strong>Outcome.</strong> {html.escape(payload['selection_rationale'])}</p>
</div>
<p>The honest reading of the table is that the bootstrap is <em>not</em> beaten on
repricing. It reprices its own pillars essentially exactly, and on the blocked
holdout it is competitive. What disqualifies it is the shape of what it produces
between those pillars: its instantaneous forward runs from
{_fmt(other_adm['min_forward_percent'] if other == 'baseline' else admissible['min_forward_percent'], 2)}%
to
{_fmt(other_adm['max_forward_percent'] if other == 'baseline' else admissible['max_forward_percent'], 2)}%
against a quoted rate range of
{_fmt(admissible['quoted_rate_range_percent'][0], 2)}%-{_fmt(admissible['quoted_rate_range_percent'][1], 2)}%.
Those excursions are not information; they are the arithmetic consequence of
forcing a curve through two pillars a few weeks apart whose quotes differ by a
basis point of idiosyncratic noise. A curve carrying them cannot price a
forward-starting trade and produces a key-rate profile that jumps with the
pillar set. Forward-curve roughness differs by
{payload['baseline']['forward_roughness'] / max(payload['advanced']['forward_roughness'], 1e-12):,.0f}x
between the two.</p>
{_figure(charts, "model_comparison.png",
         "Left: weighted RMSE by sample. Right: the difference between the two "
         "estimators, in basis points of zero rate &mdash; the width of the modelling "
         "choice.")}
"""
    )

    sections.append(
        f"""
<h2 id="validation">5. Validation and Repricing <span class="jp">検証と再価格付け</span></h2>
{_table(curve_table, {"tenor (Y)": 2, "zero rate (%)": 4,
                      "instantaneous forward (%)": 4, "discount factor": 6})}
{_figure(charts, "zero_curve.png",
         "Zero curve from both estimators, with the maturities of the "
         "calibrating instruments marked.")}
{_figure(charts, "forward_curve.png",
         "Instantaneous forwards and discount factors. The shaded band is the "
         "admissibility corridor used by the selection rule.")}
<p>The published grid runs from {_fmt(grid[0], 4)}Y to {_fmt(grid[-1], 2)}Y in
{len(curve)} rows. Discount factors are strictly positive throughout (minimum
{_fmt(float(curve['discount_factor'].min()), 6)}), and the zero curve spans
{_fmt(float(curve['zero_rate'].min()) * 100, 3)}% to
{_fmt(float(curve['zero_rate'].max()) * 100, 3)}%.</p>
"""
    )

    sections.append(
        f"""
<h3>Repricing and risk <span class="jp">再価格付けとリスク</span></h3>
{_table(_residual_summary(result), {"n": 0, "median weight": 3,
                                    "weighted RMSE (bp)": 3, "median |r| (bp)": 3,
                                    "max |r| (bp)": 3,
                                    "estimated model error (bp)": 3})}
{_figure(charts, "repricing.png",
         "Repricing residuals in yield-equivalent basis points, with the "
         "calibration weight of each instrument underneath.")}
<h3>Risk</h3>
<p>DV01 is the central finite difference of the receiver / fixed-instrument PV
for a parallel one-basis-point move of the zero curve, on notional 1,000,000 for
deposits and swaps and face 100 for bonds. Key rates use triangular tent bumps
centred on 2Y, 5Y, 10Y and 30Y that peak at their own tenor, decay linearly to
zero at the neighbouring tenors and are flat outside the range, so the four
shapes sum to exactly one at every maturity.</p>
<ul>
<li>Key-rate sensitivities add back to the parallel DV01 to within
<span class="mono">{worst_key:.2e}</span> relative across all
{len(risk)} instruments.</li>
<li>The finite-difference DV01 agrees with the closed-form cash-flow derivative
to within <span class="mono">{worst_dv01:.2e}</span> relative, which is the
expected truncation error of a 1 bp central difference. This check is what caught
a sign error in the float-leg derivative during development.</li>
</ul>
{_figure(charts, "key_rate_profile.png",
         "Key-rate decomposition of the deposit and swap book against the "
         "parallel DV01.")}
"""
    )

    sens_rows = pd.DataFrame(
        [
            {
                "check": c["name"].replace("_", " "),
                "metric": c["metric"].replace("_", " "),
                "value (bp)": c["value"],
            }
            for c in sens
        ]
    )
    sens_detail = "".join(
        f"<li><strong>{html.escape(c['name'].replace('_', ' '))}</strong> "
        f"({_fmt(c['value'], 2)} bp) &mdash; {html.escape(c['description'])}.</li>"
        for c in sens
    )
    sections.append(
        f"""
<h2 id="sensitivity">6. Sensitivity Analysis <span class="jp">感度分析</span></h2>
{_table(sens_rows, {"value (bp)": 3}) if len(sens_rows) else ""}
<ul>{sens_detail}</ul>
{_figure(charts, "sensitivity.png",
         "Maximum absolute zero-rate shift induced by each controlled change.")}
"""
    )

    warnings_html = ""
    if result.warnings:
        warnings_html = (
            '<div class="note warn"><p><strong>Run warnings.</strong></p><ul>'
            + "".join(f"<li>{html.escape(w)}</li>" for w in result.warnings)
            + "</ul></div>"
        )

    sections.append(
        f"""
<h2 id="charts">7. Charts <span class="jp">図表</span></h2>
<p>全図の一覧。各図は上の該当章でも文脈とともに論じている。図はすべて
base64 で本文に埋め込まれており、このHTMLは外部ファイルを一切参照しない。
<em>Every figure the workflow produced, gathered in one place; each is also
discussed in context above. All figures are embedded as base64 data URIs, so
this page references no external file.</em></p>
<ol>
<li><code>zero_curve.png</code> &mdash; 公開ゼロ曲線と基準モデルの比較、較正商品の満期付き。</li>
<li><code>forward_curve.png</code> &mdash; 瞬間フォワードと許容帯、および割引因子。モデル選択の根拠となった図。</li>
<li><code>repricing.png</code> &mdash; 商品別の再価格付け残差（利回り換算bp）と較正ウェイト。</li>
<li><code>model_comparison.png</code> &mdash; 学習／ホールドアウト／全標本の加重RMSEと、両推定量の差。</li>
<li><code>data_quality.png</code> &mdash; クリーニング判断の内訳と検証フラグの件数。</li>
<li><code>sensitivity.png</code> &mdash; 各感度実験が誘発したゼロ金利の最大変化。</li>
<li><code>key_rate_profile.png</code> &mdash; 預金・OISブックのキーレート分解とパラレルDV01。</li>
</ol>
{_figure(charts, "zero_curve.png",
         "1. 公開ゼロ曲線 / Published zero curve, both estimators, with the "
         "maturities of the calibrating instruments marked.")}
{_figure(charts, "forward_curve.png",
         "2. 瞬間フォワードと許容帯 / Instantaneous forward against the "
         "admissibility band, and the published discount factor.")}
{_figure(charts, "repricing.png",
         "3. 再価格付け残差 / Repricing residuals in yield-equivalent basis "
         "points, with the calibration weight underneath.")}
{_figure(charts, "model_comparison.png",
         "4. モデル比較 / Weighted RMSE by sample, and the difference between "
         "the two estimators in basis points of zero rate.")}
{_figure(charts, "data_quality.png",
         "5. データ品質 / Cleaning decisions and the validation findings "
         "behind them.")}
{_figure(charts, "sensitivity.png",
         "6. 感度分析 / Maximum absolute zero-rate shift induced by each "
         "controlled change.")}
{_figure(charts, "key_rate_profile.png",
         "7. キーレート分解 / Key-rate profile of the deposit and OIS book "
         "against the parallel DV01.")}
"""
    )

    sections.append(
        f"""
<h2 id="limits">8. Limitations <span class="jp">限界とモデルリスク</span></h2>
{warnings_html}
<ul>
<li><strong>Single-curve assumption.</strong> One discount curve is fitted to
deposits, OIS and bonds together. In a real market these are three funding bases;
here the bond basis is absorbed into an estimated per-type model error
({_fmt(result.model_error_bp.get('bond'), 2)} bp) rather than modelled explicitly.
Bond-specific valuation should not use this curve without an asset-swap spread.
</li>
<li><strong>Extrapolation.</strong> Beyond the longest calibrating instrument the
instantaneous forward is held flat. That is a policy, not a measurement, and it
carries no market information.</li>
<li><strong>Front end.</strong> Below the shortest deposit the forward is
likewise flat. Nothing in the data constrains overnight-to-1M shape.</li>
<li><strong>Schedule convention &mdash; the largest unresolved exposure.</strong>
<code>CONVENTIONS.md</code> fixes the frequency, the accrual, the face and the par
condition, but is <em>silent</em> on how many periods a fractional maturity has.
The <code>round(T x frequency)</code> rule used here was inferred from the quotes:
it is the only rule that reprices the 1.25Y OIS and the 2.44Y bond consistently.
Fitting the observations well is <em>not</em> proof that it is the rule the data
was generated under. Pricing the same known discount function under the three
defensible rules differs by <strong>94.3bp</strong> on a 1.25Y OIS par rate,
45.6bp at 2.44Y, 7.5bp at 26.4Y, and about <strong>1.25 price points</strong> on
any fractional bond &mdash; an order of magnitude larger than every fitting effect
measured in this project. Half-integer <code>T x frequency</code> cases do not
occur in this file, and the code rounds half away from zero.</li>
<li><strong>Holdout scope.</strong> The blocked holdout tests interpolation
across withheld maturity regions. It cannot test extrapolation, and it cannot
distinguish a genuinely local term-structure feature from noise.</li>
<li><strong>Idiosyncratic bond noise is irreducible.</strong> Roughly
{_fmt(result.model_error_bp.get('bond'), 1)} bp of bond repricing error is not a
fitting failure and cannot be removed by any smooth single curve.</li>
<li><strong>No uncertainty band is published.</strong> The sensitivity suite
brackets the answer but is not a posterior; the numbers in
<code>curves/curve.csv</code> are point estimates.</li>
</ul>
<p>The full treatment, including numerical failure modes and the conditions under
which each default stops being appropriate, is in <code>MODEL_RISKS.md</code>.</p>

<h2 id="next">9. Recommended Next Steps <span class="jp">推奨される次の手順</span></h2>
<ol>
<li>Fit an explicit bond asset-swap spread curve on top of the OIS discount
curve instead of absorbing the basis into a per-type error term; that would let
bonds inform the long end without contaminating it.</li>
<li>Publish an uncertainty band by bootstrapping the calibration residuals, so
downstream users get a distribution rather than a point curve.</li>
<li>Add forward-starting instruments (FRAs, forward swaps) to constrain the
forward curve directly rather than inferring it from spot instruments.</li>
<li>Track the estimated per-type model error over successive snapshots; a
structural change in it is an early warning that the single-curve assumption is
breaking down.</li>
<li>Extend the outlier screen with a same-instrument time-series check once more
than one snapshot is available; the current screen is purely cross-sectional.</li>
</ol>
"""
    )

    toc = "".join(
        f'<li><a href="#{anchor}">{label}</a></li>'
        for anchor, label in (
            ("summary", "1. Executive Summary / エグゼクティブサマリー"),
            ("method", "2. Methodology / 手法"),
            ("data", "3. Data Quality / データ品質"),
            ("comparison", "4. Model Comparison / モデル比較"),
            ("validation", "5. Validation and Repricing / 検証と再価格付け"),
            ("sensitivity", "6. Sensitivity Analysis / 感度分析"),
            ("charts", "7. Charts / 図表"),
            ("limits", "8. Limitations / 限界"),
            ("next", "9. Recommended Next Steps / 推奨される次の手順"),
        )
    )

    admissible_pill = (
        '<span class="pill on">forward curve admissible</span>'
        if admissible["admissible"]
        else '<span class="pill off">forward curve inadmissible</span>'
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Zero-curve research report - {result.valuation_date.date().isoformat()}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
<header class="masthead">
<h1>Zero-curve construction, validation and model risk</h1>
<p class="sub">Valuation date {result.valuation_date.date().isoformat()} &middot;
USD &middot; source <code>{html.escape(result.market_data_path.name)}</code>
&middot; quantcurve {html.escape(__version__)} &middot; market snapshot {html.escape(generated)}</p>
<p class="sub" style="margin-top:8px">
<span class="pill">published model: {html.escape(selected)}</span>
{admissible_pill}
<span class="pill">{len(result.instruments)} calibrating instruments</span>
</p>
<ul class="toc">{toc}</ul>
</header>
{''.join(sections)}
<footer>
<p>Generated by the <code>quantcurve</code> command-line workflow. Every figure in
this report is reproducible from
<code>python -m quantcurve.cli run --market-data ... --output-dir ...
--valuation-date {result.valuation_date.date().isoformat()}</code>; the numbers
behind it are in <code>curves/curve.csv</code> and <code>diagnostics/</code>.</p>
</footer>
</div>
</body>
</html>
"""


def write_report(
    result: WorkflowResult,
    charts: dict[str, bytes],
    path: str | Path,
    compact: bool = False,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_report(result, charts, compact=compact), encoding="utf-8")
    return target
