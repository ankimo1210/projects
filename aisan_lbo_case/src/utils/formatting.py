from __future__ import annotations


def fmt_jpy_mn(value: float | int | None, decimals: int = 0) -> str:
    if value is None:
        return "n/a"
    return f"JPY {value:,.{decimals}f}m"


def fmt_jpy_bn(value_mn: float | int | None, decimals: int = 1) -> str:
    if value_mn is None:
        return "n/a"
    return f"JPY {value_mn / 1000:,.{decimals}f}bn"


def fmt_pct(value: float | int | None, decimals: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:,.{decimals}f}%"


def fmt_multiple(value: float | int | None, decimals: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{decimals}f}x"


def fmt_int(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.0f}"
