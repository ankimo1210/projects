from __future__ import annotations

from math import isclose
from typing import Iterable


def assert_close(left: float, right: float, label: str, tolerance: float = 1e-6) -> None:
    if not isclose(left, right, abs_tol=tolerance):
        raise AssertionError(f"{label} does not reconcile: {left} != {right}")


def assert_non_negative(values: Iterable[float], label: str) -> None:
    bad = [v for v in values if v < -1e-9]
    if bad:
        raise AssertionError(f"{label} contains negative values: {bad[:5]}")


def assert_minimum(values: Iterable[float], minimum: float, label: str) -> None:
    bad = [v for v in values if v + 1e-9 < minimum]
    if bad:
        raise AssertionError(f"{label} falls below minimum {minimum}: {bad[:5]}")


def validate_sources_uses(row: dict[str, float], tolerance: float = 1e-6) -> None:
    assert_close(row["total_uses"], row["total_sources"], "Sources and uses", tolerance)


def validate_ev_bridge(row: dict[str, float], tolerance: float = 1e-6) -> None:
    expected = row["equity_purchase_price"] + row["existing_debt"] - row["cash_balance"]
    assert_close(row["headline_enterprise_value"], expected, "Enterprise value bridge", tolerance)


def validate_share_price_bridge(row: dict[str, float], tolerance: float = 1e-6) -> None:
    expected = row["offer_price"] * row["diluted_shares"] / 1_000_000
    assert_close(row["equity_purchase_price"], expected, "Share price bridge", tolerance)


def validate_exit_equity(row: dict[str, float], tolerance: float = 1e-6) -> None:
    expected = row["exit_enterprise_value"] - row["exit_net_debt"]
    assert_close(row["exit_equity_value"], expected, "Exit equity value", tolerance)
