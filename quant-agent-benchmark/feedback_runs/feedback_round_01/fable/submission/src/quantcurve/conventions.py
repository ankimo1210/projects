"""Rate/discount conversions and cash-flow schedule rules.

Everything here follows ``market_data/CONVENTIONS.md``. Where that document is
silent (payment schedules for tenors that are not a whole number of periods),
the rule is a documented, configurable choice selected by empirical evidence
(see ``MODEL_RISKS.md`` and the research report).
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

StubRule = Literal["round", "forward", "ceil", "linspace", "forward_actual"]

#: Default schedule rule: ``n = round(T * f)`` payments at ``1/f, 2/f, ...``
#: from the valuation date with the last payment at maturity, each accruing a
#: level ``1 / f``. The public conventions do not pin the payment dates or the
#: stub accrual of non-integer tenors, so this is a *provisional reading*
#: selected because it is the only one consistent with the observed 1.25Y/1.5Y
#: annual OIS quotes (readings that accrue the stub for its actual length
#: misprice them by about +/-50bp; readings that add a short front period add a
#: spurious coupon to short-stub bonds). Consistency with the data is evidence
#: about the data generator, not proof that the convention is "correct"; the
#: alternatives remain available (``--stub-rule``) and are measured in the
#: sensitivity checks ``stub_rule_*``.
DEFAULT_STUB_RULE: StubRule = "forward"


def discount_from_zero(zero_rate: float, maturity_years: float) -> float:
    """Continuously compounded discount factor exp(-z*T)."""
    if maturity_years < 0:
        raise ValueError("maturity_years must be non-negative")
    return math.exp(-zero_rate * maturity_years)


def zero_from_discount(discount_factor: float, maturity_years: float) -> float:
    """Continuously compounded zero rate -log(D)/T."""
    if discount_factor <= 0:
        raise ValueError("discount_factor must be positive")
    if maturity_years <= 0:
        raise ValueError("maturity_years must be positive")
    return -math.log(discount_factor) / maturity_years


def simple_deposit_rate(discount_factor: float, maturity_years: float) -> float:
    """Simple annual deposit rate implied by a discount factor."""
    if discount_factor <= 0 or maturity_years <= 0:
        raise ValueError("positive discount_factor and maturity_years required")
    return (1.0 / discount_factor - 1.0) / maturity_years


def discount_from_simple_rate(rate: float, maturity_years: float) -> float:
    """Deposit convention D(T) = 1 / (1 + r T)."""
    denom = 1.0 + rate * maturity_years
    if denom <= 0:
        raise ValueError("simple rate implies a non-positive discount factor")
    return 1.0 / denom


def schedule_times(maturity_years: float, frequency: int, rule: StubRule = DEFAULT_STUB_RULE) -> np.ndarray:
    """Payment times (in years from the valuation date) for a level-payment leg.

    ``rule`` (``forward_actual`` uses the ``forward`` dates with actual stub accrual):

    * ``"round"`` (default): ``n = max(1, round(T f))`` payments at
      ``T - (n-1-i)/f``; a front stub shorter than half a period is merged into
      the following period (long first period), a longer one becomes a short
      first period. Every period accrues a full ``1/f``.
    * ``"ceil"``: ``n = ceil(T f)`` payments backward from maturity; a short
      front stub receives a full level payment.
    * ``"linspace"``: ``n = max(1, round(T f))`` equally spaced payments
      ending at maturity (period length ``T/n``).
    * ``"forward"``: ``n = max(1, round(T f))`` payments at ``1/f, 2/f, ...``
      from the valuation date with the last payment moved to maturity (the
      final period is short or long).
    """
    if maturity_years <= 0:
        raise ValueError("maturity_years must be positive")
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    periods = maturity_years * frequency
    if rule == "round":
        n = max(1, int(round(periods)))
        times = maturity_years - (n - 1 - np.arange(n)) / frequency
    elif rule == "ceil":
        n = max(1, int(math.ceil(periods - 1e-9)))
        times = maturity_years - (n - 1 - np.arange(n)) / frequency
    elif rule == "linspace":
        n = max(1, int(round(periods)))
        times = np.linspace(maturity_years / n, maturity_years, n)
    elif rule in ("forward", "forward_actual"):
        n = max(1, int(round(periods)))
        times = np.concatenate([np.arange(1, n) / frequency, [maturity_years]])
    else:  # pragma: no cover - guarded by typing
        raise ValueError(f"unknown stub rule: {rule}")
    times = np.asarray(times, dtype=float)
    if times[0] <= 0:
        # Only possible for ``ceil`` with pathological inputs; drop non-positive times.
        times = times[times > 1e-12]
    return times


def ois_accruals(times: np.ndarray, frequency: int, rule: StubRule = DEFAULT_STUB_RULE) -> np.ndarray:
    """Accrual fractions alpha_i for a fixed leg.

    ``round`` / ``forward`` / ``linspace``: level ``1/f`` per payment (the reading
    that is consistent with the public 1.25Y/1.5Y OIS quotes).
    ``ceil`` / ``forward_actual``: the actual period length ``t_i - t_{i-1}`` so
    that the stub accrues for its true length (the textbook reading). The
    public specification does not pin the stub accrual; both readings are kept
    so the difference can be measured (see sensitivity checks).
    """
    if rule in ("ceil", "forward_actual"):
        return np.diff(np.concatenate([[0.0], np.asarray(times, dtype=float)]))
    return np.full(len(times), 1.0 / frequency, dtype=float)


def year_fraction_act365(start: np.datetime64, end: np.datetime64) -> float:
    """ACT/365F year fraction between two dates."""
    days = (np.datetime64(end, "D") - np.datetime64(start, "D")).astype(int)
    return float(days) / 365.0
