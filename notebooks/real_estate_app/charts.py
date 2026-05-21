"""
charts.py — Plotly chart functions for the Streamlit app.

Each function returns a plotly Figure object so Streamlit can render it
via st.plotly_chart(fig, use_container_width=True).
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_MONEY_HOVER = "Year %{x}<br>%{fullData.name}: %{y:,.0f} 円<extra></extra>"
_MONEY_M_HOVER = "Year %{x}<br>%{fullData.name}: %{y:,.1f} M<extra></extra>"
_PCT_HOVER = "Year %{x}<br>%{fullData.name}: %{y:.2f}%<extra></extra>"


def _base_layout(**kwargs):
    defaults = dict(
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=50, b=40),
    )
    defaults.update(kwargs)
    return defaults


def plot_cumulative_cashflow_components(df):
    """Cumulative CF by component (NOI, Interest, Principal, Capex, Tax, Total Eq CF)."""
    fig = go.Figure()
    series = [
        ("cum_noi", "Cum NOI", None),
        ("cum_interest", "Cum Interest", "dash"),
        ("cum_principal", "Cum Principal", "dash"),
        ("cum_capex", "Cum Capex", "dot"),
        ("cum_tax", "Cum Tax", "dashdot"),
        ("cum_total_equity_cf", "Cum Total Eq CF", None),
    ]
    for col, label, dash in series:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["year"], y=df[col],
                name=label, mode="lines+markers",
                line=dict(dash=dash, width=2),
                hovertemplate=_MONEY_HOVER,
            ))
    fig.add_hline(y=0, line_width=1, line_color="black")
    fig.update_layout(**_base_layout(
        title="Cumulative Cash Flow by Component",
        xaxis_title="Year", yaxis_title="円",
        yaxis_tickformat=",",
    ))
    return fig


def plot_annual_cashflow(df):
    """Annual CF: NOI / Debt Service / BTCF / ATCF."""
    fig = go.Figure()
    for col, label in [("noi", "NOI"), ("debt_service", "Debt Service"),
                       ("btcf", "BTCF"), ("atcf", "ATCF")]:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df[col],
            name=label, mode="lines+markers",
            hovertemplate=_MONEY_HOVER,
        ))
    fig.add_hline(y=0, line_width=1, line_color="black")
    fig.update_layout(**_base_layout(
        title="Annual Cash Flow Components",
        xaxis_title="Year", yaxis_title="円",
        yaxis_tickformat=",",
    ))
    return fig


def plot_cumulative_equity_cf(df):
    """Cumulative Equity CF (net of initial investment)."""
    colors = ["steelblue" if v >= 0 else "coral"
              for v in df["cumulative_equity_cf_with_initial"]]
    fig = go.Figure(go.Bar(
        x=df["year"], y=df["cumulative_equity_cf_with_initial"],
        marker_color=colors,
        hovertemplate="Year %{x}<br>Cum Equity CF: %{y:,.0f} 円<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="red")
    fig.update_layout(**_base_layout(
        title="Cumulative Equity CF (Net of Initial Investment)",
        xaxis_title="Year", yaxis_title="円",
        yaxis_tickformat=",",
        showlegend=False,
    ))
    return fig


def plot_operating_pl(pl_df):
    """Operating P/L: Op Profit / Pre-Tax / After-Tax."""
    fig = go.Figure()
    for col, label in [
        ("operating_profit_before_dep", "Op Profit (before dep)"),
        ("accounting_pre_tax_income", "Pre-Tax Income"),
        ("accounting_after_tax_income", "After-Tax Income"),
    ]:
        fig.add_trace(go.Scatter(
            x=pl_df["year"], y=pl_df[col],
            name=label, mode="lines+markers",
            hovertemplate=_MONEY_HOVER,
        ))
    fig.add_hline(y=0, line_width=1, line_color="black")
    fig.update_layout(**_base_layout(
        title="Operating P/L",
        xaxis_title="Year", yaxis_title="円",
        yaxis_tickformat=",",
    ))
    return fig


def plot_market_value_loan_nav(nav_df, equity_invested):
    """Market Value / Loan Balance / NAV After Tax."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nav_df["year"], y=nav_df["estimated_market_value"],
        name="Market Value", mode="lines+markers",
        line=dict(color="steelblue"), hovertemplate=_MONEY_HOVER,
    ))
    fig.add_trace(go.Scatter(
        x=nav_df["year"], y=nav_df["loan_balance_end"],
        name="Loan Balance", mode="lines+markers",
        line=dict(color="coral"), hovertemplate=_MONEY_HOVER,
    ))
    fig.add_trace(go.Scatter(
        x=nav_df["year"], y=nav_df["nav_after_tax"],
        name="NAV After Tax", mode="lines+markers",
        line=dict(color="green"), hovertemplate=_MONEY_HOVER,
    ))
    fig.add_hline(y=equity_invested, line_dash="dash", line_color="gray",
                  annotation_text="Initial Equity")
    fig.update_layout(**_base_layout(
        title="Market Value / Loan Balance / NAV After Tax",
        xaxis_title="Year", yaxis_title="円",
        yaxis_tickformat=",",
    ))
    return fig


def plot_drawdown_curves(dd_results):
    """Drawdown curves (% of peak) for Liquidity, NAV AT, Total Return."""
    colors = {"Liquidity": "steelblue", "NAV After Tax": "green", "Total Return": "darkorange"}
    fig = go.Figure()
    for name, data in dd_results.items():
        dd_df = data["dd_df"]
        fig.add_trace(go.Scatter(
            x=dd_df["year"], y=dd_df["drawdown_pct"] * 100,
            name=name, mode="lines+markers", marker=dict(size=5),
            line=dict(color=colors.get(name, "gray")),
            hovertemplate=_PCT_HOVER,
        ))
    fig.add_hline(y=0, line_width=1, line_color="black")
    fig.update_layout(**_base_layout(
        title="Drawdown Curves (% of Running Peak)",
        xaxis_title="Year", yaxis_title="Drawdown (%)",
    ))
    return fig


def plot_loan_balance(df):
    """Outstanding loan balance over time."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["loan_balance_end"],
        name="Loan Balance", mode="lines",
        fill="tozeroy", fillcolor="rgba(255,127,80,0.2)",
        line=dict(color="coral", width=2),
        hovertemplate=_MONEY_HOVER,
    ))
    fig.update_layout(**_base_layout(
        title="Outstanding Loan Balance",
        xaxis_title="Year", yaxis_title="円",
        yaxis_tickformat=",",
    ))
    return fig


def plot_scenario_summary(scenario_df):
    """Scenario comparison: 2x2 subplots."""
    fig = make_subplots(rows=2, cols=2, subplot_titles=[
        "Equity IRR by Scenario", "Final NAV After Tax",
        "Max Drawdown % (Liquidity)", "Equity Multiple by Scenario",
    ])

    scenarios = scenario_df["Scenario"]
    irr_vals = [(x if x else 0) * 100 for x in scenario_df["Equity IRR"]]
    fig.add_trace(go.Bar(
        y=scenarios, x=irr_vals, orientation="h",
        marker_color="teal", opacity=0.8,
        hovertemplate="%{y}<br>IRR: %{x:.2f}%<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        y=scenarios, x=scenario_df["Final NAV AT (M)"], orientation="h",
        marker_color="green", opacity=0.8,
        hovertemplate="%{y}<br>NAV: %{x:,.1f} M<extra></extra>",
    ), row=1, col=2)

    fig.add_trace(go.Bar(
        y=scenarios, x=scenario_df["Max DD% Liq"].abs() * 100, orientation="h",
        marker_color="coral", opacity=0.8,
        hovertemplate="%{y}<br>Max DD: %{x:.2f}%<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Bar(
        y=scenarios, x=scenario_df["Equity Multiple"], orientation="h",
        marker_color="steelblue", opacity=0.8,
        hovertemplate="%{y}<br>Multiple: %{x:.2f}x<extra></extra>",
    ), row=2, col=2)

    fig.update_layout(
        template="plotly_white", showlegend=False,
        height=600, margin=dict(l=160, r=20, t=50, b=40),
    )
    return fig


def plot_ownership_comparison(own_summary_df):
    """Ownership comparison: IRR / NAV / Tax 3-panel."""
    fig = make_subplots(rows=1, cols=3, subplot_titles=[
        "IRR: Individual vs Corporate",
        "Final NAV After Tax",
        "Total Tax Paid",
    ])
    colors = ["teal", "coral"]
    owners = own_summary_df["Ownership"]

    irr_vals = [(x if x else 0) * 100 for x in own_summary_df["Equity IRR"]]
    fig.add_trace(go.Bar(
        x=owners, y=irr_vals, marker_color=colors, opacity=0.8,
        hovertemplate="%{x}<br>IRR: %{y:.2f}%<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=owners, y=own_summary_df["Final NAV AT (M)"],
        marker_color=colors, opacity=0.8,
        hovertemplate="%{x}<br>NAV: %{y:,.1f} M<extra></extra>",
    ), row=1, col=2)

    fig.add_trace(go.Bar(
        x=owners, y=own_summary_df["Total Tax (M)"],
        marker_color=colors, opacity=0.8,
        hovertemplate="%{x}<br>Tax: %{y:,.1f} M<extra></extra>",
    ), row=1, col=3)

    fig.update_yaxes(title_text="IRR (%)", row=1, col=1)
    fig.update_yaxes(title_text="Million JPY", row=1, col=2)
    fig.update_yaxes(title_text="Million JPY", row=1, col=3)
    fig.update_layout(
        template="plotly_white", showlegend=False,
        height=400, margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


def plot_tax_bridge(tax_bridge):
    """Tax bridge bar chart."""
    categories = list(tax_bridge.keys())
    values = list(tax_bridge.values())
    colors = ["steelblue", "coral", "purple"][:len(categories)]

    fig = go.Figure(go.Bar(
        x=categories, y=values,
        marker_color=colors, opacity=0.8,
        text=[f"{v:,.0f}" for v in values],
        textposition="outside",
        hovertemplate="%{x}<br>%{y:,.0f} 円<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title="Tax Bridge",
        yaxis_title="円", yaxis_tickformat=",",
        showlegend=False,
    ))
    return fig


def plot_exit_waterfall(wf_df):
    """Exit waterfall chart."""
    items = wf_df["Item"].tolist()
    amounts = wf_df["Amount"].tolist()

    cumulative = 0
    bases = []
    for amt in amounts:
        if amt >= 0:
            bases.append(cumulative)
            cumulative += amt
        else:
            cumulative += amt
            bases.append(cumulative)

    colors = ["steelblue" if a >= 0 else "coral" for a in amounts]

    fig = go.Figure(go.Bar(
        x=items, y=[abs(a) for a in amounts],
        base=bases,
        marker_color=colors, opacity=0.8,
        text=[f"{a:,.0f}" for a in amounts],
        textposition="inside", textfont=dict(size=10),
        hovertemplate="%{x}<br>%{customdata:,.0f} 円<extra></extra>",
        customdata=amounts,
    ))
    fig.update_layout(**_base_layout(
        title="Exit Waterfall",
        yaxis_title="円", yaxis_tickformat=",",
        showlegend=False,
        xaxis_tickangle=-25,
    ))
    return fig


def plot_refinance_impact(base_params):
    """Refinance impact: Cumulative ATCF and Loan Balance comparison."""
    from sim_engine import run_scenario, add_cumulative_cashflow_columns

    refi_scenarios = [
        {"label": "No Refinance", "overrides": {"enable_refinance": False}},
        {"label": "Refi Year 5 (LTV 70%)", "overrides": {
            "enable_refinance": True, "refinance_year": 5,
            "refinance_ltv": 0.70, "refinance_interest_rate": 0.018,
            "refinance_term_years": 25, "refinance_fee_rate": 0.01,
        }},
    ]

    fig = make_subplots(rows=1, cols=2, subplot_titles=[
        "Refinance Impact: Cumulative ATCF",
        "Refinance Impact: Loan Balance",
    ])

    for sc in refi_scenarios:
        df_r, _, m_r, p_r = run_scenario(base_params, sc["overrides"])
        df_r, _ = add_cumulative_cashflow_columns(df_r, p_r)
        fig.add_trace(go.Scatter(
            x=df_r["year"], y=df_r["cumulative_atcf"],
            name=sc["label"], mode="lines+markers", marker=dict(size=5),
            hovertemplate="Year %{x}<br>Cum ATCF: %{y:,.0f} 円<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df_r["year"], y=df_r["loan_balance_end"],
            name=sc["label"], mode="lines+markers", marker=dict(size=5),
            hovertemplate="Year %{x}<br>Loan Bal: %{y:,.0f} 円<extra></extra>",
            showlegend=False,
        ), row=1, col=2)

    fig.update_yaxes(title_text="Cum ATCF (円)", tickformat=",", row=1, col=1)
    fig.update_yaxes(title_text="Loan Balance (円)", tickformat=",", row=1, col=2)
    fig.update_xaxes(title_text="Year", row=1, col=1)
    fig.update_xaxes(title_text="Year", row=1, col=2)
    fig.update_layout(
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
        height=400, margin=dict(l=80, r=20, t=80, b=40),
    )
    return fig
