"""Artifact-backed Plotly figures for johnhull volumes 18--25."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

VOLUMES = Path(__file__).resolve().parents[2] / "volumes"


def _load(slug: str, filename: str) -> dict[str, np.ndarray]:
    with np.load(VOLUMES / slug / "reference" / filename, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def _metrics(slug: str) -> dict:
    return json.loads((VOLUMES / slug / "reference" / "metrics.json").read_text())["metrics"]


def _vol19_view() -> dict[str, np.ndarray]:
    data = _load("19_inverse_surfaces", "surfaces.npz")
    return {
        **data,
        "strike": data["constraint_strikes"],
        "clean_teacher_price": data["constraint_clean_teacher_price"],
        "raw_price": data["constraint_raw_price"],
        "hard_constrained_price": data["constraint_hard_price"],
        "start_index": np.arange(len(data["calibration_start_repricing_rmse"])),
        "start_parameter_rmse": np.sqrt(
            np.mean(
                (data["calibration_start_parameters"] - data["calibration_truth"][None, :]) ** 2,
                axis=1,
            )
        ),
        "start_repricing_rmse": data["calibration_start_repricing_rmse"],
        "pareto_lambda": data["pareto_lambdas"],
        "pareto_iv_rmse": np.sqrt(np.maximum(data["pareto_losses"][:, 1], 0.0)),
        "pareto_variance_rmse": np.sqrt(np.maximum(data["pareto_losses"][:, 2], 0.0)),
        "variance_maturity": data["teacher_maturities"],
        "target_variance": data["pareto_target_variance"],
        "iv_only_variance": data["pareto_predicted_variance"][0],
        "joint_variance": data["pareto_predicted_variance"][-1],
    }


def _vol20_view() -> dict[str, np.ndarray]:
    data = _load("20_surface_dynamics", "forecast_paths.npz")
    metrics = _metrics("20_surface_dynamics")
    model_order = ["persistence", "ewma", "har_ridge", "pca_ridge_challenger"]
    strategy_order = metrics["end_to_end"]["strategy_order"]
    return {
        **data,
        "test_row": data["walk_forward_test_row"],
        "actual_variance": data["walk_forward_actual"],
        "har_ridge_prediction": data["walk_forward_prediction_har_ridge"],
        "pca_ridge_prediction": data["walk_forward_prediction_challenger"],
        "model_names": np.asarray(model_order),
        "rmse": np.asarray(
            [metrics["walk_forward"]["models"][name]["rmse"] for name in model_order]
        ),
        "qlike": np.asarray(
            [metrics["walk_forward"]["models"][name]["qlike"] for name in model_order]
        ),
        "hedge_names": np.asarray(strategy_order),
        "hedge_pnl": data["e2e_hedge_pnl"],
        "cvar95": np.asarray(
            [metrics["end_to_end"]["strategy_metrics"][name]["cvar95"] for name in strategy_order]
        ),
        "turnover": np.asarray(
            [metrics["end_to_end"]["strategy_metrics"][name]["turnover"] for name in strategy_order]
        ),
    }


def _line(
    data: dict[str, np.ndarray],
    x: str,
    series: tuple[str, ...],
    title: str,
    *,
    log_y: bool = False,
) -> go.Figure:
    fig = go.Figure()
    for name in series:
        values = np.asarray(data[name])
        if values.ndim == 2:
            for row, row_values in enumerate(values):
                fig.add_trace(
                    go.Scatter(
                        x=data[x],
                        y=row_values,
                        mode="lines",
                        name=f"{name}[{row}]",
                        opacity=0.72,
                    )
                )
        else:
            fig.add_trace(go.Scatter(x=data[x], y=values, mode="lines+markers", name=name))
    fig.update_layout(title=title, yaxis_type="log" if log_y else "linear")
    return fig


def _bar(
    data: dict[str, np.ndarray], labels: str, series: tuple[str, ...], title: str
) -> go.Figure:
    fig = go.Figure()
    for name in series:
        fig.add_trace(go.Bar(x=data[labels].astype(str), y=data[name], name=name))
    fig.update_layout(title=title, barmode="group")
    return fig


def _heatmap(data: dict[str, np.ndarray], z: str, title: str) -> go.Figure:
    return go.Figure(go.Heatmap(z=data[z], colorscale="Magma")).update_layout(title=title)


def _hist(data: dict[str, np.ndarray], rows: str, labels: str, title: str) -> go.Figure:
    fig = go.Figure()
    for values, label in zip(data[rows], data[labels], strict=True):
        fig.add_trace(
            go.Histogram(x=values, name=str(label), histnorm="probability density", opacity=0.55)
        )
    fig.update_layout(title=title, barmode="overlay")
    return fig


def _vol18_price() -> go.Figure:
    return _heatmap(
        _load("18_ml_surrogates", "pricing_slices.npz"), "price_error", "Price MAE surface"
    )


def _vol18_greeks() -> go.Figure:
    data = _load("18_ml_surrogates", "pricing_slices.npz")
    return _line(data, "moneyness", ("delta_error", "gamma_error"), "Greek error by moneyness")


def _vol18_hard() -> go.Figure:
    data = _load("18_ml_surrogates", "pricing_slices.npz")
    return _bar(
        data,
        "check_names",
        ("violations_unconstrained", "violations_constrained"),
        "Hard-check violations",
    )


def _vol18_speed() -> go.Figure:
    data = _load("18_ml_surrogates", "pricing_slices.npz")
    return _line(
        data, "batch_size", ("analytic_us", "mlp_us"), "CPU latency vs batch size", log_y=True
    )


def _vol19_fit() -> go.Figure:
    data = _vol19_view()
    return _line(
        data,
        "strike",
        ("clean_teacher_price", "hard_constrained_price"),
        "Clean teacher vs hard-constrained call price",
    )


def _vol19_identifiability() -> go.Figure:
    data = _vol19_view()
    fig = go.Figure(
        go.Scatter(
            x=data["start_parameter_rmse"],
            y=data["start_repricing_rmse"],
            mode="markers",
            marker={"color": data["start_index"], "colorscale": "Viridis", "showscale": True},
        )
    )
    return fig.update_layout(title="Parameter error vs repricing error")


def _vol19_arbitrage() -> go.Figure:
    data = _vol19_view()
    roughness = np.mean(np.abs(np.diff(data["raw_price"], n=2, axis=1)), axis=1)
    constrained = np.mean(np.abs(np.diff(data["hard_constrained_price"], n=2, axis=1)), axis=1)
    derived = {
        "maturity": data["constraint_maturities"].astype(str),
        "unconstrained": roughness,
        "hard": constrained,
    }
    return _bar(derived, "maturity", ("unconstrained", "hard"), "Fit vs surface-shape diagnostics")


def _vol19_variance() -> go.Figure:
    data = _vol19_view()
    return _line(
        data,
        "variance_maturity",
        ("target_variance", "iv_only_variance", "joint_variance"),
        "Variance-term consistency",
    )


def _vol20_forecast() -> go.Figure:
    data = _vol20_view()
    return _line(
        data,
        "test_row",
        ("actual_variance", "har_ridge_prediction", "pca_ridge_prediction"),
        "Walk-forward realized-variance forecasts",
    )


def _vol20_metrics() -> go.Figure:
    data = _vol20_view()
    return _bar(data, "model_names", ("rmse", "qlike"), "Forecast metrics")


def _vol20_pnl() -> go.Figure:
    data = _vol20_view()
    return _hist(data, "hedge_pnl", "hedge_names", "Common-path hedging P&L")


def _vol20_economics() -> go.Figure:
    data = _vol20_view()
    return _bar(data, "hedge_names", ("cvar95", "turnover"), "CVaR and turnover")


def _vol21_spx() -> go.Figure:
    data = _load("21_spx_vix", "joint_surface.npz")
    return _line(data, "strike", ("spx_target", "spx_pdv", "spx_afv"), "SPX IV joint fit")


def _vol21_vix() -> go.Figure:
    data = _load("21_spx_vix", "joint_surface.npz")
    return _line(data, "vix_maturity", ("vix_target", "vix_pdv"), "VIX term structure")


def _vol21_models() -> go.Figure:
    data = _load("21_spx_vix", "joint_surface.npz")
    return _bar(data, "model_names", ("spx_rmse", "vix_rmse"), "Joint-model error")


def _vol21_speed() -> go.Figure:
    data = _load("21_spx_vix", "joint_surface.npz")
    return _line(
        data, "batch_size", ("nested_mc_ms", "surrogate_ms"), "Nested MC vs surrogate", log_y=True
    )


def _vol22_clock() -> go.Figure:
    data = _load("22_zero_dte", "intraday_slices.npz")
    return _line(data, "minute", ("variance_weight", "variance_clock"), "Intraday variance clock")


def _vol22_jump() -> go.Figure:
    data = _load("22_zero_dte", "intraday_slices.npz")
    return _line(
        data,
        "minute",
        ("event_jump_intensity", "non_event_jump_intensity"),
        "Scheduled-event jump intensity",
    )


def _vol22_expiry() -> go.Figure:
    data = _load("22_zero_dte", "intraday_slices.npz")
    return _line(
        data,
        "adjacent_expiry_minutes",
        ("total_variance", "model_total_variance"),
        "Adjacent-expiry consistency",
    )


def _vol22_ood() -> go.Figure:
    data = _load("22_zero_dte", "intraday_slices.npz")
    return _bar(data, "tod_names", ("price_mae", "greek_mae"), "Time-of-day OOD error")


def _vol23_compounding() -> go.Figure:
    data = _load("23_rfr_post_libor", "rfr_scenarios.npz")
    return _line(
        data, "day", ("discrete_accrual", "continuous_accrual"), "RFR compounding conventions"
    )


def _vol23_convexity() -> go.Figure:
    data = _load("23_rfr_post_libor", "rfr_scenarios.npz")
    return _line(data, "maturity", ("futures_forward_bp",), "Futures-forward convexity")


def _vol23_smile() -> go.Figure:
    data = _load("23_rfr_post_libor", "rfr_scenarios.npz")
    return _line(data, "strike", ("normal_iv", "shifted_sabr_iv"), "Bachelier vs shifted SABR")


def _vol23_delta() -> go.Figure:
    data = _load("23_rfr_post_libor", "rfr_scenarios.npz")
    return _bar(data, "hedge_names", ("hedge_rmse",), "Sticky-strike vs Bartlett delta")


def _vol24_prices() -> go.Figure:
    data = _load("24_crypto_market_structure", "stress_paths.npz")
    return _line(
        data, "step", ("index_price", "mark_price", "last_price"), "Perpetual price states"
    )


def _vol24_waterfall() -> go.Figure:
    data = _load("24_crypto_market_structure", "stress_paths.npz")
    return _line(data, "step", ("insurance_fund", "adl_notional"), "Liquidation waterfall")


def _vol24_solvency() -> go.Figure:
    data = _load("24_crypto_market_structure", "stress_paths.npz")
    return _line(data, "step", ("equity", "liability"), "Stress-path solvency ledger")


def _vol24_lvr() -> go.Figure:
    data = _load("24_crypto_market_structure", "stress_paths.npz")
    return _line(
        data, "step", ("lvr", "fee_income", "dynamic_fee_income"), "LVR and fee compensation"
    )


def _vol25_carbon() -> go.Figure:
    data = _load("25_climate_energy", "scenarios.npz")
    return _line(data, "strike", ("carbon_gbm_iv", "carbon_jump_iv"), "Carbon option smile")


def _vol25_weather() -> go.Figure:
    data = _load("25_climate_energy", "scenarios.npz")
    return _line(
        data,
        "day",
        ("temperature_seasonal", "temperature_ou", "temperature_fou"),
        "Weather dynamics",
    )


def _vol25_basis() -> go.Figure:
    data = _load("25_climate_energy", "scenarios.npz")
    return _line(data, "station_distance_km", ("basis_rmse",), "Location basis risk")


def _vol25_ppa() -> go.Figure:
    data = _load("25_climate_energy", "scenarios.npz")
    return _bar(data, "risk_names", ("cvar95", "hedge_residual"), "PPA risk decomposition")


def _vol26_curves() -> go.Figure:
    data = _load("26_inflation_jgbi", "inflation_scenarios.npz")
    return _line(
        data,
        "maturity",
        ("nominal_discount_factor", "real_discount_factor"),
        "Nominal vs real discount curves",
    )


def _vol26_swaps() -> go.Figure:
    data = _load("26_inflation_jgbi", "inflation_scenarios.npz")
    return _bar(
        data,
        "zcis_maturity",
        ("zcis_quote", "zcis_repriced"),
        "Zero-coupon inflation swap repricing",
    )


def _vol26_floor() -> go.Figure:
    data = _load("26_inflation_jgbi", "inflation_scenarios.npz")
    vol = data["inflation_volatility"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=vol,
            y=data["floor_analytic"],
            mode="lines+markers",
            name="analytic floor",
            line={"color": "#dc2626"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=vol,
            y=data["floor_mc"],
            mode="markers",
            name="Monte Carlo floor",
            error_y={
                "type": "data",
                "array": data["floor_mc_standard_error"],
                "visible": True,
            },
        )
    )
    fig.update_layout(
        title="JGBi deflation floor vs inflation volatility",
        xaxis_title="inflation volatility",
        yaxis_title="floor value (per 100 face)",
    )
    return fig


def _vol26_bei() -> go.Figure:
    data = _load("26_inflation_jgbi", "inflation_scenarios.npz")
    return _bar(
        data,
        "bei_names",
        ("breakeven_inflation",),
        "Raw vs floor-adjusted breakeven inflation",
    )


def _vol27_traffic_light() -> go.Figure:
    data = _load("27_risk_desk", "risk_desk_scenarios.npz")
    count = data["traffic_light_x"]
    cumulative = data["traffic_light_cumulative_prob"]
    multiplier = data["traffic_light_multiplier"]
    zone_color = np.where(
        cumulative < 0.95, "#16a34a", np.where(cumulative < 0.9999, "#ca8a04", "#dc2626")
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=count,
            y=multiplier,
            marker_color=zone_color,
            name="capital multiplier",
            opacity=0.85,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=count,
            y=cumulative,
            mode="lines+markers",
            name="P(X<=x) binomial",
            line={"color": "#1f77b4"},
        ),
        secondary_y=True,
    )
    fig.update_xaxes(title_text="exceedance count (250-day, 99%)")
    fig.update_yaxes(title_text="capital multiplier", secondary_y=False)
    fig.update_yaxes(title_text="binomial cumulative probability", secondary_y=True)
    fig.update_layout(title="Basel traffic light: green/yellow/red zones and capital multiplier")
    return fig


def _vol27_coverage() -> go.Figure:
    data = _load("27_risk_desk", "risk_desk_scenarios.npz")
    day = data["backtest_day"]
    names = data["coverage_names"].astype(str)
    rate = data["coverage_rate"]
    fig = go.Figure()
    lines = (
        ("hs_var_forecast", "hs_violations", names[0], rate[0], "#94a3b8"),
        ("fhs_var_forecast", "fhs_violations", names[1], rate[1], "#dc2626"),
    )
    for forecast, violation, label, viol_rate, color in lines:
        fig.add_trace(
            go.Scatter(
                x=day,
                y=data[forecast],
                mode="lines",
                name=f"{label} VaR (violations {viol_rate:.2%})",
                line={"color": color},
            )
        )
        mask = data[violation] > 0.5
        fig.add_trace(
            go.Scatter(
                x=day[mask],
                y=data[forecast][mask],
                mode="markers",
                marker={"symbol": "x", "size": 6, "color": color},
                name=f"{label} violation",
            )
        )
    fig.update_layout(
        title="Rolling 99% VaR coverage: plain HS vs filtered historical simulation",
        xaxis_title="backtest day",
        yaxis_title="VaR (return units)",
    )
    return fig


def _vol27_gpd() -> go.Figure:
    data = _load("27_risk_desk", "risk_desk_scenarios.npz")
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.6, 0.4],
        subplot_titles=("VaR ladder: empirical vs GPD", "Mean-excess function"),
    )
    alpha = data["evt_quantile_alpha"]
    fig.add_trace(
        go.Scatter(x=alpha, y=data["empirical_var_ladder"], mode="lines+markers", name="empirical"),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=alpha,
            y=data["evt_var_ladder"],
            mode="lines+markers",
            name="GPD tail",
            line={"color": "#dc2626"},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["mean_excess_threshold"],
            y=data["mean_excess_curve"],
            mode="lines+markers",
            name="mean excess",
            line={"color": "#1f77b4"},
        ),
        row=1,
        col=2,
    )
    fig.update_xaxes(title_text="coverage level", row=1, col=1)
    fig.update_yaxes(title_text="VaR loss", row=1, col=1)
    fig.update_xaxes(title_text="threshold u", row=1, col=2)
    fig.update_yaxes(title_text="mean excess", row=1, col=2)
    fig.update_layout(title="GPD peaks-over-threshold tail fit")
    return fig


def _vol27_allocation() -> go.Figure:
    data = _load("27_risk_desk", "risk_desk_scenarios.npz")
    metrics = _metrics("27_risk_desk")
    names = data["asset_names"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=data["alloc_component_var"], name="component VaR"))
    fig.add_trace(go.Bar(x=names, y=data["es_components"], name="component ES"))
    var_total = metrics["alloc_normal_var"]
    es_total = metrics["total_historical_es"]
    fig.update_layout(
        title=(
            f"Euler risk allocation — sum CVaR={var_total:.2f} (VaR), "
            f"sum CES={es_total:.2f} (ES); additivity exact"
        ),
        barmode="group",
        xaxis_title="desk / asset",
        yaxis_title="loss amount",
    )
    return fig


FRONTIER_BUILDERS: dict[str, Callable[[], go.Figure]] = {
    "ml_price_error": _vol18_price,
    "ml_greek_error": _vol18_greeks,
    "ml_hard_violations": _vol18_hard,
    "ml_speed": _vol18_speed,
    "surface_fit": _vol19_fit,
    "surface_identifiability": _vol19_identifiability,
    "surface_arbitrage": _vol19_arbitrage,
    "variance_consistency": _vol19_variance,
    "forecast_paths": _vol20_forecast,
    "forecast_metrics": _vol20_metrics,
    "hedge_pnl": _vol20_pnl,
    "hedge_economics": _vol20_economics,
    "spx_joint_fit": _vol21_spx,
    "vix_joint_fit": _vol21_vix,
    "joint_model_error": _vol21_models,
    "nested_mc_speed": _vol21_speed,
    "zero_dte_clock": _vol22_clock,
    "zero_dte_jump": _vol22_jump,
    "zero_dte_expiry": _vol22_expiry,
    "zero_dte_ood": _vol22_ood,
    "rfr_compounding": _vol23_compounding,
    "rfr_convexity": _vol23_convexity,
    "rfr_smile": _vol23_smile,
    "rfr_delta": _vol23_delta,
    "perpetual_prices": _vol24_prices,
    "liquidation_waterfall": _vol24_waterfall,
    "crypto_solvency": _vol24_solvency,
    "amm_lvr": _vol24_lvr,
    "carbon_smile": _vol25_carbon,
    "weather_paths": _vol25_weather,
    "weather_basis": _vol25_basis,
    "ppa_risk": _vol25_ppa,
    "inflation_curves": _vol26_curves,
    "inflation_swaps": _vol26_swaps,
    "jgbi_floor": _vol26_floor,
    "jgbi_bei": _vol26_bei,
    "var_traffic_light": _vol27_traffic_light,
    "fhs_vs_hs_coverage": _vol27_coverage,
    "gpd_tail_fit": _vol27_gpd,
    "risk_allocation_bars": _vol27_allocation,
}
