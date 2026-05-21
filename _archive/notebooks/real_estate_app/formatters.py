"""
formatters.py — Unified number formatting helpers for display layer.

Internal data stays numeric; these are used only at display time.
"""

import streamlit as st


# ---------------------------------------------------------------------------
# String formatters (for st.metric, markdown, hover, summary tables)
# ---------------------------------------------------------------------------

def format_money(value, decimals=0, suffix="円"):
    """Format a monetary value with thousand separators."""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f} {suffix}".strip()


def format_money_m(value, suffix="M"):
    """Format a monetary value in millions."""
    if value is None:
        return "N/A"
    return f"{value / 1e6:,.1f} {suffix}"


def format_percent(value, decimals=1):
    """Format a ratio as percentage string (0.05 → '5.0%')."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}%}"


def format_multiple(value, decimals=2):
    """Format a multiple (e.g. equity multiple) with 'x' suffix."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}x"


def format_year(value):
    """Format year as integer string."""
    if value is None:
        return "N/A"
    return str(int(value))


# ---------------------------------------------------------------------------
# Streamlit column_config builders (for st.dataframe / st.data_editor)
# ---------------------------------------------------------------------------

def col_money(label, step=None, fmt="%,.0f"):
    """NumberColumn config for monetary values."""
    kwargs = {"label": label, "format": fmt}
    if step is not None:
        kwargs["step"] = step
    return st.column_config.NumberColumn(**kwargs)


def col_percent(label, fmt="%.2f%%"):
    """NumberColumn config for percentage values (stored as ratio 0–1, displayed as %)."""
    return st.column_config.NumberColumn(label=label, format=fmt)


def col_multiple(label, fmt="%.2f"):
    """NumberColumn config for multiple/ratio values."""
    return st.column_config.NumberColumn(label=label, format=fmt)


def col_year(label="Year"):
    """NumberColumn config for year column."""
    return st.column_config.NumberColumn(label=label, format="%d")


# ---------------------------------------------------------------------------
# Column config builders for common table patterns
# ---------------------------------------------------------------------------

def cashflow_column_config(columns):
    """Build column_config dict for cash flow tables."""
    cfg = {}
    for c in columns:
        if c == "year":
            cfg[c] = col_year("Year")
        else:
            cfg[c] = col_money(c, fmt="%,.0f")
    return cfg


def nav_column_config(columns):
    """Build column_config dict for NAV tables."""
    cfg = {}
    for c in columns:
        if c == "year":
            cfg[c] = col_year("Year")
        else:
            cfg[c] = col_money(c, fmt="%,.0f")
    return cfg


# ---------------------------------------------------------------------------
# Pandas Styler helper
# ---------------------------------------------------------------------------

def style_negatives_red(df):
    """Return a pandas Styler that colours all negative numeric cells red."""
    def _color(val):
        try:
            if float(val) < 0:
                return "color: #e53935; font-weight: 600"
        except (TypeError, ValueError):
            pass
        return ""
    return df.style.map(_color)
