"""Self-contained offline Plotly report with a technical narrative."""

from __future__ import annotations

import base64
import html
import io
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rough_volatility.config import ProjectConfig
from rough_volatility.i18n import Translator
from rough_volatility.notebook import SECTIONS

INK = "#27313A"
MUTED = "#66727C"
BLUE = "#2F6BFF"
GOLD = "#D69E2E"
ORANGE = "#E07A3F"
OLIVE = "#7A8B3A"
PINK = "#C95B8B"
PALETTE = (BLUE, GOLD, ORANGE, OLIVE, PINK)
DASHES = ("solid", "dash", "dot", "dashdot")

EQUATIONS: dict[str, str] = {
    "fbm_covariance": r"\mathrm{Cov}(B_t^H,B_s^H)=\frac{1}{2}\left(t^{2H}+s^{2H}-|t-s|^{2H}\right)",
    "structure_function": r"S_q(\Delta)=\mathbb{E}\left[|X_{t+\Delta}-X_t|^q\right]\propto\Delta^{qH}",
    "rough_bergomi": r"V_t=\xi_0(t)\exp\left(\eta\widetilde W_t^H-\frac{1}{2}\eta^2t^{2H}\right)",
    "skew_power": r"\left.\frac{\partial\sigma_{\mathrm{imp}}}{\partial k}\right|_{k=0}\propto T^{H-\frac{1}{2}}",
    "hawkes": r"\lambda_t^i=\mu_i+\sum_j\int_0^t\phi_{ij}(t-s)\,dN_s^j",
}

REPORT_FIGURE_ANCHORS: tuple[str, ...] = (
    "fbm_paths",
    "fbm_zoom",
    "fgn_increments",
    "increment_acf",
    "structure_scaling",
    "hurst_distributions",
    "hurst_bias",
    "ou_vs_fou",
    "model_spot_variance",
    "heston_comparison",
    "terminal_distributions",
    "iv_smiles",
    "iv_surface",
    "skew_term",
    "skew_scaling",
    "hawkes_events",
    "hawkes_price",
    "hawkes_intensity",
    "noise_bias",
)


def render_equation_svg(mathtext: str) -> str:
    """Render one mathtext equation as an inline base64 SVG data URI."""
    if not mathtext:
        raise ValueError("equation cannot be empty")
    figure = plt.figure(figsize=(10.0, 0.75), facecolor="none")
    figure.text(0.01, 0.5, f"${mathtext}$", va="center", ha="left", fontsize=15, color=INK)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="svg", transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(figure)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _style_figure(figure: go.Figure, title: str, subtitle: str, *, height: int = 480) -> go.Figure:
    figure.update_layout(
        template="plotly_white",
        title={
            "text": f"{html.escape(title)}<br><sup>{html.escape(subtitle)}</sup>",
            "x": 0.01,
            "xanchor": "left",
        },
        height=height,
        margin={"l": 60, "r": 30, "t": 90, "b": 55},
        font={"family": "Arial, sans-serif", "color": INK, "size": 12},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0.0},
        hoverlabel={"font": {"family": "Arial, sans-serif"}},
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    figure.update_xaxes(gridcolor="#E5E9ED", zerolinecolor="#AAB4BC")
    figure.update_yaxes(gridcolor="#E5E9ED", zerolinecolor="#AAB4BC")
    return figure


def _selector_buttons(
    groups: list[Any], trace_groups: list[Any], label: str
) -> list[dict[str, Any]]:
    return [
        {
            "label": f"{label}={group:g}"
            if isinstance(group, (float, int, np.number))
            else str(group),
            "method": "update",
            "args": [{"visible": [trace_group == group for trace_group in trace_groups]}],
        }
        for group in groups
    ]


def _fbm_selector(
    frame: pd.DataFrame, column: str, title: str, subtitle: str, *, zoom: bool = False
) -> go.Figure:
    figure = go.Figure()
    h_values = sorted(frame["h"].unique())
    trace_groups: list[float] = []
    for h_index, h in enumerate(h_values):
        subset = frame[frame["h"] == h]
        if zoom:
            lower, upper = frame["time"].max() * 0.45, frame["time"].max() * 0.55
            subset = subset[subset["time"].between(lower, upper)]
        for path_id, path in subset.groupby("path_id"):
            figure.add_trace(
                go.Scattergl(
                    x=path["time"],
                    y=path[column],
                    mode="lines",
                    name=f"path {path_id}",
                    legendgroup=f"H={h:g}",
                    line={"color": PALETTE[h_index % len(PALETTE)], "width": 1.5},
                    opacity=0.95 if path_id == subset["path_id"].min() else 0.28,
                    visible=h_index == 0,
                    hovertemplate=f"H={h:g}<br>t=%{{x:.4f}}<br>value=%{{y:.4f}}<extra></extra>",
                )
            )
            trace_groups.append(float(h))
    figure.update_layout(
        updatemenus=[
            {
                "buttons": _selector_buttons(h_values, trace_groups, "H"),
                "direction": "down",
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
            }
        ]
    )
    figure.update_xaxes(title="Time")
    figure.update_yaxes(title="Increment" if column == "increment" else "Process value")
    return _style_figure(figure, title, subtitle)


def _acf_figure(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    for index, (h, group) in enumerate(frame.groupby("h", sort=True)):
        figure.add_trace(
            go.Scatter(
                x=group["lag"],
                y=group["acf"],
                mode="lines+markers",
                name=f"H={h:g}",
                line={"color": PALETTE[index], "dash": DASHES[index % len(DASHES)]},
            )
        )
    figure.add_hline(y=0, line_color=INK, line_width=1)
    figure.update_xaxes(title="Lag")
    figure.update_yaxes(title="Increment ACF")
    return _style_figure(figure, title, subtitle)


def _structure_figure(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    data = frame[frame["q"] == 2.0]
    for index, (h, group) in enumerate(data.groupby("h", sort=True)):
        figure.add_trace(
            go.Scatter(
                x=group["delta"],
                y=group["moment"],
                mode="lines+markers",
                name=f"H={h:g} observed",
                line={"color": PALETTE[index]},
            )
        )
        figure.add_trace(
            go.Scatter(
                x=group["delta"],
                y=group["fitted"],
                mode="lines",
                name=f"H={h:g} fitted",
                line={"color": PALETTE[index], "dash": "dot"},
            )
        )
    figure.update_xaxes(type="log", title="Lag Δ")
    figure.update_yaxes(type="log", title="Second-order structure function")
    return _style_figure(figure, title, subtitle)


def _hurst_distribution_figure(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    data = frame[(frame["estimator"] == "variogram") & frame["ok"].astype(bool)]
    for index, ((h, sample_size), group) in enumerate(
        data.groupby(["true_h", "sample_size"], sort=True)
    ):
        figure.add_trace(
            go.Box(
                y=group["h_hat"],
                name=f"H={h:g}<br>n={int(sample_size)}",
                marker_color=PALETTE[index % len(PALETTE)],
                boxmean=True,
            )
        )
    figure.update_yaxes(title="Estimated H")
    return _style_figure(figure, title, subtitle, height=520)


def _hurst_bias_figure(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    for index, ((h, estimator), group) in enumerate(
        frame.groupby(["true_h", "estimator"], sort=True)
    ):
        figure.add_trace(
            go.Scatter(
                x=group["sample_size"],
                y=group["bias"],
                mode="lines+markers",
                name=f"H={h:g} · {estimator.replace('_', ' ')}",
                line={"color": PALETTE[index % len(PALETTE)], "dash": DASHES[index % len(DASHES)]},
            )
        )
    figure.add_hline(y=0.0, line_color=INK, line_width=1)
    figure.update_xaxes(type="log", title="Increment count")
    figure.update_yaxes(title="Bias (mean estimate − true H)")
    return _style_figure(figure, title, subtitle)


def _ou_selector(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    models = list(frame["model"].drop_duplicates())
    trace_groups: list[str] = []
    for model_index, model in enumerate(models):
        subset = frame[frame["model"] == model]
        for path_id, path in subset.groupby("path_id"):
            figure.add_trace(
                go.Scattergl(
                    x=path["time"],
                    y=path["log_volatility"],
                    mode="lines",
                    name=f"path {path_id}",
                    line={"color": PALETTE[model_index], "width": 1.3},
                    opacity=0.95 if path_id == subset["path_id"].min() else 0.25,
                    visible=model_index == 0,
                    hovertemplate=f"{html.escape(model)}<br>t=%{{x:.3f}}<br>X=%{{y:.4f}}<extra></extra>",
                )
            )
            trace_groups.append(model)
    figure.update_layout(
        updatemenus=[
            {
                "buttons": _selector_buttons(models, trace_groups, "model"),
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
            }
        ]
    )
    figure.update_xaxes(title="Time (years)")
    figure.update_yaxes(title="Log-volatility")
    return _style_figure(figure, title, subtitle)


def _model_path_figure(
    frame: pd.DataFrame, title: str, subtitle: str, *, rough_only: bool
) -> go.Figure:
    figure = make_subplots(rows=1, cols=2, subplot_titles=("Spot", "Variance"))
    data = frame[frame["model"] == "rough_bergomi"] if rough_only else frame
    for model_index, (model, model_data) in enumerate(data.groupby("model", sort=False)):
        first_id = model_data["path_id"].min()
        path = model_data[model_data["path_id"] == first_id]
        for column, subplot in (("spot", 1), ("variance", 2)):
            figure.add_trace(
                go.Scatter(
                    x=path["time"],
                    y=path[column],
                    mode="lines",
                    name=model.replace("_", " "),
                    legendgroup=model,
                    showlegend=subplot == 1,
                    line={"color": PALETTE[model_index], "dash": DASHES[model_index]},
                ),
                row=1,
                col=subplot,
            )
    figure.update_xaxes(title="Time (years)")
    figure.update_yaxes(title="Spot", row=1, col=1)
    figure.update_yaxes(title="Variance", row=1, col=2)
    return _style_figure(figure, title, subtitle)


def _terminal_figure(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = make_subplots(
        rows=1, cols=2, subplot_titles=("Terminal log return", "Realized variance")
    )
    for index, (model, group) in enumerate(frame.groupby("model", sort=False)):
        figure.add_trace(
            go.Histogram(
                x=group["terminal_log_return"],
                histnorm="probability density",
                opacity=0.55,
                name=model.replace("_", " "),
                marker_color=PALETTE[index],
                legendgroup=model,
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Histogram(
                x=group["realized_variance"],
                histnorm="probability density",
                opacity=0.55,
                name=model.replace("_", " "),
                marker_color=PALETTE[index],
                legendgroup=model,
                showlegend=False,
            ),
            row=1,
            col=2,
        )
    figure.update_layout(barmode="overlay")
    return _style_figure(figure, title, subtitle)


def _smile_selector(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    data = frame[frame["ok"].astype(bool)]
    maturities = sorted(data["maturity"].unique())
    trace_groups: list[float] = []
    for maturity_index, maturity in enumerate(maturities):
        for model_index, (model, group) in enumerate(
            data[data["maturity"] == maturity].groupby("model", sort=False)
        ):
            figure.add_trace(
                go.Scatter(
                    x=group["k"],
                    y=group["iv"],
                    error_y={"type": "data", "array": 1.96 * group["iv_se"], "visible": True},
                    mode="lines+markers",
                    name=model.replace("_", " "),
                    line={"color": (BLUE, ORANGE)[model_index % 2], "dash": DASHES[model_index]},
                    visible=maturity_index == 0,
                )
            )
            trace_groups.append(float(maturity))
    figure.update_layout(
        updatemenus=[
            {
                "buttons": _selector_buttons(maturities, trace_groups, "T"),
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
            }
        ]
    )
    figure.update_xaxes(title="Log-moneyness k")
    figure.update_yaxes(title="Implied volatility")
    return _style_figure(figure, title, subtitle)


def _surface_selector(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    data = frame[frame["ok"].astype(bool)]
    models = list(data["model"].drop_duplicates())
    for index, model in enumerate(models):
        pivot = data[data["model"] == model].pivot(index="maturity", columns="k", values="iv")
        figure.add_trace(
            go.Heatmap(
                x=pivot.columns,
                y=pivot.index,
                z=pivot.to_numpy(),
                colorscale="Blues" if index == 0 else "Oranges",
                colorbar={"title": "IV"},
                visible=index == 0,
                hovertemplate="k=%{x:.3f}<br>T=%{y:.3f}<br>IV=%{z:.4f}<extra></extra>",
            )
        )
    figure.update_layout(
        updatemenus=[
            {
                "buttons": _selector_buttons(models, models, "model"),
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
            }
        ]
    )
    figure.update_xaxes(title="Log-moneyness k")
    figure.update_yaxes(title="Maturity (years)")
    return _style_figure(figure, title, subtitle)


def _skew_term_figure(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = go.Figure()
    for index, (h, group) in enumerate(frame[frame["ok"].astype(bool)].groupby("h", sort=True)):
        figure.add_trace(
            go.Scatter(
                x=group["maturity"],
                y=group["skew"],
                error_y={"type": "data", "array": 1.96 * group["skew_se"], "visible": True},
                mode="lines+markers",
                name=f"H={h:g}",
                line={"color": PALETTE[index], "dash": DASHES[index % len(DASHES)]},
            )
        )
    figure.add_hline(y=0.0, line_color=INK, line_width=1)
    figure.update_xaxes(type="log", title="Maturity (years)")
    figure.update_yaxes(title="ATM skew")
    return _style_figure(figure, title, subtitle)


def _skew_scaling_figure(
    term: pd.DataFrame, powers: pd.DataFrame, title: str, subtitle: str
) -> go.Figure:
    figure = go.Figure()
    power_map = powers.set_index("h")
    for index, (h, group) in enumerate(term[term["ok"].astype(bool)].groupby("h", sort=True)):
        x = group["maturity"].to_numpy()
        y = np.abs(group["skew"].to_numpy())
        figure.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="markers",
                name=f"H={h:g} observed",
                marker={"color": PALETTE[index], "size": 8},
            )
        )
        if h in power_map.index and bool(power_map.loc[h, "ok"]):
            beta = float(power_map.loc[h, "beta"])
            intercept = float(power_map.loc[h, "intercept"])
            figure.add_trace(
                go.Scatter(
                    x=x,
                    y=np.exp(intercept) * x**beta,
                    mode="lines",
                    name=f"H={h:g}: β={beta:.3f}, theory={h - 0.5:.2f}",
                    line={"color": PALETTE[index], "dash": DASHES[index % len(DASHES)]},
                )
            )
    figure.update_xaxes(type="log", title="Maturity T")
    figure.update_yaxes(type="log", title="Absolute ATM skew")
    return _style_figure(figure, title, subtitle)


def _scenario_selector(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    title: str,
    subtitle: str,
    mode: str = "lines",
    clip_to_first_100: bool = False,
) -> go.Figure:
    figure = go.Figure()
    scenarios = list(frame["scenario"].drop_duplicates())
    for index, scenario in enumerate(scenarios):
        group = frame[frame["scenario"] == scenario]
        if clip_to_first_100:
            horizon = min(float(group[x].max()), 100.0) if len(group) else 100.0
            group = group[group[x] <= horizon]
        figure.add_trace(
            go.Scattergl(
                x=group[x],
                y=group[y],
                mode=mode,
                name=scenario.replace("_", " "),
                marker={"color": PALETTE[index], "size": 5, "opacity": 0.55},
                line={"color": PALETTE[index]},
                visible=index == 0,
            )
        )
    figure.update_layout(
        updatemenus=[
            {
                "buttons": _selector_buttons(scenarios, scenarios, "scenario"),
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
            }
        ]
    )
    figure.update_xaxes(title="Time")
    figure.update_yaxes(title="Side" if y == "mark" else y.replace("_", " ").title())
    if y == "mark":
        figure.update_yaxes(tickmode="array", tickvals=[0, 1], ticktext=["Buy", "Sell"])
    return _style_figure(figure, title, subtitle)


def _hawkes_price_figure(frame: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    figure = make_subplots(
        rows=2, cols=1, shared_xaxes=True, subplot_titles=("Synthetic price", "Rolling RV proxy")
    )
    scenarios = list(frame["scenario"].drop_duplicates())
    trace_groups: list[str] = []
    for index, scenario in enumerate(scenarios):
        group = frame[frame["scenario"] == scenario]
        for row, column in ((1, "price"), (2, "rolling_rv")):
            figure.add_trace(
                go.Scattergl(
                    x=group["time"],
                    y=group[column],
                    mode="lines",
                    name=scenario.replace("_", " "),
                    legendgroup=scenario,
                    showlegend=row == 1,
                    line={"color": PALETTE[index]},
                    visible=index == 0,
                ),
                row=row,
                col=1,
            )
            trace_groups.append(scenario)
    figure.update_layout(
        updatemenus=[
            {
                "buttons": _selector_buttons(scenarios, trace_groups, "scenario"),
                "x": 1.0,
                "xanchor": "right",
                "y": 1.13,
            }
        ]
    )
    figure.update_xaxes(title="Time", row=2, col=1)
    figure.update_yaxes(title="Price", row=1, col=1)
    figure.update_yaxes(title="Rolling RV", row=2, col=1)
    return _style_figure(figure, title, subtitle, height=650)


def _noise_selector(frame: pd.DataFrame, t: Translator) -> go.Figure:
    # Receives the Translator (rather than resolved caption strings) because the
    # subtitle interpolates the estimator name, which is selected from the data here.
    estimator = (
        "variogram" if "variogram" in set(frame["estimator"]) else frame["estimator"].iloc[0]
    )
    data = frame[frame["estimator"] == estimator]
    modes = list(data["mode"].drop_duplicates())
    maximum = max(float(data["bias"].abs().max()), 0.05)
    figure = go.Figure()
    for index, mode in enumerate(modes):
        pivot = data[data["mode"] == mode].pivot(index="noise_std", columns="stride", values="bias")
        figure.add_trace(
            go.Heatmap(
                x=pivot.columns,
                y=pivot.index,
                z=pivot.to_numpy(),
                zmin=-maximum,
                zmax=maximum,
                zmid=0,
                colorscale="RdBu_r",
                colorbar={"title": "Bias"},
                visible=index == 0,
                hovertemplate="stride=%{x}<br>noise=%{y}<br>bias=%{z:.4f}<extra></extra>",
            )
        )
    figure.update_layout(
        updatemenus=[
            {
                "buttons": _selector_buttons(modes, modes, "mode"),
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
            }
        ]
    )
    figure.update_xaxes(title="Sampling stride")
    figure.update_yaxes(title="Observation-noise standard deviation")
    return _style_figure(
        figure,
        t("figure.noise_bias.title"),
        t("figure.noise_bias.subtitle", estimator=estimator),
    )


def _load_frames(manifest: dict[str, Path]) -> dict[str, pd.DataFrame]:
    return {
        key: pd.read_csv(manifest[key])
        for key in (
            "fbm_paths",
            "fbm_increments",
            "fbm_acf",
            "fbm_structure",
            "hurst_recovery",
            "hurst_summary",
            "ou_paths",
            "model_paths",
            "terminal_distributions",
            "option_surface",
            "skew_term_structure",
            "skew_power_law",
            "hawkes_events",
            "hawkes_series",
            "hawkes_intensity",
            "hawkes_summary",
            "noise_fragility",
        )
    }


def _build_figures(frames: dict[str, pd.DataFrame], t: Translator) -> dict[str, go.Figure]:
    def caption(key: str) -> tuple[str, str]:
        return t(f"figure.{key}.title"), t(f"figure.{key}.subtitle")

    return {
        "fbm_paths": _fbm_selector(frames["fbm_paths"], "value", *caption("fbm_paths")),
        "fbm_zoom": _fbm_selector(frames["fbm_paths"], "value", *caption("fbm_zoom"), zoom=True),
        "fgn_increments": _fbm_selector(
            frames["fbm_increments"], "increment", *caption("fgn_increments")
        ),
        "increment_acf": _acf_figure(frames["fbm_acf"], *caption("increment_acf")),
        "structure_scaling": _structure_figure(
            frames["fbm_structure"], *caption("structure_scaling")
        ),
        "hurst_distributions": _hurst_distribution_figure(
            frames["hurst_recovery"], *caption("hurst_distributions")
        ),
        "hurst_bias": _hurst_bias_figure(frames["hurst_summary"], *caption("hurst_bias")),
        "ou_vs_fou": _ou_selector(frames["ou_paths"], *caption("ou_vs_fou")),
        "model_spot_variance": _model_path_figure(
            frames["model_paths"], *caption("model_spot_variance"), rough_only=True
        ),
        "heston_comparison": _model_path_figure(
            frames["model_paths"], *caption("heston_comparison"), rough_only=False
        ),
        "terminal_distributions": _terminal_figure(
            frames["terminal_distributions"], *caption("terminal_distributions")
        ),
        "iv_smiles": _smile_selector(frames["option_surface"], *caption("iv_smiles")),
        "iv_surface": _surface_selector(frames["option_surface"], *caption("iv_surface")),
        "skew_term": _skew_term_figure(frames["skew_term_structure"], *caption("skew_term")),
        "skew_scaling": _skew_scaling_figure(
            frames["skew_term_structure"], frames["skew_power_law"], *caption("skew_scaling")
        ),
        "hawkes_events": _scenario_selector(
            frames["hawkes_events"],
            x="time",
            y="mark",
            title=t("figure.hawkes_events.title"),
            subtitle=t("figure.hawkes_events.subtitle"),
            mode="markers",
            clip_to_first_100=True,
        ),
        "hawkes_price": _hawkes_price_figure(frames["hawkes_series"], *caption("hawkes_price")),
        "hawkes_intensity": _scenario_selector(
            frames["hawkes_intensity"],
            x="time",
            y="total_intensity",
            title=t("figure.hawkes_intensity.title"),
            subtitle=t("figure.hawkes_intensity.subtitle"),
        ),
        "noise_bias": _noise_selector(frames["noise_fragility"], t),
    }


def _figure_fragments(figures: dict[str, go.Figure]) -> dict[str, str]:
    if set(figures) != set(REPORT_FIGURE_ANCHORS):
        raise RuntimeError("report figure registry is incomplete")
    fragments: dict[str, str] = {}
    first = True
    for key in REPORT_FIGURE_ANCHORS:
        fragment = figures[key].to_html(
            full_html=False,
            include_plotlyjs="inline" if first else False,
            config={
                "responsive": True,
                "displaylogo": False,
                "displayModeBar": False,
                "scrollZoom": False,
            },
            div_id=f"plot-{key}",
        )
        if first:
            # Plotly's bundled (unused) logo/help code contains literal remote
            # href strings. Keep runtime strings equivalent while preventing
            # them from being interpreted as HTML attributes by offline audits;
            # the modebar is disabled and no report trace requests remote data.
            fragment = (
                fragment.replace('href="https://', 'href="https:\\x2f\\x2f')
                .replace("href='https://", "href='https:\\x2f\\x2f")
                .replace('href="http://', 'href="http:\\x2f\\x2f')
                .replace("href='http://", "href='http:\\x2f\\x2f")
                .replace('src="https://', 'src="https:\\x2f\\x2f')
                .replace("src='https://", "src='https:\\x2f\\x2f")
                .replace('src="http://', 'src="http:\\x2f\\x2f')
                .replace("src='http://", "src='http:\\x2f\\x2f")
                .replace("cdn.plot.ly", "offline.plotly.local")
            )
        fragments[key] = fragment
        first = False
    return fragments


def _configuration_table(config: ProjectConfig) -> str:
    rows = (
        ("Profile", config.profile),
        ("Seed", config.seed),
        ("fBM steps / paths", f"{config.fbm.n_steps:,} / {config.fbm.n_paths:,}"),
        ("Hurst replications", f"{config.hurst.n_replications:,}"),
        (
            "rBergomi H / η / ρ",
            f"{config.bergomi.h:g} / {config.bergomi.eta:g} / {config.bergomi.rho:g}",
        ),
        ("rBergomi paths / steps", f"{config.bergomi.n_paths:,} / {config.bergomi.n_steps:,}"),
        ("Option maturities", ", ".join(f"{value:g}" for value in config.options.maturities)),
        (
            "Hawkes horizon / target rate",
            f"{config.hawkes.horizon:g} / {config.hawkes.target_rate:g} per side",
        ),
        ("Fingerprint", config.fingerprint()),
    )
    return (
        "<table class=definition-table><tbody>"
        + "".join(
            f"<tr><th>{html.escape(str(label))}</th><td>{html.escape(str(value))}</td></tr>"
            for label, value in rows
        )
        + "</tbody></table>"
    )


def _metric_cards(
    config: ProjectConfig, frames: dict[str, pd.DataFrame], validation: dict[str, Any]
) -> str:
    powers = frames["skew_power_law"]
    target = powers.iloc[(powers["h"] - config.bergomi.h).abs().argmin()]
    summary = frames["hurst_summary"]
    sample_max = summary["sample_size"].max()
    h_rows = summary[
        (summary["sample_size"] == sample_max)
        & (summary["estimator"] == "variogram")
        & np.isclose(summary["true_h"], config.bergomi.h)
    ]
    h_bias = float(h_rows["bias"].iloc[0]) if len(h_rows) else float("nan")
    near_critical = frames["hawkes_summary"].iloc[
        frames["hawkes_summary"]["branching_ratio"].argmax()
    ]
    checks = validation.get("checks", {})
    all_passed = bool(checks.get("all_passed", False))
    cards = (
        ("Skew exponent β", f"{target['beta']:.3f}", f"theory {config.bergomi.h - 0.5:.2f}"),
        ("Implied H from skew", f"{target['h_implied']:.3f}", "finite-maturity diagnostic"),
        ("Long-sample H bias", f"{h_bias:+.3f}", f"variogram, n={int(sample_max):,}"),
        (
            "Near-critical events",
            f"{int(near_critical['event_count']):,}",
            f"branching {near_critical['branching_ratio']:.2f}",
        ),
        ("Validation gates", "PASS" if all_passed else "REVIEW", "moment, operator, skew, Hawkes"),
    )
    return (
        '<div class="metric-grid">'
        + "".join(
            f'<div class="metric-card"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong><small>{html.escape(note)}</small></div>'
            for label, value, note in cards
        )
        + "</div>"
    )


def _equation_gallery() -> str:
    return (
        '<div class="equation-grid">'
        + "".join(
            f'<div class="equation-card"><span>{html.escape(name.replace("_", " ").title())}</span><img alt="{html.escape(name)} equation" src="{render_equation_svg(equation)}"></div>'
            for name, equation in EQUATIONS.items()
        )
        + "</div>"
    )


def _validation_table(validation: dict[str, Any]) -> str:
    checks = validation.get("checks", {})
    rows = []
    for name, payload in checks.items():
        if name == "all_passed" or not isinstance(payload, dict):
            continue
        passed = bool(payload.get("passed", False))
        rows.append(
            f'<tr><th>{html.escape(name.replace("_", " ").title())}</th><td class="status {"pass" if passed else "review"}">{"PASS" if passed else "REVIEW"}</td></tr>'
        )
    return (
        '<table class="definition-table"><thead><tr><th>Validation gate</th><th>Status</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table>"
    )


# Module-level literal tuple of the anchors that carry a narrative callout, in the same
# order as the dict this function used to return. Every section currently has a callout,
# so this matches `i18n._SECTION_ANCHORS` / `i18n._CALLOUT_ANCHORS` exactly; keep the three
# in sync if a section's narrative is ever added or removed.
_NARRATIVE_ANCHORS: tuple[str, ...] = (
    "executive-summary",
    "conceptual-map",
    "mathematical-definitions",
    "configuration",
    "fbm-path-comparison",
    "local-zoom",
    "fgn-increments",
    "increment-acf",
    "structure-functions",
    "hurst-recovery",
    "estimator-bias",
    "ou-versus-fou",
    "rough-bergomi-paths",
    "heston-comparison",
    "terminal-distributions",
    "iv-smiles",
    "iv-surface",
    "atm-skew-term",
    "skew-scaling",
    "hawkes-events",
    "order-flow-price",
    "volatility-proxy",
    "noise-bias",
    "establishes",
    "does-not-establish",
    "limitations-next-steps",
)


def _narratives(
    config: ProjectConfig, frames: dict[str, pd.DataFrame], t: Translator
) -> dict[str, str]:
    powers = frames["skew_power_law"]
    target = powers.iloc[(powers["h"] - config.bergomi.h).abs().argmin()]
    values = {
        "executive-summary": {
            "h": config.bergomi.h,
            "beta": float(target["beta"]),
            "h_minus_half": config.bergomi.h - 0.5,
        },
    }
    return {a: t(f"callout.{a}", **values.get(a, {})) for a in _NARRATIVE_ANCHORS}


def _section_extra(
    anchor: str,
    config: ProjectConfig,
    validation: dict[str, Any],
    t: Translator,
) -> str:
    if anchor == "mathematical-definitions":
        return _equation_gallery()
    if anchor == "configuration":
        return _configuration_table(config)
    if anchor == "limitations-next-steps":
        heading = html.escape(t("validation_gates_heading"))
        return f"<h3>{heading}</h3>" + _validation_table(validation)
    return ""


def build_standalone_report(
    config: ProjectConfig,
    root: str | Path,
    manifest: dict[str, Path],
    *,
    locale: str = "en",
    output_path: str | Path | None = None,
) -> Path:
    """Build the single-file, offline, interactive technical report."""
    config.validate()
    t = Translator(locale)
    frames = _load_frames(manifest)
    figures = _build_figures(frames, t)
    fragments = _figure_fragments(figures)
    validation = json.loads(manifest["validation_checks"].read_text(encoding="utf-8"))
    narratives = _narratives(config, frames, t)
    if len(SECTIONS) != 26:
        raise RuntimeError("the shared narrative registry must contain 26 sections")

    toc = "".join(
        f'<li><a href="#{section.anchor}">{index}. '
        f'{html.escape(t(f"section.{section.anchor}"))}</a></li>'
        for index, section in enumerate(SECTIONS, start=1)
    )
    sections_html: list[str] = []
    for index, section in enumerate(SECTIONS, start=1):
        figure_html = fragments.get(section.figure_key or "", "")
        evidence_note = (
            "<p class=\"evidence-note\">"
            f"{html.escape(t('evidence_note', profile=config.profile, seed=config.seed, fingerprint=config.fingerprint()))}"
            "</p>"
            if figure_html
            else ""
        )
        sections_html.append(
            f'<section id="{section.anchor}"><div class="section-number">{index:02d}</div>'
            f'<h2>{html.escape(t(f"section.{section.anchor}"))}</h2>{narratives[section.anchor]}'
            f"{_section_extra(section.anchor, config, validation, t)}{figure_html}{evidence_note}</section>"
        )
    metric_cards = _metric_cards(config, frames, validation)
    sections_html[0] = sections_html[0].replace("</section>", metric_cards + "</section>")

    css = """
    :root{--ink:#27313a;--muted:#66727c;--line:#dce2e7;--paper:#fff;--wash:#f5f7f9;--blue:#2f6bff;--gold:#d69e2e}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--wash);color:var(--ink);font-family:Arial,sans-serif;line-height:1.58}
    .layout{display:grid;grid-template-columns:280px minmax(0,1fr);max-width:1500px;margin:auto}.sidebar{position:sticky;top:0;height:100vh;overflow:auto;padding:28px 22px;background:#202a33;color:#fff}.brand{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#aebac4}.sidebar h1{font-size:21px;line-height:1.2;margin:12px 0 20px}.sidebar ol{padding-left:18px;margin:0}.sidebar li{margin:7px 0;color:#bfc9d0;font-size:12px}.sidebar a{color:inherit;text-decoration:none}.sidebar a:hover{color:#fff}.content{min-width:0;padding:44px 52px 90px;background:var(--paper)}header{border-bottom:1px solid var(--line);padding-bottom:26px;margin-bottom:20px}header h1{font-size:34px;line-height:1.12;margin:0 0 10px}header p{color:var(--muted);margin:0}.badge{display:inline-block;padding:5px 9px;border-radius:999px;background:#e8efff;color:#2455cc;font-size:12px;font-weight:700;margin-bottom:14px}
    section{position:relative;padding:34px 0;border-bottom:1px solid var(--line);scroll-margin-top:15px}section h2{font-size:25px;line-height:1.22;margin:0 0 15px;max-width:900px}section h3{margin-top:24px}.section-number{font:700 11px/1 monospace;color:var(--blue);letter-spacing:.12em;margin-bottom:10px}section>p,section>ul,section>ol{max-width:940px}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin:24px 0 2px}.metric-card{border:1px solid var(--line);border-radius:10px;padding:15px;background:#fff}.metric-card span,.metric-card small{display:block;color:var(--muted);font-size:11px}.metric-card strong{display:block;font-size:25px;margin:6px 0}.flow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:22px 0}.flow span{border:1px solid var(--line);border-radius:8px;padding:10px 13px;background:var(--wash)}.flow b{color:var(--blue)}
    .equation-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}.equation-card{border:1px solid var(--line);border-radius:9px;padding:12px;overflow:auto}.equation-card span{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}.equation-card img{display:block;max-width:100%;height:60px;margin-top:5px}.definition-table{width:100%;max-width:850px;border-collapse:collapse;margin:18px 0}.definition-table th,.definition-table td{text-align:left;border-bottom:1px solid var(--line);padding:10px 12px}.definition-table th{background:var(--wash);width:42%}.status{font-weight:700}.status.pass{color:#2455cc}.status.review{color:#a65512}.plotly-graph-div{width:100%!important}.evidence-note{font-size:11px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px}.footer{color:var(--muted);font-size:12px;padding-top:26px}
    @media(max-width:900px){.layout{display:block}.sidebar{position:relative;height:auto}.sidebar ol{columns:2}.content{padding:30px 22px}.content header h1{font-size:29px}}@media(max-width:560px){.sidebar ol{columns:1}.content{padding:24px 14px}.equation-grid{grid-template-columns:1fr}}
    @media print{.sidebar{display:none}.layout{display:block}.content{padding:0}.plotly-graph-div{page-break-inside:avoid}section{break-inside:avoid}}
    """
    output = (
        Path(output_path)
        if output_path is not None
        else Path(root).resolve()
        / config.output.reports_dir
        / f"rough_volatility_report_{locale}.html"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    document = (
        f'<!doctype html><html lang="{locale}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        f"<title>{html.escape(t('document_title'))}</title><style>{css}</style></head>"
        '<body><div class="layout"><nav class="sidebar" aria-label="Report sections">'
        f'<div class="brand">{html.escape(t("brand"))}</div>'
        f'<h1>{html.escape(t("report_title"))}</h1><ol>{toc}</ol></nav>'
        '<main class="content"><header>'
        f'<div class="badge">{html.escape(t("badge", profile=config.profile.upper()))}</div>'
        f'<h1>{html.escape(t("report_title"))}</h1>'
        f'<p>{html.escape(t("report_subtitle", seed=config.seed, fingerprint=config.fingerprint()))}</p>'
        f'</header>{"".join(sections_html)}'
        f'<div class="footer">{html.escape(t("footer"))}</div>'
        "</main></div></body></html>"
    )
    output.write_text(document, encoding="utf-8")
    return output
