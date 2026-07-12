"""Publication-style static figures for the rough-volatility visual lab."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import ArrayLike, NDArray

from rough_volatility.config import ProjectConfig

FloatArray = NDArray[np.float64]

INK = "#27313A"
MUTED = "#66727C"
GRID = "#DCE2E7"
BLUE = "#2F6BFF"
GOLD = "#D69E2E"
ORANGE = "#E07A3F"
OLIVE = "#7A8B3A"
PINK = "#C95B8B"
PALETTE = (BLUE, GOLD, ORANGE, OLIVE, PINK)
LINE_STYLES = ("-", "--", "-.", ":")
MARKERS = ("o", "s", "^", "D", "v")


@dataclass(frozen=True)
class ChartContract:
    """Compact analytical and delivery contract for one shipped figure."""

    question: str
    takeaway: str
    family: str
    palette_policy: str
    minimum_data: str
    output: str


def _contract(
    question: str,
    takeaway: str,
    family: str,
    minimum_data: str,
) -> ChartContract:
    return ChartContract(
        question=question,
        takeaway=takeaway,
        family=family,
        palette_policy="hard two-root cap or explicit multi-category palette; line style also encodes series",
        minimum_data=minimum_data,
        output="Matplotlib PNG + SVG under artifacts/figures",
    )


CHART_CONTRACTS: dict[str, ChartContract] = {
    "fbm_paths": _contract(
        "How does path texture vary with H?",
        "Lower H produces finer local oscillation at matched horizon scale.",
        "trend / small multiples",
        ">=2 H values and >=64 time points",
    ),
    "fbm_zoom": _contract(
        "Does local roughness remain visible under zoom?",
        "The H=0.1 path remains visibly more irregular locally.",
        "trend / small multiples",
        ">=16 points in the zoom interval",
    ),
    "fgn_increments": _contract(
        "How do increments differ across H?",
        "Rough increments alternate more sharply without implying larger unconditional scale.",
        "trend / small multiples",
        ">=64 increments per H",
    ),
    "increment_acf": _contract(
        "Are short-lag increments persistent or anti-persistent?",
        "H<0.5 gives negative short-lag correlation; H>0.5 gives positive correlation.",
        "trend / benchmark",
        ">=8 lags per H",
    ),
    "structure_scaling": _contract(
        "Does the second-order structure function scale as delta^(2H)?",
        "Log-log slopes recover the expected H ordering.",
        "uncertainty & benchmark",
        ">=5 log-spaced lags per H",
    ),
    "hurst_distributions": _contract(
        "How dispersed are finite-sample H estimates?",
        "Estimator dispersion narrows with sample size but does not vanish.",
        "distribution / box plot",
        ">=3 replications per group",
    ),
    "hurst_bias": _contract(
        "How do bias and sample size interact?",
        "Bias and RMSE generally shrink with longer samples, at estimator-specific rates.",
        "comparison / line-dot",
        ">=2 sample sizes and >=2 estimators",
    ),
    "ou_vs_fou": _contract(
        "How does rough log-volatility differ from ordinary OU?",
        "Matched-scale fOU has sharper local movement despite similar broad dispersion.",
        "trend / small multiples",
        ">=64 time points per model",
    ),
    "ou_volatility": _contract(
        "How does exponentiation translate log roughness into volatility?",
        "Positive volatility preserves the rough local texture.",
        "trend / small multiples",
        ">=64 time points per model",
    ),
    "ou_acf": _contract(
        "Can levels look persistent while increments are anti-persistent?",
        "Level and increment ACFs answer different dependence questions.",
        "trend / paired panels",
        ">=8 lags per model",
    ),
    "model_spot": _contract(
        "How do rBergomi and Heston spot paths compare under CRN?",
        "Common shocks isolate model-dynamics differences.",
        "trend / small multiples",
        ">=2 retained paths per model",
    ),
    "model_variance": _contract(
        "How do rough and Markovian variance paths differ?",
        "rBergomi variance changes more abruptly at fine scales.",
        "trend / small multiples",
        ">=2 retained paths per model",
    ),
    "terminal_returns": _contract(
        "Do the models imply different terminal-return shapes?",
        "Distribution shape is compared on a common axis and sample size.",
        "distribution / histogram",
        ">=100 terminal paths per model",
    ),
    "realized_variance": _contract(
        "How do realized-variance distributions differ?",
        "The rough model changes the dispersion and tail of integrated path variability.",
        "distribution / histogram",
        ">=100 paths per model",
    ),
    "leverage": _contract(
        "How strongly do returns co-move with future variance changes?",
        "Both models encode negative leverage, with different finite-step strength.",
        "relationship / scatter",
        ">=20 interval observations per model",
    ),
    "iv_smiles": _contract(
        "How do smiles vary by maturity and model?",
        "Maturity selectors in the report rest on visibly distinct smile families.",
        "trend / small multiples",
        ">=5 strikes and >=2 maturities",
    ),
    "iv_surface": _contract(
        "How does implied volatility vary jointly in k and T?",
        "Heatmaps expose short-maturity shape without 3D perspective distortion.",
        "matrix / heatmap",
        ">=5 strikes by >=2 maturities",
    ),
    "skew_term": _contract(
        "How does ATM skew decay with maturity for each H?",
        "Smaller H generates steeper short-maturity skew magnitude.",
        "uncertainty / line-dot",
        ">=3 maturities per H",
    ),
    "skew_scaling": _contract(
        "Is absolute skew approximately a maturity power law?",
        "Fitted slopes can be compared with H-1/2 without claiming exact asymptotics.",
        "uncertainty & benchmark / log-log",
        ">=3 valid maturities per H",
    ),
    "hawkes_events": _contract(
        "How does self-excitation alter event clustering?",
        "Near-critical flow forms bursts absent from the Poisson baseline.",
        "event raster / small multiples",
        ">=20 events per scenario",
    ),
    "hawkes_counts": _contract(
        "How does clustered flow appear after binning?",
        "Near-critical counts are more bursty at the same long-run rate target.",
        "trend / small multiples",
        ">=20 bins per scenario",
    ),
    "hawkes_intensity": _contract(
        "What intensity dynamics generate the bursts?",
        "Conditional intensity jumps after events and decays across kernel scales.",
        "trend / small multiples",
        ">=20 grid points per scenario",
    ),
    "hawkes_price_rv": _contract(
        "How can clustered order flow create a rough-looking proxy?",
        "Signed flow creates clustered realized-variance proxies but not structural identification.",
        "trend / paired small multiples",
        ">=20 bins per scenario",
    ),
    "noise_bias": _contract(
        "How sensitive is H bias to noise, stride, and preprocessing?",
        "Measurement choices materially shift estimated roughness.",
        "matrix / diverging heatmap",
        ">=2 noise levels by >=2 strides",
    ),
}


def apply_style() -> None:
    """Apply a restrained, reproducible research-chart style."""
    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "grid.alpha": 0.8,
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.titleweight": "semibold",
            "axes.labelsize": 9,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "legend.frameon": False,
            "legend.fontsize": 8,
            "lines.linewidth": 1.6,
            "savefig.facecolor": "white",
            "svg.fonttype": "path",
        }
    )


def _title(axis: Axes, title: str, subtitle: str) -> None:
    axis.set_title(f"{title}\n{subtitle}", loc="left", pad=10)


def _figure_title(figure: Figure, title: str, subtitle: str) -> None:
    figure.suptitle(
        f"{title}\n{subtitle}",
        x=0.01,
        y=1.04,
        ha="left",
        va="bottom",
        fontsize=12,
        fontweight="semibold",
        color=INK,
    )


def _axes(n: int, *, width: float = 4.0, height: float = 3.2) -> tuple[Figure, list[Axes]]:
    figure, axes = plt.subplots(
        1, n, figsize=(max(6.0, width * n), height), constrained_layout=True, squeeze=False
    )
    return figure, list(axes.ravel())


def _series_style(index: int) -> dict[str, Any]:
    return {
        "color": PALETTE[index % len(PALETTE)],
        "linestyle": LINE_STYLES[index % len(LINE_STYLES)],
        "marker": MARKERS[index % len(MARKERS)],
    }


def thin(*arrays: ArrayLike, max_points: int = 2500) -> tuple[FloatArray, ...]:
    """Thin aligned arrays evenly while retaining both endpoints."""
    if not arrays:
        raise ValueError("at least one array is required")
    values = tuple(np.asarray(array) for array in arrays)
    length = len(values[0])
    if any(len(value) != length for value in values):
        raise ValueError("all arrays must have equal length")
    if max_points < 2:
        raise ValueError("max_points must be at least two")
    if length <= max_points:
        return values  # type: ignore[return-value]
    indices = np.unique(np.rint(np.linspace(0, length - 1, max_points)).astype(int))
    return tuple(value[indices] for value in values)  # type: ignore[return-value]


def save_figure(figure: Figure, base: str | Path) -> tuple[Path, Path]:
    """Save one figure as a 150-DPI PNG and compact vector SVG."""
    output = Path(base)
    output.parent.mkdir(parents=True, exist_ok=True)
    png = output.with_suffix(".png")
    svg = output.with_suffix(".svg")
    figure.savefig(png, dpi=150, bbox_inches="tight")
    figure.savefig(svg, bbox_inches="tight")
    return png, svg


def plot_fbm_paths(frame: pd.DataFrame) -> Figure:
    h_values = sorted(frame["h"].unique())
    figure, axes = _axes(len(h_values))
    for h_index, (axis, h) in enumerate(zip(axes, h_values, strict=True)):
        subset = frame[frame["h"] == h]
        for path_index, (_, path) in enumerate(subset.groupby("path_id")):
            x, y = thin(path["time"], path["value"])
            axis.plot(
                x, y, color=PALETTE[h_index % len(PALETTE)], alpha=0.95 if path_index == 0 else 0.3
            )
        axis.set_title(f"H={h:g}", loc="left")
        axis.set_xlabel("Time")
        axis.set_ylabel("$B_t^H$")
    _figure_title(
        figure,
        "Fractional Brownian-motion paths",
        "Matched horizon scale; retained synthetic paths",
    )
    return figure


def plot_fbm_zoom(frame: pd.DataFrame) -> Figure:
    h_values = sorted(frame["h"].unique())
    figure, axes = _axes(len(h_values))
    lower, upper = frame["time"].max() * 0.45, frame["time"].max() * 0.55
    for h_index, (axis, h) in enumerate(zip(axes, h_values, strict=True)):
        subset = frame[(frame["h"] == h) & (frame["path_id"] == frame["path_id"].min())]
        zoom = subset[subset["time"].between(lower, upper)]
        axis.plot(zoom["time"], zoom["value"], color=PALETTE[h_index], marker="o", markersize=2)
        axis.set_title(f"H={h:g}", loc="left")
        axis.set_xlabel("Time")
        axis.set_ylabel("$B_t^H$")
    _figure_title(figure, "Local path zoom", f"Time window [{lower:.2f}, {upper:.2f}]")
    return figure


def plot_fgn_increments(frame: pd.DataFrame) -> Figure:
    h_values = sorted(frame["h"].unique())
    figure, axes = _axes(len(h_values))
    for h_index, (axis, h) in enumerate(zip(axes, h_values, strict=True)):
        subset = frame[(frame["h"] == h) & (frame["path_id"] == frame["path_id"].min())].head(250)
        axis.plot(subset["time"], subset["increment"], color=PALETTE[h_index])
        axis.axhline(0.0, color=INK, linewidth=0.8)
        axis.set_title(f"H={h:g}", loc="left")
        axis.set_xlabel("Time")
        axis.set_ylabel("Increment")
    _figure_title(
        figure,
        "Fractional Gaussian-noise increments",
        "First 250 increments; zero reference shown",
    )
    return figure


def plot_increment_acf(frame: pd.DataFrame) -> Figure:
    figure, axes = _axes(1, width=7)
    axis = axes[0]
    for index, (h, group) in enumerate(frame.groupby("h", sort=True)):
        style = _series_style(index)
        axis.plot(group["lag"], group["acf"], label=f"H={h:g}", **style, markersize=3)
    axis.axhline(0.0, color=INK, linewidth=0.8)
    _title(axis, "Increment autocorrelation", "Mean across paths; short lags only")
    axis.set_xlabel("Lag")
    axis.set_ylabel("ACF")
    axis.legend(ncol=min(4, frame["h"].nunique()))
    return figure


def plot_structure_scaling(frame: pd.DataFrame) -> Figure:
    data = frame[frame["q"] == 2.0]
    figure, axes = _axes(1, width=7)
    axis = axes[0]
    for index, (h, group) in enumerate(data.groupby("h", sort=True)):
        style = _series_style(index)
        axis.loglog(
            group["delta"], group["moment"], label=f"H={h:g} observed", **style, markersize=4
        )
        axis.loglog(group["delta"], group["fitted"], color=style["color"], linestyle=":", alpha=0.8)
    _title(
        axis,
        "Second-order structure-function scaling",
        r"$S_2(\Delta)$ with fitted log-log lines; slope is $2H$",
    )
    axis.set_xlabel(r"Lag $\Delta$")
    axis.set_ylabel(r"$S_2(\Delta)$")
    axis.legend(ncol=2)
    return figure


def plot_hurst_distributions(frame: pd.DataFrame) -> Figure:
    data = frame[(frame["estimator"] == "variogram") & frame["ok"].astype(bool)]
    h_values = sorted(data["true_h"].unique())
    figure, axes = _axes(len(h_values))
    for axis, h in zip(axes, h_values, strict=True):
        subset = data[data["true_h"] == h]
        sizes = sorted(subset["sample_size"].unique())
        values = [subset[subset["sample_size"] == size]["h_hat"].dropna() for size in sizes]
        axis.boxplot(
            values,
            tick_labels=[str(size) for size in sizes],
            patch_artist=True,
            boxprops={"facecolor": "#DDE7FF", "edgecolor": BLUE},
            medianprops={"color": INK},
        )
        axis.axhline(h, color=INK, linestyle="--", label="True H")
        axis.set_title(f"True H={h:g}", loc="left")
        axis.set_xlabel("Sample size")
        axis.set_ylabel("Estimated H")
    _figure_title(
        figure,
        "H-estimate distributions",
        "Variogram estimator; boxes by increment count",
    )
    return figure


def plot_hurst_bias(frame: pd.DataFrame) -> Figure:
    h_values = sorted(frame["true_h"].unique())
    figure, axes = _axes(len(h_values))
    for axis, h in zip(axes, h_values, strict=True):
        subset = frame[frame["true_h"] == h]
        for index, (estimator, group) in enumerate(subset.groupby("estimator", sort=True)):
            style = _series_style(index)
            axis.semilogx(
                group["sample_size"],
                group["bias"],
                label=estimator.replace("_", " "),
                **style,
                markersize=4,
            )
        axis.axhline(0.0, color=INK, linewidth=0.8)
        axis.set_title(f"True H={h:g}", loc="left")
        axis.set_xlabel("Sample size")
        axis.set_ylabel("Bias")
        axis.legend()
    _figure_title(
        figure,
        "Hurst-estimator bias",
        "Mean estimate minus truth; log sample-size axis",
    )
    return figure


def _plot_ou_paths(frame: pd.DataFrame, column: str, title: str, ylabel: str) -> Figure:
    models = list(frame["model"].drop_duplicates())
    figure, axes = _axes(len(models))
    for index, (axis, model) in enumerate(zip(axes, models, strict=True)):
        subset = frame[frame["model"] == model]
        for path_index, (_, path) in enumerate(subset.groupby("path_id")):
            x, y = thin(path["time"], path[column])
            axis.plot(x, y, color=PALETTE[index], alpha=0.95 if path_index == 0 else 0.25)
        axis.set_title(model, loc="left")
        axis.set_xlabel("Time (years)")
        axis.set_ylabel(ylabel)
    _figure_title(
        figure,
        f"{title}: ordinary OU versus fractional OU",
        "Matched broad scale; retained paths",
    )
    return figure


def plot_ou_vs_fou(frame: pd.DataFrame) -> Figure:
    return _plot_ou_paths(frame, "log_volatility", "Log-volatility", "$X_t$")


def plot_ou_volatility(frame: pd.DataFrame) -> Figure:
    return _plot_ou_paths(frame, "volatility", "Volatility", r"$\exp(X_t)$")


def plot_ou_acf(frame: pd.DataFrame) -> Figure:
    data = frame[frame["metric"].isin(["level_acf", "increment_acf"])]
    figure, axes = _axes(2)
    for axis, metric, label in zip(
        axes, ("level_acf", "increment_acf"), ("Levels", "Increments"), strict=True
    ):
        subset = data[data["metric"] == metric]
        for index, (model, group) in enumerate(subset.groupby("model", sort=False)):
            style = _series_style(index)
            axis.plot(group["x"], group["value"], label=model, **style, markersize=3)
        axis.axhline(0.0, color=INK, linewidth=0.8)
        axis.set_title(label, loc="left")
        axis.set_xlabel("Lag")
        axis.set_ylabel("ACF")
        axis.legend()
    _figure_title(
        figure,
        "Log-volatility autocorrelation",
        "Mean across paths; levels and increments answer different questions",
    )
    return figure


def _plot_model_paths(frame: pd.DataFrame, column: str, title: str, ylabel: str) -> Figure:
    models = list(frame["model"].drop_duplicates())
    figure, axes = _axes(len(models))
    for index, (axis, model) in enumerate(zip(axes, models, strict=True)):
        subset = frame[frame["model"] == model]
        for path_index, (_, path) in enumerate(subset.groupby("path_id")):
            x, y = thin(path["time"], path[column])
            axis.plot(x, y, color=PALETTE[index], alpha=0.9 if path_index == 0 else 0.22)
        axis.set_title(model.replace("_", " "), loc="left")
        axis.set_xlabel("Maturity (years)")
        axis.set_ylabel(ylabel)
    _figure_title(figure, title, "Common random numbers; retained path reservoir")
    return figure


def plot_model_spot(frame: pd.DataFrame) -> Figure:
    return _plot_model_paths(frame, "spot", "Spot paths", "Spot")


def plot_model_variance(frame: pd.DataFrame) -> Figure:
    return _plot_model_paths(frame, "variance", "Variance paths", "Variance")


def _distribution(frame: pd.DataFrame, column: str, title: str, xlabel: str) -> Figure:
    figure, axes = _axes(1, width=7)
    axis = axes[0]
    for index, (model, group) in enumerate(frame.groupby("model", sort=False)):
        axis.hist(
            group[column].dropna(),
            bins=50,
            density=True,
            histtype="step",
            linewidth=1.8,
            color=PALETTE[index],
            label=f"{model.replace('_', ' ')} (n={len(group):,})",
        )
    _title(axis, title, "Density-normalized synthetic Monte Carlo distribution")
    axis.set_xlabel(xlabel)
    axis.set_ylabel("Density")
    axis.legend()
    return figure


def plot_terminal_returns(frame: pd.DataFrame) -> Figure:
    return _distribution(
        frame, "terminal_log_return", "Terminal log-return distributions", "Log return"
    )


def plot_realized_variance(frame: pd.DataFrame) -> Figure:
    return _distribution(
        frame, "realized_variance", "Realized-variance distributions", "Sum of squared log returns"
    )


def plot_leverage(frame: pd.DataFrame) -> Figure:
    models = list(frame["model"].drop_duplicates())
    figure, axes = _axes(len(models))
    for index, (axis, model) in enumerate(zip(axes, models, strict=True)):
        group = frame[frame["model"] == model]
        x, y = thin(group["return"], group["future_variance_change"], max_points=5000)
        axis.scatter(
            x, y, s=5, alpha=0.18, color=PALETTE[index], edgecolors="none", rasterized=True
        )
        correlation = np.corrcoef(x, y)[0, 1] if len(x) > 1 else np.nan
        _title(
            axis,
            f"Leverage relation · {model.replace('_', ' ')}",
            f"Interval grain; correlation={correlation:.3f}",
        )
        axis.set_xlabel("Log return")
        axis.set_ylabel("Next variance change")
    return figure


def plot_iv_smiles(frame: pd.DataFrame) -> Figure:
    models = list(frame["model"].drop_duplicates())
    figure, axes = _axes(len(models), width=5)
    for model_index, (axis, model) in enumerate(zip(axes, models, strict=True)):
        subset = frame[(frame["model"] == model) & frame["ok"].astype(bool)]
        maturities = sorted(subset["maturity"].unique())
        for maturity_index, maturity in enumerate(maturities):
            group = subset[subset["maturity"] == maturity]
            color = mpl.colors.to_hex(
                plt.get_cmap("Blues" if model_index == 0 else "Oranges")(
                    (maturity_index + 2) / (len(maturities) + 2)
                )
            )
            axis.errorbar(
                group["k"],
                group["iv"],
                yerr=1.96 * group["iv_se"],
                color=color,
                marker=MARKERS[maturity_index % len(MARKERS)],
                markersize=3,
                linewidth=1.2,
                label=f"T={maturity:g}",
            )
        axis.set_title(model.replace("_", " "), loc="left")
        axis.set_xlabel("Log-moneyness k")
        axis.set_ylabel("Implied volatility")
        axis.legend(ncol=2)
    _figure_title(
        figure,
        "Implied-volatility smiles",
        "95% delta-method Monte Carlo intervals",
    )
    return figure


def plot_iv_surface(frame: pd.DataFrame) -> Figure:
    models = list(frame["model"].drop_duplicates())
    figure, axes = _axes(len(models), width=5)
    for axis, model in zip(axes, models, strict=True):
        subset = frame[(frame["model"] == model) & frame["ok"].astype(bool)]
        pivot = subset.pivot(index="maturity", columns="k", values="iv")
        image = axis.imshow(
            pivot.to_numpy(),
            aspect="auto",
            origin="lower",
            cmap="Blues",
            extent=[pivot.columns.min(), pivot.columns.max(), pivot.index.min(), pivot.index.max()],
        )
        figure.colorbar(image, ax=axis, label="Implied volatility", shrink=0.8)
        axis.set_title(model.replace("_", " "), loc="left")
        axis.set_xlabel("Log-moneyness k")
        axis.set_ylabel("Maturity (years)")
    _figure_title(
        figure,
        "Implied-volatility surfaces",
        "Heatmaps avoid perspective distortion",
    )
    return figure


def plot_skew_term(frame: pd.DataFrame) -> Figure:
    figure, axes = _axes(1, width=7)
    axis = axes[0]
    for index, (h, group) in enumerate(frame[frame["ok"].astype(bool)].groupby("h", sort=True)):
        style = _series_style(index)
        axis.errorbar(
            group["maturity"],
            group["skew"],
            yerr=1.96 * group["skew_se"],
            label=f"H={h:g}",
            color=style["color"],
            linestyle=style["linestyle"],
            marker=style["marker"],
            markersize=4,
        )
    axis.axhline(0.0, color=INK, linewidth=0.8)
    axis.set_xscale("log")
    _title(
        axis, "ATM skew term structure", "Local weighted-quadratic slope; 95% Monte Carlo intervals"
    )
    axis.set_xlabel("Maturity (years, log scale)")
    axis.set_ylabel(r"$\partial \sigma_{imp}/\partial k|_{0}$")
    axis.legend(ncol=2)
    return figure


def plot_skew_scaling(term: pd.DataFrame, powers: pd.DataFrame) -> Figure:
    figure, axes = _axes(1, width=7)
    axis = axes[0]
    power_map = powers.set_index("h") if not powers.empty else pd.DataFrame()
    for index, (h, group) in enumerate(term[term["ok"].astype(bool)].groupby("h", sort=True)):
        style = _series_style(index)
        x = group["maturity"].to_numpy()
        y = np.abs(group["skew"].to_numpy())
        axis.loglog(
            x,
            y,
            label=f"H={h:g} observed",
            color=style["color"],
            marker=style["marker"],
            linestyle="none",
        )
        if h in power_map.index and bool(power_map.loc[h, "ok"]):
            beta = float(power_map.loc[h, "beta"])
            intercept = float(power_map.loc[h, "intercept"])
            axis.loglog(
                x,
                np.exp(intercept) * x**beta,
                color=style["color"],
                linestyle=style["linestyle"],
                label=f"fit β={beta:.3f}; theory={h - 0.5:.2f}",
            )
    _title(
        axis, "Short-maturity skew scaling", r"$|\mathrm{ATM\ skew}|$ versus T; finite-maturity fit"
    )
    axis.set_xlabel("Maturity T")
    axis.set_ylabel("Absolute ATM skew")
    axis.legend(ncol=2)
    return figure


def plot_hawkes_events(frame: pd.DataFrame) -> Figure:
    scenarios = list(frame["scenario"].drop_duplicates())
    figure, axes = _axes(len(scenarios))
    for index, (axis, scenario) in enumerate(zip(axes, scenarios, strict=True)):
        group = frame[frame["scenario"] == scenario]
        horizon = min(group["time"].max(), 100.0) if len(group) else 100.0
        shown = group[group["time"] <= horizon]
        x, marks = thin(shown["time"], shown["mark"], max_points=2500)
        axis.scatter(
            x, marks, s=5, color=PALETTE[index], alpha=0.55, edgecolors="none", rasterized=True
        )
        axis.set_yticks([0, 1], labels=["Buy", "Sell"])
        axis.set_title(scenario.replace("_", " "), loc="left")
        axis.set_xlabel("Time")
    _figure_title(
        figure,
        "Hawkes event raster",
        "First 100 time units (or available horizon); buy/sell event grain",
    )
    return figure


def plot_hawkes_counts(frame: pd.DataFrame) -> Figure:
    scenarios = list(frame["scenario"].drop_duplicates())
    figure, axes = _axes(len(scenarios))
    for index, (axis, scenario) in enumerate(zip(axes, scenarios, strict=True)):
        group = frame[frame["scenario"] == scenario]
        x, y = thin(group["time"], group["event_count"])
        axis.plot(x, y, color=PALETTE[index])
        axis.set_title(scenario.replace("_", " "), loc="left")
        axis.set_xlabel("Time")
        axis.set_ylabel("Events per bin")
    _figure_title(
        figure,
        "Binned event counts",
        "Equal-width bins; same target long-run rate",
    )
    return figure


def plot_hawkes_intensity(frame: pd.DataFrame) -> Figure:
    scenarios = list(frame["scenario"].drop_duplicates())
    figure, axes = _axes(len(scenarios))
    for index, (axis, scenario) in enumerate(zip(axes, scenarios, strict=True)):
        group = frame[frame["scenario"] == scenario]
        x, y = thin(group["time"], group["total_intensity"])
        axis.plot(x, y, color=PALETTE[index])
        axis.set_title(scenario.replace("_", " "), loc="left")
        axis.set_xlabel("Time")
        axis.set_ylabel("Total intensity")
    _figure_title(
        figure,
        "Conditional Hawkes intensity",
        "Buy + sell intensity reconstructed after simulation",
    )
    return figure


def plot_hawkes_price_rv(frame: pd.DataFrame) -> Figure:
    scenarios = list(frame["scenario"].drop_duplicates())
    figure, axes_grid = plt.subplots(
        2,
        len(scenarios),
        figsize=(4.0 * len(scenarios), 6.0),
        constrained_layout=True,
        squeeze=False,
    )
    for index, scenario in enumerate(scenarios):
        group = frame[frame["scenario"] == scenario]
        x, price = thin(group["time"], group["price"])
        axes_grid[0, index].plot(x, price, color=PALETTE[index])
        axes_grid[0, index].set_title(scenario.replace("_", " "), loc="left")
        axes_grid[0, index].set_ylabel("Price")
        valid = group.dropna(subset=["rolling_rv"])
        x_rv, rv = thin(valid["time"], valid["rolling_rv"])
        axes_grid[1, index].plot(x_rv, rv, color=PALETTE[index])
        axes_grid[1, index].set_title("rolling RV proxy", loc="left")
        axes_grid[1, index].set_xlabel("Time")
        axes_grid[1, index].set_ylabel("Rolling RV")
    _figure_title(
        figure,
        "Signed-event price and realized-variance proxy",
        "Pedagogical construction; the effective H is an empirical diagnostic only",
    )
    return figure


def plot_noise_bias(frame: pd.DataFrame) -> Figure:
    estimator = (
        "variogram" if "variogram" in set(frame["estimator"]) else frame["estimator"].iloc[0]
    )
    data = frame[frame["estimator"] == estimator]
    modes = list(data["mode"].drop_duplicates())
    figure, axes = _axes(len(modes))
    maximum = max(float(data["bias"].abs().max()), 0.05)
    for axis, mode in zip(axes, modes, strict=True):
        subset = data[data["mode"] == mode]
        pivot = subset.pivot(index="noise_std", columns="stride", values="bias")
        image = axis.imshow(
            pivot.to_numpy(),
            aspect="auto",
            origin="lower",
            cmap="coolwarm",
            vmin=-maximum,
            vmax=maximum,
        )
        axis.set_xticks(
            np.arange(len(pivot.columns)), labels=[str(value) for value in pivot.columns]
        )
        axis.set_yticks(np.arange(len(pivot.index)), labels=[f"{value:g}" for value in pivot.index])
        axis.set_title(mode, loc="left")
        axis.set_xlabel("Sampling stride")
        axis.set_ylabel("Noise standard deviation")
        figure.colorbar(image, ax=axis, label="Bias", shrink=0.8)
    _figure_title(
        figure,
        "H-estimation bias",
        f"{estimator} estimator; estimate minus known latent H",
    )
    return figure


def generate_static_figures(
    config: ProjectConfig,
    root: str | Path,
    manifest: dict[str, Path],
) -> list[Path]:
    """Read validated artifacts and export every chart contract to PNG/SVG."""
    apply_style()
    output_dir = Path(root).resolve() / config.output.artifacts_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = {
        key: pd.read_csv(manifest[key])
        for key in (
            "fbm_paths",
            "fbm_increments",
            "fbm_acf",
            "fbm_structure",
            "hurst_recovery",
            "hurst_summary",
            "ou_paths",
            "ou_diagnostics",
            "model_paths",
            "terminal_distributions",
            "leverage_data",
            "option_surface",
            "skew_term_structure",
            "skew_power_law",
            "hawkes_events",
            "hawkes_series",
            "hawkes_intensity",
            "noise_fragility",
        )
    }
    builders: dict[str, Callable[[], Figure]] = {
        "fbm_paths": lambda: plot_fbm_paths(frames["fbm_paths"]),
        "fbm_zoom": lambda: plot_fbm_zoom(frames["fbm_paths"]),
        "fgn_increments": lambda: plot_fgn_increments(frames["fbm_increments"]),
        "increment_acf": lambda: plot_increment_acf(frames["fbm_acf"]),
        "structure_scaling": lambda: plot_structure_scaling(frames["fbm_structure"]),
        "hurst_distributions": lambda: plot_hurst_distributions(frames["hurst_recovery"]),
        "hurst_bias": lambda: plot_hurst_bias(frames["hurst_summary"]),
        "ou_vs_fou": lambda: plot_ou_vs_fou(frames["ou_paths"]),
        "ou_volatility": lambda: plot_ou_volatility(frames["ou_paths"]),
        "ou_acf": lambda: plot_ou_acf(frames["ou_diagnostics"]),
        "model_spot": lambda: plot_model_spot(frames["model_paths"]),
        "model_variance": lambda: plot_model_variance(frames["model_paths"]),
        "terminal_returns": lambda: plot_terminal_returns(frames["terminal_distributions"]),
        "realized_variance": lambda: plot_realized_variance(frames["terminal_distributions"]),
        "leverage": lambda: plot_leverage(frames["leverage_data"]),
        "iv_smiles": lambda: plot_iv_smiles(frames["option_surface"]),
        "iv_surface": lambda: plot_iv_surface(frames["option_surface"]),
        "skew_term": lambda: plot_skew_term(frames["skew_term_structure"]),
        "skew_scaling": lambda: plot_skew_scaling(
            frames["skew_term_structure"], frames["skew_power_law"]
        ),
        "hawkes_events": lambda: plot_hawkes_events(frames["hawkes_events"]),
        "hawkes_counts": lambda: plot_hawkes_counts(frames["hawkes_series"]),
        "hawkes_intensity": lambda: plot_hawkes_intensity(frames["hawkes_intensity"]),
        "hawkes_price_rv": lambda: plot_hawkes_price_rv(frames["hawkes_series"]),
        "noise_bias": lambda: plot_noise_bias(frames["noise_fragility"]),
    }
    if set(builders) != set(CHART_CONTRACTS):
        raise RuntimeError("static figure registry and chart contracts are out of sync")
    exported: list[Path] = []
    for name, builder in builders.items():
        figure = builder()
        exported.extend(save_figure(figure, output_dir / name))
        plt.close(figure)
    return exported
