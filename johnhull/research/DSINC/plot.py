"""Three diagnostic figures from small saved DSINC results; no solver runs."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_results(results, output):
    """Render errors/costs, boundary failures and sensitivity without success filtering."""
    results = Path(results)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "_dsinc_plot_runner", Path(__file__).with_name("run.py")
    )
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    report = runner.replay(results.parent)
    lookup = {r["id"]: r for r in report["records"]}
    cases = runner.load_cases()["primary_groups"]
    anchor = np.array(cases[0]["paper_anchors"]["european"])
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
    for label, color in (("spectral", "tab:blue"), ("fd", "tab:orange")):
        rows = [
            r
            for r in report["records"]
            if r.get("method") == label
            and r["id"].startswith("T0.5:")
            and all(v is not None for v in r.get("values", {}).get("european", [None] * 3))
        ]
        if rows:
            ax.scatter(
                [r["wall_seconds"] for r in rows],
                [
                    max(abs(np.array(r["values"]["european"]) / r["contract"]["strike"] - anchor))
                    for r in rows
                ],
                label=f"{label}: EU printed-anchor difference",
                color=color,
                alpha=0.75,
            )
    ax.axhline(6e-6, color="black", ls="--", lw=1, label="S0 paper gate (EU + AM required)")
    ax.set(
        xlabel="Charged subprocess wall time (s), including setup",
        ylabel="max |European - printed anchor| / K",
        yscale="log",
        title="Price diagnostics and cost; no American DSINC price on failed jobs",
    )
    failed = sum(r["status"] != "completed" for r in report["records"])
    ax.text(
        0.98,
        0.97,
        f"{failed}/{len(report['records'])} jobs failed; none removed from accounting",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
    )
    ax.legend(loc="lower right", fontsize=8)
    fig.savefig(output / "price_cost.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    base = lookup.get("T0.5:S0", {})
    details = base.get("failure", {})
    nodes = details.get("failed_slice", {}).get("nodes", [])
    if nodes:
        settings = base["settings"]
        z = np.linspace(*settings["log_var_bounds"], settings["n_var"])
        statuses = details["failed_slice"]["statuses"]
        valid = np.array([s == "ok" for s in statuses])
        roots = np.array([np.mean(n["bracket"]) for n in nodes])
        axes[0].scatter(
            np.exp(z[valid]), roots[valid], s=12, label="successful nodes in failed slice"
        )
        axes[0].scatter(
            np.exp(z[~valid]),
            np.zeros(np.count_nonzero(~valid)),
            marker="x",
            s=20,
            label="failed nodes; boundary unavailable",
        )
        axes[0].set(
            xscale="log",
            xlabel="Variance v",
            ylabel="log(S*/K)",
            title=f"First backward slice only: n={details['time_index']}",
        )
        axes[0].legend(fontsize=8)
        artifact = results.parent / (runner._slug(base["id"]) + ".npz")
        if artifact.is_file():
            with np.load(artifact, allow_pickle=False) as data:
                for i, row in zip(data["node_indices"], data["residual_scan"], strict=True):
                    axes[1].plot(data["x_scan"], row, label=f"v={np.exp(z[i]):.4g}")
        else:
            axes[1].text(
                0.5, 0.5, "No saved first-slice scan", ha="center", transform=axes[1].transAxes
            )
        axes[1].axhline(0, color="black", lw=0.8)
        axes[1].set(
            xlabel="x = log(S/K)",
            ylabel="Value-matching residual / K",
            title="Raw local residual scans",
        )
        axes[1].legend(fontsize=8)
    else:
        axes[0].text(
            0.5, 0.5, "See saved boundary arrays", ha="center", transform=axes[0].transAxes
        )
    fig.suptitle("No full DSINC boundary: failed nodes remain visible")
    fig.savefig(output / "boundary.png", dpi=150)
    plt.close(fig)
    rows = [lookup.get("T0.5:S0")] + [
        lookup.get("T0.5:S0:" + name) for name in runner.SENSITIVITIES
    ]
    rows = [r for r in rows if r]
    labels = ["S0" if r["id"] == "T0.5:S0" else r["id"].split(":")[-1] for r in rows]
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), layout="constrained", sharex=True)
    base_eu = np.array(
        base.get("values", {}).get("european", [np.nan] * 3), dtype=float
    ) / base.get("contract", {}).get("strike", 1)
    differences = [
        max(abs(np.array(r["values"]["european"]) / r["contract"]["strike"] - base_eu))
        if all(v is not None for v in r["values"]["european"])
        else np.nan
        for r in rows
    ]
    failures = [
        sum(s != "ok" for s in r.get("failure", {}).get("failed_slice", {}).get("statuses", []))
        for r in rows
    ]
    axes[0].bar(labels, differences)
    axes[0].axhline(5e-6, color="black", ls="--", lw=1)
    axes[0].set(
        ylabel="max EU change / K",
        title="Pilot sensitivities: EU diagnostics; AM sensitivity gate unavailable",
    )
    axes[1].bar(labels, failures, color="tab:red")
    axes[1].set(ylabel="Failed boundary nodes", xlabel="One-axis change from S0")
    axes[1].tick_params(axis="x", rotation=30)
    fig.savefig(output / "sensitivity.png", dpi=150)
    plt.close(fig)
    return [output / name for name in ("price_cost.png", "boundary.png", "sensitivity.png")]


def main():
    """Plot a saved result file without recomputing a price."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot_results(args.results, args.output)


if __name__ == "__main__":
    main()
