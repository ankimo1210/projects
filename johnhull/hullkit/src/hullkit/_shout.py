"""Private teaching CRR engine for one optimal shout (Hull 11e GE §26.12).

Constant-parameter GBM; positive spot, strike, volatility and maturity. Rates
and yield are continuous annual rates, time is years, values are currency.
The call is Hull's contract; the independently evaluated put is an extension.
Finite trees approximate continuous decision times; convergence need not be
pointwise monotone. This module deliberately imports no reference engine.
"""

import math
from numbers import Integral

import numpy as np
from scipy.special import ndtr


def _immediate(spots, strike, rate, dividend, sigma, tau, kind):
    """Signed locked cash plus a fresh ATM European option, paid at maturity."""
    discounted_cash = (spots - strike) * math.exp(-rate * tau)
    root = sigma * math.sqrt(tau)
    d1 = (rate - dividend + sigma * sigma / 2) * tau / root
    d2 = d1 - root
    if kind == "call":
        reset = spots * (math.exp(-dividend * tau) * ndtr(d1) - math.exp(-rate * tau) * ndtr(d2))
        return discounted_cash + reset, discounted_cash, reset
    reset = spots * (math.exp(-rate * tau) * ndtr(-d2) - math.exp(-dividend * tau) * ndtr(-d1))
    return -discounted_cash + reset, -discounted_cash, reset


def _tree(spot, strike, rate, dividend, sigma, expiry, kind="call", steps=1024):
    """Return root decision, actual node boundary brackets and tiny-tree nodes.

    ``remaining_times``, ``boundary_lower`` and ``boundary_upper`` run from
    expiry down to one time step. A None bracket means no unique adjacent
    continuation/shout transition was identified in that layer. These are node brackets of the finite
    tree decision boundary, not certified brackets of the continuous boundary.
    ``small_tree_nodes`` contains all nodes only for steps <= 16. Terminal
    nodes have action ``maturity`` and null immediate/continuation/cash/reset.
    Root immediate and continuation are signed analytic shout value and
    discounted child expectation, respectively, before taking their maximum.
    """
    inputs = (spot, strike, rate, dividend, sigma, expiry)
    try:
        valid = all(math.isfinite(x) for x in inputs)
    except (TypeError, ValueError):
        valid = False
    if not valid or min(spot, strike, sigma, expiry) <= 0:
        raise ValueError("finite inputs and positive spot, strike, sigma, expiry required")
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    if isinstance(steps, bool) or not isinstance(steps, Integral) or steps < 1:
        raise ValueError("steps must be a positive integer")
    dt = expiry / steps
    log_up = sigma * math.sqrt(dt)
    try:
        up = math.exp(log_up)
        down = 1 / up
        probability = (math.exp((rate - dividend) * dt) - down) / (up - down)
        discount = math.exp(-rate * dt)
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError("unrepresentable CRR parameters") from error
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("CRR transition probability must lie in [0, 1]; increase steps")
    if abs(math.log(spot)) + steps * log_up > 700 or max(abs(rate), abs(dividend)) * expiry > 700:
        raise ValueError("parameters exceed the representable teaching-tree domain")
    sign = 1 if kind == "call" else -1
    terminal = spot * np.exp((2 * np.arange(steps + 1) - steps) * log_up)
    values = np.maximum(sign * (terminal - strike), 0)
    nodes = []
    if steps <= 16:
        for j, level in enumerate(terminal):
            nodes.append(
                dict(
                    id=f"{steps}-{j}",
                    step=steps,
                    upcount=j,
                    spot=float(level),
                    remaining_time=0.0,
                    immediate=None,
                    continuation=None,
                    discounted_cash=None,
                    reset_atm=None,
                    value=float(values[j]),
                    action="maturity",
                )
            )
    times = [expiry - i * dt for i in range(steps)]
    lower, upper = [None] * steps, [None] * steps
    for i in range(steps - 1, -1, -1):
        levels = spot * np.exp((2 * np.arange(i + 1) - i) * log_up)
        continuation = discount * ((1 - probability) * values[:-1] + probability * values[1:])
        immediate, cash, reset = _immediate(levels, strike, rate, dividend, sigma, times[i], kind)
        exercise = immediate >= continuation
        values = np.maximum(continuation, immediate)
        if kind == "call":
            crossings = np.flatnonzero((~exercise[:-1]) & exercise[1:] & (levels[1:] > strike))
        else:
            crossings = np.flatnonzero(exercise[:-1] & (~exercise[1:]) & (levels[:-1] < strike))
        if len(crossings) == 1:
            index = crossings[0]
            lower[i], upper[i] = float(levels[index]), float(levels[index + 1])
        if steps <= 16:
            for j, level in enumerate(levels):
                nodes.append(
                    dict(
                        id=f"{i}-{j}",
                        step=i,
                        upcount=j,
                        spot=float(level),
                        remaining_time=times[i],
                        immediate=float(immediate[j]),
                        continuation=float(continuation[j]),
                        discounted_cash=float(cash[j]),
                        reset_atm=float(reset[j]),
                        value=float(values[j]),
                        action="shout" if exercise[j] else "continue",
                    )
                )
    return dict(
        price=float(values[0]),
        immediate=float(immediate[0]),
        continuation=float(continuation[0]),
        root_decision="shout" if exercise[0] else "continue",
        remaining_times=times,
        boundary_lower=lower,
        boundary_upper=upper,
        small_tree_nodes=sorted(nodes, key=lambda node: (node["step"], node["upcount"])),
        steps=int(steps),
        up=up,
        down=down,
        probability=probability,
        discount=discount,
    )


def _price(spot, strike, rate, dividend, sigma, expiry, kind="call", steps=1024):
    """Price one shout or no shout on a finite CRR decision grid (currency)."""
    return _tree(spot, strike, rate, dividend, sigma, expiry, kind, steps)["price"]
