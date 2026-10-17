"""How far each model's share drifts in a 479-month sample (design §5.1, not a gate).

The DGP is the ACM model estimated on US GSW data (1961-06..2026-06), so no
Japanese estimate is used. The shadow-rate model is excluded (cost; spec §9).

    $PY macrokit/research/2026-10-jgb-term-premium/small_sample.py \
        --data-root /home/kazumasa/projects/macrokit/data
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

from macrokit.snapshot import latest_payload
from macrokit.sources import us_term
from macrokit.termstructure import acm, dns, synthetic
from macrokit.termstructure.curve import ZeroPanel
from macrokit.termstructure.decompose import largest_rise_window, share_of

HERE = Path(__file__).resolve().parent
SEED = 20261117
SAMPLES, MONTHS, WINDOW = 500, 479, 23


def us_params(raw_root: Path) -> synthetic.AffineParams:
    days = us_term.parse_gsw(latest_payload(raw_root, us_term.SOURCE, "gsw").read_bytes())
    ends = [
        d
        for d in us_term.month_end_days(days)
        if date(1961, 6, 1) <= d.obs_date <= date(2026, 6, 30)
    ]
    months = np.arange(1, 121)
    panel = ZeroPanel(
        tuple(d.obs_date for d in ends),
        months,
        np.vstack([us_term.gsw_zero(d, months) for d in ends]),
    )
    return synthetic.AffineParams.from_fit(acm.fit_acm(panel))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    params = us_params(args.data_root / "raw")
    rng = np.random.default_rng(SEED)
    errors: dict[str, list[float]] = {"acm": [], "acm_bc": [], "dns": []}
    for _ in range(SAMPLES):
        syn = synthetic.simulate_affine(params, MONTHS, rng)
        y = syn.panel.column(120)
        i0, i1 = largest_rise_window(y, WINDOW)
        truth = float(share_of(syn.expected_pct, y, i0, i1))
        fit = acm.fit_acm(syn.panel)
        bc = acm.kilian_correct(fit.factors, fit.var, 1000, rng)
        estimates = {
            "acm": fit.expected(120),
            "acm_bc": fit.expected(120, bc.mu, bc.phi),
            "dns": dns.fit_dns(syn.panel).expected(120),
        }
        for model, expected in estimates.items():
            errors[model].append(float(share_of(expected, y, i0, i1)) - truth)
    summary = {
        model: {
            "mean_error": float(np.mean(v)),
            "sd_error": float(np.std(v)),
            "q05": float(np.quantile(v, 0.05)),
            "q50": float(np.quantile(v, 0.50)),
            "q95": float(np.quantile(v, 0.95)),
        }
        for model, v in errors.items()
    }
    out = {
        "samples": SAMPLES,
        "months": MONTHS,
        "seed": SEED,
        "dgp": "US ACM K=5, GSW 1961-06..2026-06",
        "share_error": summary,
    }
    (HERE / "small_sample.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
