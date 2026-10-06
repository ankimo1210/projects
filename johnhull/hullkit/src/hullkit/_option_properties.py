"""Private Hull GE Ch11 calculations; educational conventions are explicit."""

import math

import numpy as np

from . import bsm, trees


def _market(spot, strike, rate, volatility, maturity):
    values = np.asarray([spot, strike, rate, volatility, maturity], dtype=float)
    if not np.all(np.isfinite(values)) or min(spot, strike, volatility, maturity) < 0:
        raise ValueError("finite inputs and nonnegative spot, strike, volatility, maturity required")


def _european_pair(spot, strike, rate, volatility, maturity, times=(), amounts=()):
    """Escrowed-dividend BSM: volatility applies to spot less dividend PV.

    Ex-dates <= maturity are paid before terminal exercise; dates stay fixed
    when maturity changes. This model convention is not a general stock-jump model.
    Zero spot/strike endpoints are analytic limits, avoiding undefined log(S/K).
    """
    _market(spot, strike, rate, volatility, maturity)
    prepaid = spot - bsm.pv_dividends(times, amounts, rate, maturity)
    if prepaid < 0:
        raise ValueError("dividend PV cannot exceed spot in the escrowed model")
    if prepaid == 0 or strike == 0:
        difference = prepaid - strike * math.exp(-rate * maturity)
        return max(difference, 0), max(-difference, 0)
    return (float(bsm.call_price(prepaid, strike, rate, volatility, maturity)),
            float(bsm.put_price(prepaid, strike, rate, volatility, maturity)))


def factor_prices(values, *, factor, spot=50, strike=50, rate=.05, volatility=.3,
                  maturity=1, dividend_times=(), dividend_amounts=()):
    """European call/put curves for Hull Figures 11.1/11.2 and Table 11.1.

    ``dividend_scale`` multiplies the caller's cash amounts at unchanged dates.
    Values may include zero price/strike/maturity/volatility endpoints.
    """
    baseline = dict(spot=spot, strike=strike, rate=rate, volatility=volatility, maturity=maturity)
    if factor not in (*baseline, "dividend_scale"):
        raise ValueError("unknown option price factor")
    axis = np.asarray(values, dtype=float)
    if axis.ndim != 1 or not np.all(np.isfinite(axis)):
        raise ValueError("values must be a finite one-dimensional curve axis")
    call, put = [], []
    for value in axis:
        inputs = baseline.copy()
        amounts = dividend_amounts
        if factor == "dividend_scale":
            if value < 0:
                raise ValueError("dividend scale must be nonnegative")
            amounts = np.asarray(dividend_amounts, dtype=float) * value
        else:
            inputs[factor] = float(value)
        c, p = _european_pair(**inputs, times=dividend_times, amounts=amounts)
        call.append(c)
        put.append(p)
    return dict(values=axis.copy(), call=np.asarray(call), put=np.asarray(put))


def no_dividend_bounds(spot, strike, rate, maturity, *, american=False):
    """Hull (11.1)-(11.5), with immediate exercise included for Americans.

    For negative rates, use max(K, discounted K) as the American put upper
    bound. Positive-rate Hull examples recover P <= K and intrinsic lowers.
    """
    _market(spot, strike, rate, 0, maturity)
    discounted_strike = strike * math.exp(-rate * maturity)
    call_lower = max(spot-discounted_strike, 0)
    put_lower = max(discounted_strike-spot, 0)
    if american:
        call_lower = max(call_lower, spot-strike)
        put_lower = max(put_lower, strike-spot)
    return dict(call_lower=call_lower, call_upper=spot, put_lower=put_lower,
                put_upper=max(strike, discounted_strike) if american else discounted_strike)


def bound_arbitrage(terminal_spot, spot, strike, rate, maturity, option_price, *, kind):
    """Self-financing lower-bound portfolios from Hull pp.252-254.

    Call: long call, short one share, invest spot minus option premium.
    Put: long put and one share, borrow spot plus option premium.
    Positive ``minimum_profit`` means the quote violates the lower bound;
    other quotes still return portfolio cashflows without claiming arbitrage.
    """
    _market(spot, strike, rate, 0, maturity)
    terminal = np.asarray(terminal_spot, dtype=float)
    if not np.all(np.isfinite(terminal)) or np.any(terminal < 0):
        raise ValueError("terminal stock prices must be finite and nonnegative")
    if not math.isfinite(option_price) or option_price < 0:
        raise ValueError("option price must be finite and nonnegative")
    if kind == "call":
        initial_bank = spot-option_price
        terminal_bank = initial_bank * math.exp(rate*maturity)
        profit = terminal_bank - np.minimum(terminal, strike)
        minimum_profit = terminal_bank-strike
    elif kind == "put":
        initial_bank = -(spot+option_price)
        terminal_bank = initial_bank * math.exp(rate*maturity)
        profit = np.maximum(terminal, strike) + terminal_bank
        minimum_profit = strike+terminal_bank
    else:
        raise ValueError("kind must be call or put")
    return dict(initial_bank=initial_bank, terminal_bank=terminal_bank, profit=profit,
                minimum_profit=minimum_profit)


def parity_arbitrage(terminal_spot, spot, strike, rate, maturity, call_price, put_price):
    """European, no-dividend Table 11.3 replication with zero initial net cash.

    Buy the cheap portfolio and sell the dear one. ``call_quantity`` is +1
    for long call/short put/short share, -1 for the reversed trade.
    Cash profits are nominal at maturity; bank proceeds can be negative debt.
    """
    _market(spot, strike, rate, 0, maturity)
    _market(call_price, put_price, rate, 0, maturity)
    terminal = np.asarray(terminal_spot, dtype=float)
    if not np.all(np.isfinite(terminal)) or np.any(terminal < 0):
        raise ValueError("terminal stock prices must be finite and nonnegative")
    portfolio_a = call_price + strike * math.exp(-rate*maturity)
    portfolio_c = put_price + spot
    direction = float(np.sign(portfolio_c-portfolio_a))
    initial_bank = direction*(spot+put_price-call_price)
    terminal_bank = initial_bank*math.exp(rate*maturity)
    call_payoff = np.maximum(terminal-strike, 0)
    put_payoff = np.maximum(strike-terminal, 0)
    profit = terminal_bank + direction*(call_payoff-put_payoff-terminal)
    return dict(portfolio_a=portfolio_a, portfolio_c=portfolio_c, call_quantity=direction,
                initial_bank=initial_bank, terminal_bank=terminal_bank, profit=profit)


def american_put_interval(call_price, spot, strike, rate, maturity, *, dividend_pv=0):
    """Hull (11.7)/(11.11), expressed as a put interval conditional on C.

    These American parity inequalities assume r >= 0; unlike European
    parity they must not be extended to negative rates without rederivation.
    The put interval is also clipped to max(K-S, 0) <= P <= K, and an
    American call above the stock price is rejected.
    """
    _market(spot, strike, rate, 0, maturity)
    if rate < 0:
        raise ValueError("Hull American parity interval assumes nonnegative rate")
    if not math.isfinite(call_price) or call_price < 0 or not math.isfinite(dividend_pv) or dividend_pv < 0:
        raise ValueError("call price and dividend PV must be finite and nonnegative")
    if call_price > spot:
        raise ValueError("an American call cannot exceed the stock price")
    lower = strike*math.exp(-rate*maturity)-spot
    upper = strike+dividend_pv-spot
    return dict(put_minus_call_lower=lower, put_minus_call_upper=upper,
                put_lower=max(call_price+lower, strike-spot, 0), put_upper=min(call_price+upper, strike))


def capital_structure_payoffs(terminal_assets, face_value):
    """Business Snapshot 11.1: equity is a call, debt is min(A_T,K)."""
    assets = np.asarray(terminal_assets, dtype=float)
    if not np.all(np.isfinite(assets)) or np.any(assets < 0) or not math.isfinite(face_value) or face_value < 0:
        raise ValueError("assets and face value must be finite and nonnegative")
    return dict(equity=np.maximum(assets-face_value, 0), debt=np.minimum(assets, face_value))


def exercise_comparison(spot, strike, rate, volatility, maturity, *, kind="call", steps=400):
    """No-dividend price/intrinsic comparison for sections 11.5 and 11.6.

    American minus European *on the same CRR grid* isolates the exercise
    premium; the analytic European price is also returned as a convergence
    reference. ``exercise_now`` is a numerical root decision, not a precise
    continuous-time free boundary. Zero inputs use deterministic limits.
    """
    _market(spot, strike, rate, volatility, maturity)
    if kind not in ("call", "put") or steps < 1 or int(steps) != steps:
        raise ValueError("call/put kind and a positive integer step count required")
    call, put = _european_pair(spot, strike, rate, volatility, maturity)
    european = call if kind == "call" else put
    intrinsic = max(spot-strike, 0) if kind == "call" else max(strike-spot, 0)
    if maturity == 0 or volatility == 0 or spot == 0 or strike == 0:
        tree_european = european
        american = max(european, intrinsic)
    else:
        args = (spot, strike, rate, volatility, maturity, int(steps))
        tree_european = trees.crr_price(*args, kind=kind)
        american = trees.crr_price(*args, kind=kind, american=True)
    return dict(european=european, tree_european=tree_european, american=american,
                intrinsic=intrinsic, early_exercise_premium=american-tree_european,
                exercise_gap=american-intrinsic,
                exercise_now=intrinsic > 0 and american <= intrinsic+1e-9,
                interest_deferral=strike*(1-math.exp(-rate*maturity)), put_insurance=put)


def exercise_profile(spots, strike, rate, volatility, maturity, *, kind="put", steps=400):
    """Current-spot price curves, with numerical root exercise decisions.

    A (American immediate-exercise level) and B (European/intrinsic crossing)
    must be read from distinct columns. This does not return a time-varying
    free boundary or assign printed numbers to Hull's schematic A/B labels.
    """
    axis = np.asarray(spots, dtype=float)
    if axis.ndim != 1 or not np.all(np.isfinite(axis)) or np.any(axis < 0):
        raise ValueError("spots must be a finite nonnegative one-dimensional axis")
    rows = [exercise_comparison(float(spot), strike, rate, volatility, maturity,
                                kind=kind, steps=steps) for spot in axis]
    keys = ("european", "tree_european", "american", "intrinsic", "exercise_now", "early_exercise_premium")
    result = {key: np.asarray([row[key] for row in rows], dtype=bool if key == "exercise_now" else float)
              for key in keys}
    return dict(spots=axis.copy(), **result)


def cash_dividend_tree(spot, strike, rate, volatility, maturity, dividend_times, dividend_amounts,
                       *, kind="call", american=False, steps=400):
    """Escrowed-dividend lattice for section 11.7, not a general cash-jump GBM.

    Y=S-PV(remaining dividends) follows GBM with volatility applied to Y.
    The physical stock is Y plus the remaining dividend reserve: it drops by
    each known cash amount on its ex-date. Dates in life must align with this
    uniform time grid. European expiry is after any maturity dividend;
    Americans can exercise before or after each payment, including at expiry.
    ``exercise_times`` reports levels where exercise strictly improves value.
    """
    _market(spot, strike, rate, volatility, maturity)
    if kind not in ("call", "put") or steps < 1 or int(steps) != steps:
        raise ValueError("call/put kind and positive integer steps required")
    pv = bsm.pv_dividends(dividend_times, dividend_amounts, rate, maturity)
    risky_spot = spot-pv
    if risky_spot < 0:
        raise ValueError("dividend PV cannot exceed spot in the escrowed model")
    times = np.asarray(dividend_times, dtype=float)
    amounts = np.asarray(dividend_amounts, dtype=float)
    in_life = times <= maturity
    times, amounts = times[in_life], amounts[in_life]

    def payoff(stock):
        return np.maximum(stock-strike, 0) if kind == "call" else np.maximum(strike-stock, 0)

    if maturity == 0:
        european = float(payoff(risky_spot))
        immediate = float(payoff(spot))
        return dict(price=max(european, immediate) if american else european,
                    exercise_times=(0.,) if american and immediate > european else ())
    steps = int(steps)
    dt = maturity/steps
    indices = np.rint(times/dt).astype(int)
    if np.any(np.abs(indices*dt-times) > 1e-10*max(1, maturity)):
        raise ValueError("in-life ex-dates must align with the chosen time grid")
    cash = np.zeros(steps+1)
    np.add.at(cash, indices, amounts)
    discount = math.exp(-rate*dt)
    reserve = np.zeros(steps+1)
    for i in range(steps-1, -1, -1):
        reserve[i] = discount*(cash[i+1]+reserve[i+1])
    if volatility == 0 or risky_spot == 0:
        european = float(payoff(risky_spot*math.exp(rate*maturity))) * math.exp(-rate*maturity)
        if not american:
            return dict(price=european, exercise_times=())
        candidates = sorted({0, steps, *indices.tolist()})
        values = []
        for i in candidates:
            after = risky_spot*math.exp(rate*i*dt)+reserve[i]
            immediate = max(float(payoff(after)), float(payoff(after+cash[i])))
            values.append(immediate*math.exp(-rate*i*dt))
        price = max(european, *values)
        optimal = tuple(i*dt for i, value in zip(candidates, values, strict=True)
                        if value > european+1e-9 and abs(value-price) < 1e-9)
        return dict(price=price, exercise_times=optimal)
    log_up = volatility*math.sqrt(dt)
    up = math.exp(log_up)
    probability = trees.risk_neutral_p(up, 1/up, rate, dt)
    risky_terminal = risky_spot*np.exp(log_up*(steps-2*np.arange(steps+1)))
    value = payoff(risky_terminal)
    exercised = []
    if american:
        before = payoff(risky_terminal+cash[-1])
        if np.any(before > value+1e-9):
            exercised.append(steps)
        value = np.maximum(value, before)
    for i in range(steps-1, -1, -1):
        continuation = discount*(probability*value[:-1]+(1-probability)*value[1:])
        if american:
            after = risky_spot*np.exp(log_up*(i-2*np.arange(i+1)))+reserve[i]
            immediate = np.maximum(payoff(after), payoff(after+cash[i]))
            if np.any(immediate > continuation+1e-9):
                exercised.append(i)
            value = np.maximum(continuation, immediate)
        else:
            value = continuation
    return dict(price=float(value[0]), exercise_times=tuple(i*dt for i in sorted(exercised)))
