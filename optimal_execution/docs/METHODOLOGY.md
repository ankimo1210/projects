# Methodology

## Scope and units

The project is a synthetic educational demonstrator. Time is measured in
seconds, quantity in shares, and price/cost in currency units. One trading day
is 6.5 hours and one trading year is 252 days. Annualized volatility is
converted to absolute price volatility per square-root second.

The linear temporary coefficient \(\eta\) has units
currency·second/share², permanent \(\gamma\) has currency/share, transient
\(\eta_t\) has currency/share, and resilience \(\rho\) has 1/second.

## Sign convention

Remaining inventory is always positive. Executed quantity is nonnegative:

\[
x_{k+1}=x_k-q_k,\qquad 0\le q_k\le x_k.
\]

The program sign is \(s=+1\) for a sell and \(s=-1\) for a buy. An adverse
price concession \(a_k\ge0\) gives \(P_k=S_k^0-sa_k\). The unified
implementation-shortfall expression is

\[
IS=s\left(XP_0-\sum_k q_kP_k\right)+\text{fees}.
\]

Thus positive cost is worse than arrival on either side. Tests cover one-step
examples and buy/sell symmetry.

## Unaffected price

The arithmetic synthetic mid follows

\[
S^0_{k+1}=S^0_k+\alpha_k\Delta t+\sigma_k\sqrt{\Delta t}Z_k+J_k.
\]

The base volatility is constant or U-shaped. Optional components are a
decaying deterministic alpha, a two-state volatility regime, and compound
Poisson jumps. The unaffected path never includes the agent's trades.

## Volume, spread, and liquidity

Expected interval volume equals ADV times elapsed trading-day fraction. Flat
and mean-one U-shaped profiles are supported, with mean-one lognormal
multipliers. VWAP normalizes expected step volumes; POV uses realized volume.

The spread is a positive product of base spread, intraday seasonality,
volatility response, persistent stress, and lognormal noise, floored at one
tick. Displayed bid/ask depth is positive and mean-reverts toward configured
depth. Depletion widens the reactive-book spread and replenishment restores
depth gradually.

## Impact channels

For rate \(v_k=q_k/\Delta t\), linear temporary concession and cost are

\[
g(v_k)=\eta v_k,\qquad C_k^{\text{temp}}=\eta q_k^2/\Delta t.
\]

Permanent impact is the cumulative shift \(\gamma\sum_{j<k}q_j\), with half
of the current block charged to its average execution price.

Transient displacement uses a point-impulse convention:

\[
D_{k+1}=e^{-\rho\Delta t}(D_k+\eta_tq_k).
\]

The block-average execution concession is
\(D_k+\tfrac12\eta_tq_k\). Exponential and power-law propagator kernels are
available. The empirical square-root diagnostic

\[
I(Q)=Y\sigma_{\text{day}}\sqrt{Q/ADV}
\]

is reported separately and never added to the linear model.

## Default calibration

The default scenario deviates deliberately from the task statement's
illustrative values, and `configs/default.yaml` documents the arithmetic:

- The written recursion \(D_{k+1}=e^{-\rho\Delta t}D_k+\eta_tq_k\) adds the
  newest impulse undecayed, which makes adjacent-step trades interact at full
  strength and the discrete scheduling quadratic form indefinite; the
  point-impulse form above is the continuous-time-faithful discretization and
  keeps the optimization well posed.
- \(X=60{,}000\) shares is 15.6% of expected interval volume, so TWAP fits
  inside the 20% participation cap while front-loaded schedules hit it; the
  illustrative \(X=100{,}000\) requires 26% participation and cannot complete
  under the cap at all.
- \(\eta=10^{-4}\), \(\gamma=2.5\times10^{-7}\) put schedule costs at a
  visible bps scale with \(\kappa T\approx1.5\); the illustrative
  \(\eta=2.5\times10^{-7}\), \(\gamma=5\times10^{-8}\) imply \(\kappa T\approx30\)
  and sub-0.01 bp impact, which hides every trade-off the lab exists to show.
  The sensitivity sweeps in Experiment A still cover such extremes.
- LOB market-order intensity is derived from ADV
  (2 sides × rate × mean size = ADV rate), so the schedule world and the
  reactive book share one volume scale by construction.

## Almgren–Chriss

The continuous mean-variance objective is

\[
J[x]=\int_0^T\left(\eta\dot{x}_t^2+\lambda\sigma^2x_t^2\right)dt,
\qquad \kappa=\sqrt{\lambda\sigma^2/\eta}.
\]

The analytical trajectory is

\[
x_t^*=X\frac{\sinh(\kappa(T-t))}{\sinh(\kappa T)}.
\]

A stable exponential form avoids overflow, and \(\kappa T<10^{-6}\) uses
the exact TWAP limit. Discrete child orders are inventory differences. The
efficient frontier reports expected cost and timing-risk standard deviation in
currency and bps.

## Resilient execution

The risk-neutral exponential Obizhaeva–Wang-style schedule has equal initial
and terminal blocks \(X/(\rho T+2)\) and constant interior rate
\(\rho X/(\rho T+2)\). A discrete constrained quadratic program minimizes

\[
C(q)=\tfrac12\eta_t q^\top Mq,\qquad
M_{ij}=G(|i-j|\Delta t),\quad \mathbf{1}^\top q=X,\quad q\ge0.
\]

An active-set solve handles nonnegativity. A risk-averse exact OW solution is
not implemented; risk aversion belongs to the AC strategic layer.

## Reactive limit-order book

The aggregate state contains best bid/ask, spread, L1 depth, deeper-book
density, queue imbalance, recent signed flow and return, stress, volatility,
unaffected mid, permanent footprint, transient displacement, agent inventory,
time, and one outstanding limit order.

Queue imbalance is

\[
I_k=\frac{Q_k^b-Q_k^a}{Q_k^b+Q_k^a}\in[-1,1].
\]

Exogenous market-order intensities are capped log-linear functions of
imbalance, recent return, stress, and latent short-horizon alpha. Limit arrivals
and cancellations reshape depth. All primitive random draws are made before
state-dependent transforms, enabling common random numbers across policies.

An agent market order consumes touch depth and walks a linear deeper-book
density. In reactive mode it also widens spread and adds permanent/transient
footprint. In replay mode these agent state mutations are suppressed; exogenous
events remain paired.

## Passive fills and adverse selection

The single outstanding agent order has FIFO queue ahead. Opposite market flow
first consumes that queue, then fills at most the remaining agent quantity.
Queue cancellations erode the amount ahead. If the market trades through the
limit price, the remainder fills and is marked as crossed. A latent alpha tilts
both opposite flow and the next mid move, producing stylized statistical
adverse selection. No order can be filled twice.

## Strategies

The classical world includes immediate, TWAP, expected-volume VWAP, realized
POV, Almgren–Chriss, and resilience-aware schedules. The LOB world includes
market-only schedule followers, adaptive POV, limit-only, and a mixed urgency/
imbalance heuristic. Residual RL scales the AC slice; free RL uses a TWAP-sized
action grid. Every policy passes through the same environment safety layer.

## Transaction-cost analysis

Path-level output records total implementation shortfall, bps, exact synthetic
components, completion, inventory, participation, fill/cleanup shares, order
counts, exposure, and violations. Summary output includes mean, median,
standard deviation, RMSE, 1/5/25/50/75/95/99% quantiles, VaR, CVaR, worst case,
and a bootstrap interval for the mean.

Timing, spread, temporary, permanent, transient, fee, cleanup, spread-capture,
and adverse-selection components are latent synthetic ground truth. Such a
decomposition is not unique or directly observable in real markets.

## Common-random-number protocol

Named deterministic streams derive from the master seed. In schedule-world
comparisons, all strategies receive identical price, volume, and spread arrays.
In LOB comparisons, all policies receive identical primitive scenario draws;
realized state then diverges because actions change the reactive market. Train,
validation, test, stress, ablation, and misspecification purposes use disjoint
seed labels.
