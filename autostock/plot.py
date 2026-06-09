"""
autostock dashboard — a static progress.png in the spirit of autoresearch.

Regenerable tooling (not part of the read-only metric or the agent-edited
strategy): it imports prepare.py (the engine) and strategy.py (the current best
strategy) and renders a 2x2 panel summary.

Run:
    uv run plot.py                  # equity/rolling stop at TEST_END (lockbox withheld)
    uv run plot.py --reveal-lockbox # extend equity/rolling through the lockbox
"""

import argparse
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import prepare  # noqa: E402
import strategy  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "progress.png")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.tsv")


def _equity(net):
    return (1.0 + net.fillna(0.0)).cumprod()


def _equal_weight(prices):
    n = prices.shape[1]
    return pd.DataFrame(1.0 / n, index=prices.index, columns=prices.columns)


def _shade_segments(ax, xmax, reveal):
    """Shade train (grey) / test (blue) / lockbox (red, only if revealed)."""
    ax.axvspan(pd.Timestamp(prepare.START_DATE), pd.Timestamp(prepare.TRAIN_END),
               color="#888888", alpha=0.12)
    ax.axvspan(pd.Timestamp(prepare.TEST_START), pd.Timestamp(prepare.TEST_END),
               color="#1f77b4", alpha=0.12)
    if reveal:
        ax.axvspan(pd.Timestamp(prepare.LOCKBOX_START), xmax, color="#d62728", alpha=0.12)


def build_figure(prices, reveal_lockbox=False):
    """Build the 2x2 dashboard figure for the current strategy + baseline."""
    end = None if reveal_lockbox else prepare.TEST_END
    weights = strategy.generate_weights(prices)

    net_best, _ = prepare._net_returns(weights, prices)
    net_base, _ = prepare._net_returns(_equal_weight(prices), prices)
    if end is not None:
        net_best = net_best.loc[:end]
        net_base = net_base.loc[:end]
    xmax = net_best.index.max()

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("autostock — research progress (Mag-7, OOS test Sharpe higher = better)",
                 fontsize=14, fontweight="bold")

    # Panel 1: experiment progress from results.tsv
    ax = axes[0, 0]
    if os.path.exists(RESULTS_PATH):
        df = pd.read_csv(RESULTS_PATH, sep="\t")
        pos = range(len(df))
        colors = ["#2ca02c" if s == "keep" else "#cccccc" for s in df["status"]]
        ax.bar(pos, df["sharpe"], color=colors)
        ax.set_xticks(list(pos))
        ax.set_xticklabels([str(d)[:26] for d in df["description"]],
                           rotation=45, ha="right", fontsize=7)
        base = df.loc[df["description"].str.contains("baseline", case=False), "sharpe"]
        if len(base):
            ax.axhline(base.iloc[0], color="#d62728", ls="--", lw=1,
                       label=f"baseline {base.iloc[0]:.3f}")
            ax.legend(fontsize=8)
        ax.set_title("Experiment progress (OOS Sharpe; green = keep)")
        ax.set_ylabel("Sharpe")
    else:
        ax.text(0.5, 0.5, "no results.tsv\n(run experiments first)",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Experiment progress")

    # Panel 2: equity curves (best vs baseline)
    ax = axes[0, 1]
    eq_best, eq_base = _equity(net_best), _equity(net_base)
    ax.plot(eq_best.index, eq_best.values, label="best strategy", color="#1f77b4")
    ax.plot(eq_base.index, eq_base.values, label="equal-weight baseline",
            color="#ff7f0e", alpha=0.85)
    ax.set_yscale("log")
    _shade_segments(ax, xmax, reveal_lockbox)
    ax.set_title("Equity curve (log scale)")
    ax.legend(fontsize=8)

    # Panel 3: rolling Sharpe (best)
    ax = axes[1, 0]
    roll = prepare._rolling_sharpe(net_best)
    ax.plot(roll.index, roll.values, color="#1f77b4")
    ax.axhline(0, color="black", lw=0.8)
    _shade_segments(ax, xmax, reveal_lockbox)
    ax.set_title(f"Rolling {prepare.ROLL_WINDOW}d Sharpe (best)")
    ax.set_ylabel("Sharpe")

    # Panel 4: annual Sharpe (best) — always within visible (<= TEST_END) data
    ax = axes[1, 1]
    m = prepare.evaluate(weights, prices)
    years = sorted(m["annual_sharpe"])
    vals = [m["annual_sharpe"][y] for y in years]
    ax.bar(range(len(years)), vals,
           color=["#2ca02c" if v >= 0 else "#d62728" for v in vals])
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha="right", fontsize=8)
    ax.set_title("Annual Sharpe (best)")
    ax.set_ylabel("Sharpe")

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reveal-lockbox", action="store_true")
    args = ap.parse_args()

    prices = prepare.load_prices()
    fig = build_figure(prices, reveal_lockbox=args.reveal_lockbox)
    fig.savefig(OUT_PATH, dpi=120)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
