"""Self-contained Phase 2 pricing report; no network or live training."""

from __future__ import annotations

import html
import json
from pathlib import Path

from .pricing_plotting import (
    error_comparison_figure,
    greek_error_figure,
    hard_check_figure,
    speed_figure,
)

REQUIRED_SECTIONS = (
    "Label QA and fingerprints",
    "Baselines and learning outcome",
    "Learning curve",
    "Error surface and buckets",
    "Greek slices",
    "Hard arbitrage checks",
    "Out-of-domain shell",
    "Calibration recovery",
    "CPU speed and break-even",
    "Limitations and negative results",
)


def _figure_html(figure, include_js):
    return figure.to_html(
        full_html=False,
        include_plotlyjs="inline" if include_js else False,
        config={"responsive": True, "displaylogo": False},
    )


def _table(rows):
    return (
        "<table><tbody>"
        + "".join(
            f"<tr><th>{html.escape(str(name))}</th><td>{html.escape(str(value))}</td></tr>"
            for name, value in rows
        )
        + "</tbody></table>"
    )


def _benchmark_table(evaluation):
    benchmark = evaluation["benchmark"]
    rows = []
    for name in ("analytic", "heston_cos", "monte_carlo", "polynomial", "neural"):
        timings = benchmark.get(name)
        if timings:
            largest = timings[-1]
            rows.append(
                (
                    f"{name} ({largest['batch_size']} rows)",
                    f"{largest['median_ms']:.6g} ms median",
                )
            )
    conditions = benchmark.get("conditions", {})
    if conditions:
        rows.extend(
            (
                ("common harness", bool(conditions.get("common_input_slices"))),
                ("warmup / repeats", f"{conditions.get('warmup')} / {conditions.get('repeats')}"),
                ("device", conditions.get("device")),
            )
        )
    teacher_metadata = benchmark.get("teacher_metadata", {})
    heston = teacher_metadata.get("heston_cos", {})
    monte_carlo = teacher_metadata.get("monte_carlo", {})
    if heston:
        rows.append(("Heston/COS terms", heston.get("terms")))
    if monte_carlo:
        rows.append(
            (
                "MC seed / paths per row",
                f"{monte_carlo.get('seed')} / {monte_carlo.get('paths_per_row')}",
            )
        )
    return _table(rows)


def build_pricing_report(
    evaluation_path: str | Path,
    *,
    history_path: str | Path | None = None,
    output_path: str | Path,
):
    """Render the self-contained offline HTML pricing report."""
    evaluation_path = Path(evaluation_path)
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    history = (
        [] if history_path is None else json.loads(Path(history_path).read_text(encoding="utf-8"))
    )
    figures = [
        error_comparison_figure(evaluation),
        greek_error_figure(evaluation),
        hard_check_figure(evaluation),
        speed_figure(evaluation),
    ]
    figure_html = [_figure_html(figure, index == 0) for index, figure in enumerate(figures)]
    fingerprints = evaluation["dataset_fingerprints"]
    test = evaluation["splits"]["test"]
    ood = evaluation["splits"]["ood"]
    hard = evaluation["hard_validation"]
    acceptance = evaluation["acceptance"]
    residual = evaluation.get("residual_correction", {})
    negative = [name for name, passed in acceptance.items() if not passed]
    history_rows = [
        ("epochs", len(history)),
        (
            "best validation MAE",
            min((row["validation_price_mae"] for row in history), default="n/a"),
        ),
    ]
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Neural Pricing Surrogate — Offline Validation</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:auto;padding:2rem;color:#111827}}section{{margin:2rem 0}}table{{border-collapse:collapse}}th,td{{padding:.45rem;border:1px solid #d1d5db;text-align:left}}code{{background:#f1f5f9;padding:.1rem .3rem}}.warn{{color:#b91c1c}}</style></head><body>
<h1>Neural Pricing Surrogate — Phase 2</h1>
<p>Offline, synthetic Black–Scholes reference experiment. No market-predictive or production-readiness claim is made.</p>
<section><h2>{REQUIRED_SECTIONS[0]}</h2>{_table(fingerprints.items())}<p>Evaluation artifact: <code>{html.escape(evaluation_path.name)}</code>; config fingerprint <code>{html.escape(evaluation["config_fingerprint"])}</code>.</p></section>
<section><h2>{REQUIRED_SECTIONS[1]}</h2>{figure_html[0]}{_table((("Polynomial price MAE", test["polynomial_price"]["mae"]), ("Neural price MAE", test["neural_price"]["mae"]), ("Heston raw-price polynomial MAE", residual.get("raw_price_mae", "n/a")), ("Heston BSM-residual polynomial MAE", residual.get("bsm_residual_mae", "n/a")), ("Heston route adopted", residual.get("adopted", "n/a"))))}</section>
<section><h2>{REQUIRED_SECTIONS[2]}</h2>{_table(history_rows)}</section>
<section><h2>{REQUIRED_SECTIONS[3]}</h2>{_table((name, values["mae"]) for name, values in test["price_buckets"].items())}</section>
<section><h2>{REQUIRED_SECTIONS[4]}</h2>{figure_html[1]}</section>
<section><h2>{REQUIRED_SECTIONS[5]}</h2>{figure_html[2]}<p>arbitrage_free = <strong>{hard["arbitrage_free"]}</strong>. This flag is true only when every applicable hard check passes.</p></section>
<section><h2>{REQUIRED_SECTIONS[6]}</h2>{_table((("OOD price MAE", ood["neural_price"]["mae"]), ("OOD worst error", ood["neural_price"]["worst_absolute_error"])))}</section>
<section><h2>{REQUIRED_SECTIONS[7]}</h2>{_table(evaluation["calibration"].items())}</section>
<section><h2>{REQUIRED_SECTIONS[8]}</h2>{figure_html[3]}{_benchmark_table(evaluation)}<p>Break-even batch: {evaluation["benchmark"]["neural_vs_analytic_break_even_batch"]}</p><p>Heston/COS and seeded Monte Carlo are numerical-teacher latency workloads. Their prices are not used as Black–Scholes accuracy targets.</p></section>
<section><h2>{REQUIRED_SECTIONS[9]}</h2><p class="warn">Failed acceptance checks: {html.escape(", ".join(negative) or "none")}.</p><ul><li>Teachers are synthetic; MC teacher noise must be read with its confidence interval.</li><li>OOD results are extrapolation diagnostics, not evidence of market performance.</li><li>Price-only remains the accepted fallback if DML or direct heads do not improve Greeks without harming price.</li></ul></section>
</body></html>"""
    document = "\n".join(line.rstrip() for line in document.splitlines()) + "\n"
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output
