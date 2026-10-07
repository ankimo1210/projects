"""Private §36.4 Schwartz–Moon business simulation, with explicit accounting choices.

Defaults are the quarterly, million-USD inputs in Schwartz and Moon (2000),
Exhibit 2 (Financial Analysts Journal 56(3), pp. 62–75). Revenue R is a flow per
quarter; cash X and tax loss carry L are stocks. Growth mu has units 1/quarter;
sigma has units 1/sqrt(quarter) and eta units growth/sqrt(quarter). The annual
continuously compounded interest rate is converted by dividing it by four.

Source: https://www.anderson.ucla.edu/faculty/eduardo.schwartz/articles/70.pdf
The source does not fully determine discrete revenue timing, terminal earnings
annualization, loss-carry exhaustion within a step, or the original option
buckets and dates. This module implements the stated conventions below; it
does not claim to reproduce the printed 5457M, 27.9% or stock price 12.42.
"""

import math
from dataclasses import dataclass, fields

import numpy as np


@dataclass(frozen=True)
class BusinessModel:
    """Quarter-based parameters; monetary flows/stocks are in million USD.

    The two Brownian shocks are independent, matching the source rho=0 case.
    Drift risk prices subtract lambda_R*sigma and lambda_mu*eta under Q.
    Production financing, optimized abandonment and optimal employee-option
    exercise are outside this private lesson.
    """

    initial_revenue: float = 356.0
    initial_growth: float = 0.11
    initial_cash: float = 906.0
    initial_loss_carry: float = 559.0
    revenue_volatility: float = 0.10
    long_revenue_volatility: float = 0.05
    growth_volatility: float = 0.03
    long_growth: float = 0.015
    growth_reversion: float = 0.07
    volatility_reversion: float = 0.07
    growth_volatility_reversion: float = 0.07
    revenue_risk_price: float = 0.01
    growth_risk_price: float = 0.0
    cogs_fraction: float = 0.75
    other_variable_fraction: float = 0.19
    fixed_cost: float = 75.0
    tax_rate: float = 0.35
    annual_rate: float = 0.05
    horizon_quarters: int = 100

    def __post_init__(self):
        values = [getattr(self, item.name) for item in fields(self)]
        if not np.isfinite(values).all():
            raise ValueError("finite business parameters required")
        nonnegative = [
            self.initial_revenue,
            self.initial_cash,
            self.initial_loss_carry,
            self.revenue_volatility,
            self.long_revenue_volatility,
            self.growth_volatility,
            self.growth_reversion,
            self.volatility_reversion,
            self.growth_volatility_reversion,
            self.cogs_fraction,
            self.other_variable_fraction,
            self.fixed_cost,
        ]
        if min(nonnegative) < 0 or not 0 <= self.tax_rate <= 1:
            raise ValueError("nonnegative stocks/volatilities/costs and tax in [0,1] required")
        if (
            isinstance(self.horizon_quarters, bool)
            or self.horizon_quarters < 1
            or int(self.horizon_quarters) != self.horizon_quarters
        ):
            raise ValueError("positive whole-quarter horizon required")


def _time_step(dt):
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("positive finite quarter time step required")


def business_factor_step(revenue, growth, time, dt, normal_revenue, normal_growth, model):
    """Advance R and mu using old mu/sigma and exact frozen-eta OU variance.

    Time and dt are quarters. Sigma(t) decays to its long-run level; eta(t)
    decays to zero. The supplied standard-normal shocks must be independent
    under the source rho=0 assumption; broadcasting supports scalar/path input.

    Eq. 18 of the original paper prints an additional sqrt(dt) on OU noise.
    At its dt=1 quarter this has no effect. Subdivisions here omit that factor:
    Var(mu_next | mu)=eta(t)^2*(1-exp(-2*kappa*dt))/(2*kappa), with limit
    eta(t)^2*dt at kappa=0. Eta and sigma are frozen only within each step;
    their time variation and the integrated stochastic mu in R are approximated
    by step refinement, rather than claimed as exact continuous-time paths.
    """
    _time_step(dt)
    if not np.isfinite(time) or time < 0:
        raise ValueError("nonnegative finite quarter time required")
    R, mu, zR, zmu = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (revenue, growth, normal_revenue, normal_growth)]
    )
    if not all(np.isfinite(x).all() for x in (R, mu, zR, zmu)) or np.any(R < 0):
        raise ValueError("finite compatible factors/shocks and nonnegative revenue required")
    sigma = model.long_revenue_volatility + (
        model.revenue_volatility - model.long_revenue_volatility
    ) * math.exp(-model.volatility_reversion * time)
    eta = model.growth_volatility * math.exp(-model.growth_volatility_reversion * time)
    kappa = model.growth_reversion
    if kappa == 0:
        mean_growth = mu - model.growth_risk_price * eta * dt
        variance_growth = eta**2 * dt
    else:
        decay = math.exp(-kappa * dt)
        duration = -math.expm1(-kappa * dt) / kappa
        mean_growth = (
            decay * mu + (1 - decay) * model.long_growth - model.growth_risk_price * eta * duration
        )
        variance_growth = eta**2 * -math.expm1(-2 * kappa * dt) / (2 * kappa)
    with np.errstate(over="raise", invalid="raise"):
        next_revenue = R * np.exp(
            (mu - model.revenue_risk_price * sigma - 0.5 * sigma**2) * dt
            + sigma * math.sqrt(dt) * zR
        )
        next_growth = mean_growth + math.sqrt(variance_growth) * zmu
    return {
        "revenue": next_revenue,
        "growth": next_growth,
        "revenue_volatility": sigma,
        "growth_volatility": eta,
        "conditional_growth_mean": mean_growth,
        "conditional_growth_variance": variance_growth,
    }


def business_cash_step(cash, loss_carry, revenue, dt, model, *, alive=True):
    """Post a step's retained after-tax cash and an absorbing cash<=0 default.

    Revenue and fixed costs are quarterly flows multiplied by dt. Start cash
    earns expm1((annual_rate/4)*dt); that interest enters taxable pre-tax profit.
    Profit first consumes L, then its excess is taxed; losses increase L and
    receive no refund. This defines the source's unspecified discrete crossing.
    Cash is not distributed before the terminal date. A default deficit remains
    visible in cash, while all later cashflows, interest and taxes are zero.
    """
    _time_step(dt)
    X, L, R, active = np.broadcast_arrays(
        np.asarray(cash, dtype=float),
        np.asarray(loss_carry, dtype=float),
        np.asarray(revenue, dtype=float),
        np.asarray(alive, dtype=bool),
    )
    if not all(np.isfinite(x).all() for x in (X, L, R)) or np.any(L < 0) or np.any(R < 0):
        raise ValueError(
            "finite compatible cash/loss/revenue and nonnegative loss/revenue required"
        )
    active = active & (X > 0)
    operations = np.where(
        active,
        ((1 - model.cogs_fraction - model.other_variable_fraction) * R - model.fixed_cost) * dt,
        0,
    )
    interest = np.where(active, X * math.expm1(model.annual_rate * dt / 4), 0)
    pretax = operations + interest
    tax = np.where(active, model.tax_rate * np.maximum(pretax - L, 0), 0)
    next_loss = np.where(active, np.maximum(L - pretax, 0), L)
    cashflow = pretax - tax
    next_cash = X + cashflow
    return {
        "cash": next_cash,
        "loss_carry": next_loss,
        "alive": active & (next_cash > 0),
        "operating_cashflow": operations,
        "cash_interest": interest,
        "pretax_cashflow": pretax,
        "tax": tax,
        "cashflow": cashflow,
    }


def _estimate(values, antithetic):
    samples = (
        (values[: len(values) // 2] + values[len(values) // 2 :]) / 2 if antithetic else values
    )
    error = float(samples.std(ddof=1) / math.sqrt(len(samples))) if len(samples) > 1 else None
    return float(samples.mean()), error, len(samples)


def simulate_business_value(
    model,
    *,
    n_paths,
    seed,
    substeps_per_quarter,
    revenue_timing,
    terminal_multiple,
    terminal_profit_periods,
    floor_terminal_profit=True,
    antithetic=True,
    record_paths=0,
):
    """Simulate enterprise value under Q with caller-selected accounting timing.

    revenue_timing is 'start' or 'end' for each accounting substep. At horizon,
    each survivor receives cash_T plus terminal_multiple times quarterly EBITDA
    times terminal_profit_periods (1=quarterly, 4=annualized). No interim payout
    is added. floor_terminal_profit=True floors EBITDA at zero; the alternate
    signed-EBITDA convention is available explicitly. Payout is discounted once
    at the annual rate over horizon_quarters/4 years; defaulted paths pay zero.

    The first and second half of paths are antithetic pairs at every step.
    Standard errors use independent pair averages, not the correlated raw
    paths. Fewer than two independent samples gives standard_error=None.
    record_paths stores only the first requested histories, with a zero root
    cashflow; defaulted factor and accounting states are frozen thereafter.
    Seeded estimates and refinement checks are reproducible, but cannot certify
    the source's printed prices without its missing accounting/capital inputs.
    """
    controls = [n_paths, substeps_per_quarter, record_paths]
    if (
        not np.isfinite(controls).all()
        or any(isinstance(x, bool) or int(x) != x for x in controls)
        or n_paths < 2
        or substeps_per_quarter < 1
        or not 0 <= record_paths <= n_paths
    ):
        raise ValueError("integer paths>=2, positive subdivisions and valid record_paths required")
    n_paths, substeps_per_quarter, record_paths = map(int, controls)
    if antithetic and n_paths % 2:
        raise ValueError("even n_paths required for antithetic pairs")
    if revenue_timing not in ("start", "end"):
        raise ValueError("revenue timing must be start or end")
    if (
        not np.isfinite([terminal_multiple, terminal_profit_periods]).all()
        or terminal_multiple < 0
        or terminal_profit_periods <= 0
    ):
        raise ValueError("nonnegative terminal multiple and positive profit periods required")
    dt = 1 / substeps_per_quarter
    steps = int(model.horizon_quarters) * substeps_per_quarter
    R = np.full(n_paths, model.initial_revenue, dtype=float)
    mu = np.full(n_paths, model.initial_growth, dtype=float)
    X = np.full(n_paths, model.initial_cash, dtype=float)
    L = np.full(n_paths, model.initial_loss_carry, dtype=float)
    active = X > 0
    default_time = np.where(active, np.nan, 0.0)
    cashflow_total = np.zeros(n_paths)
    history = {}
    if record_paths:
        for key in ("revenue", "growth", "cash", "loss_carry", "tax", "cashflow", "cash_interest"):
            history[key] = np.zeros((steps + 1, record_paths))
        for key, value in (("revenue", R), ("growth", mu), ("cash", X), ("loss_carry", L)):
            history[key][0] = value[:record_paths]
        history["time_quarters"] = np.arange(steps + 1) * dt
    rng = np.random.default_rng(seed)
    for step in range(steps):
        draw = rng.standard_normal((n_paths // 2 if antithetic else n_paths, 2))
        if antithetic:
            draw = np.concatenate((draw, -draw), axis=0)
        factors = business_factor_step(R, mu, step * dt, dt, draw[:, 0], draw[:, 1], model)
        next_R = np.where(active, factors["revenue"], R)
        next_mu = np.where(active, factors["growth"], mu)
        accounting = business_cash_step(
            X, L, R if revenue_timing == "start" else next_R, dt, model, alive=active
        )
        newly_failed = active & ~accounting["alive"]
        default_time[newly_failed] = (step + 1) * dt
        R, mu = next_R, next_mu
        X, L, active = accounting["cash"], accounting["loss_carry"], accounting["alive"]
        cashflow_total += accounting["cashflow"]
        if record_paths:
            for key, value in (("revenue", R), ("growth", mu)):
                history[key][step + 1] = value[:record_paths]
            for key in ("cash", "loss_carry", "tax", "cashflow", "cash_interest"):
                history[key][step + 1] = accounting[key][:record_paths]
    profit = (1 - model.cogs_fraction - model.other_variable_fraction) * R - model.fixed_cost
    terminal_business_value = (
        terminal_multiple
        * terminal_profit_periods
        * (np.maximum(profit, 0) if floor_terminal_profit else profit)
    )
    distribution = np.where(active, X + terminal_business_value, 0)
    discount = math.exp(-model.annual_rate * model.horizon_quarters / 4)
    path_pv = distribution * discount
    value, standard_error, independent_samples = _estimate(path_pv, antithetic)
    probability, probability_se, _ = _estimate((~active).astype(float), antithetic)
    return {
        "value": value,
        "standard_error": standard_error,
        "independent_samples": independent_samples,
        "bankruptcy_probability": probability,
        "bankruptcy_standard_error": probability_se,
        "path_pv": path_pv,
        "terminal_distribution": distribution,
        "terminal_cash": X,
        "terminal_business_value": np.where(active, terminal_business_value, 0),
        "terminal_operating_profit": profit,
        "revenue": R,
        "growth": mu,
        "loss_carry": L,
        "cashflow_total": cashflow_total,
        "default_time": default_time,
        "alive": active,
        "history": history,
        "accounting": {
            "revenue_timing": revenue_timing,
            "terminal_profit_periods": terminal_profit_periods,
            "floor_terminal_profit": floor_terminal_profit,
            "cash_interest": "start cash, compounded at annual_rate/4, taxable",
            "default": "first accounting endpoint with cash<=0; absorbing",
            "units": "quarter; million USD; annual continuous discount rate",
            "source_price_reproduction": "unverified: source timing and capital inputs incomplete",
        },
    }


@dataclass(frozen=True)
class CapitalEvent:
    """Caller-specified cash/share event, quarter date and million-share counts.

    Option strike is USD/share, so option_shares*option_strike is million USD.
    Debt amounts are million USD and coupons must already be after tax. Caller
    sets principal_payment=0 for converted principal, unless another debt is
    paid at the same event. This is a bookkeeping event, not an exercise rule.
    """

    time_quarters: float
    option_shares: float = 0.0
    option_strike: float = 0.0
    conversion_shares: float = 0.0
    after_tax_coupon: float = 0.0
    principal_payment: float = 0.0

    def __post_init__(self):
        values = [getattr(self, item.name) for item in fields(self)]
        if not np.isfinite(values).all() or min(values) < 0:
            raise ValueError("finite nonnegative dated capital-event inputs required")


def capitalized_equity(
    enterprise_terminal, survival, *, initial_shares, events, annual_rate, horizon_quarters
):
    """Allocate a terminal enterprise value using fully supplied capital events.

    Each dated cash receipt/payment is accumulated to the terminal quarter,
    added once to enterprise_terminal, then discounted once from that date.
    Existing and issued shares are in millions. Specified options/conversions
    occur on every terminal-survivor path; this mimics the source's simplistic
    unconditional survivor exercise assumption, not economic optimization.
    Equity is floored at zero, and defaulted paths pay zero. The financing
    allocation does not re-simulate cash/default dynamics (the source assumes
    offsetting debt refinancing). Missing bucket dates, shares and strikes are
    deliberately caller inputs; these events cannot establish the printed 12.42.
    """
    enterprise = np.asarray(enterprise_terminal, dtype=float)
    survived = np.asarray(survival, dtype=bool)
    if (
        enterprise.ndim != 1
        or enterprise.shape != survived.shape
        or not len(enterprise)
        or not np.isfinite(enterprise).all()
        or not np.isfinite([initial_shares, annual_rate, horizon_quarters]).all()
        or initial_shares <= 0
        or horizon_quarters <= 0
    ):
        raise ValueError("finite matching terminal paths, positive shares and horizon required")
    events = tuple(events)
    if any(event.time_quarters > horizon_quarters for event in events):
        raise ValueError("capital event date lies beyond the horizon")
    proceeds = sum(event.option_shares * event.option_strike for event in events)
    debt = sum(event.after_tax_coupon + event.principal_payment for event in events)
    shares = initial_shares + sum(event.option_shares + event.conversion_shares for event in events)
    adjustment = sum(
        (
            event.option_shares * event.option_strike
            - event.after_tax_coupon
            - event.principal_payment
        )
        * math.exp(annual_rate * (horizon_quarters - event.time_quarters) / 4)
        for event in events
    )
    equity = np.where(survived, np.maximum(enterprise + adjustment, 0), 0)
    per_share_pv = equity * math.exp(-annual_rate * horizon_quarters / 4) / shares
    return {
        "shares": shares,
        "exercise_proceeds": proceeds,
        "debt_service": debt,
        "terminal_capital_adjustment": adjustment,
        "equity_terminal": equity,
        "per_share_path_pv": per_share_pv,
        "per_share_value": float(per_share_pv.mean()),
        "source_capital_reconstruction": "unverified: caller-specified events",
    }
