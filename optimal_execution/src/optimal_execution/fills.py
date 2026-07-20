"""Passive (limit-order) fill model.

FIFO queue at one aggregated price level:

* The agent's order sits behind ``queue_ahead`` shares at its price.
* Opposite-side market-order volume first consumes the queue ahead, then the
  agent's order (no double filling — fills are bounded by remaining size).
* Cancellations ahead erode the queue by a small factor per sub-step.
* If the market trades *through* the agent's price (for a sell order: the
  best bid rises to or above it), the remainder fills instantly at the limit
  price — the "crossed" fill. This is the sharpest adverse-selection channel:
  the order is taken exactly when the price is moving against holding it.
* Additional adverse selection is statistical: opposite flow intensity is
  tilted by the latent alpha that also drifts the mid (see order_book.py).

``passive_fill_probability`` gives the Poisson-flow estimate used by the
tactical heuristic and the tests.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from scipy import stats

if TYPE_CHECKING:  # pragma: no cover
    from .order_book import AgentLimitOrder, OrderBook

QUEUE_CANCEL_EROSION = 0.02  # fraction of queue-ahead cancelled per sub-step


def match_passive(
    book: OrderBook, order: AgentLimitOrder, opposite_mo_volume: float
) -> tuple[float, bool]:
    """Match one sub-step of opposite flow against the agent's resting order.

    Returns (fill_qty, crossed). Mutates ``order`` (filled / queue_ahead).
    """
    remaining = order.qty - order.filled
    if remaining <= 1e-9:
        return 0.0, False
    sign = book.sign
    eps = 1e-12

    # market traded through our price -> instant full fill at our price
    if (sign > 0 and book.best_bid >= order.price - eps) or (
        sign < 0 and book.best_ask <= order.price + eps
    ):
        order.filled = order.qty
        return remaining, True

    # are we still at the touch (or better)? otherwise we sit away from market
    at_market = (sign > 0 and order.price <= book.best_ask + 1e-9) or (
        sign < 0 and order.price >= book.best_bid - 1e-9
    )
    order.queue_ahead *= 1.0 - QUEUE_CANCEL_EROSION
    if not at_market or opposite_mo_volume <= 0:
        return 0.0, False

    take = max(0.0, opposite_mo_volume - order.queue_ahead)
    fill = min(take, remaining)
    order.queue_ahead = max(0.0, order.queue_ahead - opposite_mo_volume)
    order.filled += fill
    return fill, False


def queue_position_value(
    queue_ahead: float,
    order_qty: float,
    opposite_rate_per_s: float,
    mean_order_size: float,
    horizon_s: float,
    half_spread: float,
    target_depth: float,
) -> float:
    """Stylized Moallemi–Yuan (2016) value of a resting order's queue position.

        V(Q_a) = P_fill(Q_a) * (half_spread - c_adv(Q_a)),
        c_adv(Q_a) = 2 * half_spread * (1 - exp(-Q_a / target_depth)).

    Filling earns the half-spread; conditional on filling, deeper queue
    positions are reached only when large (more informed) flow sweeps the
    level, so the adverse-selection cost grows toward the full spread. The
    value therefore crosses zero at Q_a = target_depth * ln 2 and the front
    of the queue is worth ~ P_fill(0) * half_spread. This is a reduced form
    in the spirit of Moallemi–Yuan — their model prices the position from
    the flow dynamics; here the shape is postulated for exposition.
    """
    p_fill = passive_fill_probability(
        queue_ahead, order_qty, opposite_rate_per_s, mean_order_size, horizon_s
    )
    c_adv = 2.0 * half_spread * (1.0 - math.exp(-queue_ahead / max(target_depth, 1e-12)))
    return p_fill * (half_spread - c_adv)


def passive_fill_probability(
    queue_ahead: float,
    order_qty: float,
    opposite_rate_per_s: float,
    mean_order_size: float,
    horizon_s: float,
) -> float:
    """P(cumulative opposite MO volume over horizon > queue_ahead + qty/2).

    Opposite volume ~ Poisson(rate * horizon) * mean size (the simulator's
    aggregation). Returns a probability in [0, 1].
    """
    if mean_order_size <= 0 or opposite_rate_per_s <= 0 or horizon_s <= 0:
        return 0.0
    lam = opposite_rate_per_s * horizon_s
    need = max(queue_ahead + 0.5 * order_qty, 0.0) / mean_order_size
    # P(N >= ceil(need)) = survival function at need - 1
    k = max(math.ceil(need) - 1, -1)
    p = float(stats.poisson.sf(k, lam))
    return min(max(p, 0.0), 1.0)
