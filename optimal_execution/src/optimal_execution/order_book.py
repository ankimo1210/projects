"""Simplified reactive limit-order-book simulator.

Purpose: a transparent synthetic environment that *reacts* to the execution
agent — not exchange realism. One aggregated level-1 quote per side plus a
deeper-liquidity density; state-dependent exogenous flow; a latent short-
horizon alpha that drives both order flow and future mid moves (this is the
adverse-selection channel).

Design choices (documented in docs/RL_ENVIRONMENT.md):

* The *unaffected* mid ``s0`` never responds to the agent.
* The agent's market orders (and forced terminal liquidation) add permanent
  (gamma) and transient (eta_t, decaying at rho) impact to the *impacted*
  fair mid ``mid = s0 - sign * (gamma * cum_mkt + D)``; passive limit fills
  add none (they provide liquidity). This is the classical <-> LOB mapping.
* Temporary impact in this world is endogenous: walking the visible book
  plus the depletion-driven spread widening — there is no separate eta.
* Exogenous market-order volume per sub-step per side is
  ``count(Poisson-inverse from a pre-drawn uniform) * mean size`` with the
  intensity a capped log-linear function of imbalance, recent return, stress
  and the latent alpha. Pre-drawn uniforms give common random numbers across
  strategies; state-dependence enters only through the intensity.
* In ``reactive=False`` (replay) mode the same exogenous draws evolve the
  book, but agent actions leave *no* trace: depth is not consumed, quotes and
  the mid do not move, and impact states stay untouched.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Config
from .price_process import alpha_profile, sigma_profile, u_shape_factor
from .volume import volume_weights


def inverse_poisson(u: float, lam: float, max_k: int = 40) -> int:
    """Poisson count via inverse transform from one uniform (small lambda)."""
    if lam <= 0:
        return 0
    p = np.exp(-lam)
    cdf = p
    k = 0
    while u > cdf and k < max_k:
        k += 1
        p *= lam / k
        cdf += p
    return k


@dataclass
class AgentLimitOrder:
    """The agent's single outstanding passive order (sell side for a seller)."""

    price: float
    qty: float
    queue_ahead: float
    age_sub_steps: int = 0
    filled: float = 0.0


@dataclass
class SubStepFlow:
    """Exogenous + agent-relevant outcomes of one sub-step."""

    buy_mo_volume: float = 0.0
    sell_mo_volume: float = 0.0
    buy_mo_count: int = 0
    sell_mo_count: int = 0
    lo_count: int = 0
    cancel_count: int = 0
    agent_limit_fill: float = 0.0
    agent_fill_price: float = 0.0
    crossed: bool = False  # order filled because price traded through it
    # market state captured at the fill instant (exact TCA decomposition)
    fill_s0: float = 0.0
    fill_mid: float = 0.0
    fill_perm: float = 0.0
    fill_D: float = 0.0


@dataclass
class BookState:
    """Snapshot of observable + latent state (for logging and plots)."""

    t: float
    s0: float
    mid: float
    best_bid: float
    best_ask: float
    spread: float
    bid_depth: float
    ask_depth: float
    imbalance: float
    D: float
    eps_alpha: float
    stress: float
    recent_flow: float
    recent_return: float
    vol_mult: float


class OrderBook:
    """One-episode reactive book. All quantities are per-share currency/shares."""

    def __init__(
        self,
        cfg: Config,
        rng: np.random.Generator,
        n_sub_total: int,
        reactive: bool = True,
    ) -> None:
        self.cfg = cfg
        self.reactive = reactive
        self.n_sub_total = n_sub_total
        self.sub_dt = cfg.horizon_seconds / n_sub_total
        liq = cfg.liquidity

        # --- pre-drawn exogenous randomness (CRN across strategies) ---------
        self._z_mid = rng.standard_normal(n_sub_total)
        self._z_alpha = rng.standard_normal(n_sub_total)
        self._u_buy = rng.random(n_sub_total)
        self._u_sell = rng.random(n_sub_total)
        self._u_lo = rng.random(n_sub_total)
        self._u_cancel = rng.random(n_sub_total)
        self._u_stress = rng.random(n_sub_total)
        self._z_depth = rng.standard_normal((n_sub_total, 2))
        s = cfg.volume_mult_sigma
        self._vol_mult_episode = float(rng.lognormal(-0.5 * s * s, s)) if s > 0 else 1.0

        # --- deterministic profiles on the sub-step grid --------------------
        self._sigma_sub = sigma_profile(cfg, n_sub_total)  # currency/share/sqrt(s)
        self._alpha_sub = alpha_profile(cfg, n_sub_total)  # currency/share/s
        self._u_shape_sub = u_shape_factor(n_sub_total, cfg.volume_u_amplitude)
        self._vol_weights = volume_weights(cfg, n_sub_total)

        # --- state -----------------------------------------------------------
        self.k_sub = 0
        self.s0 = cfg.arrival_price
        self.D = 0.0  # transient displacement of the agent (adverse magnitude)
        self.cum_agent_mkt = 0.0  # shares executed via agent market orders
        self.eps_alpha = 0.0  # latent short-horizon alpha (currency/share units)
        self.stress = 0.0
        self.recent_flow = 0.0  # EMA of signed exogenous MO volume (buy - sell)
        self.recent_return = 0.0  # EMA of sub-step mid returns (currency)
        self.target_depth = liq.depth_shares
        self.bid_depth = float(
            np.clip(liq.depth_shares * np.exp(0.2 * rng.standard_normal()), 200, None)
        )
        self.ask_depth = float(
            np.clip(liq.depth_shares * np.exp(0.2 * rng.standard_normal()), 200, None)
        )
        self._base_spread = cfg.spread_bps * 1e-4 * cfg.arrival_price
        self.spread = max(self._base_spread, cfg.tick_size)
        self._ema_lambda = 0.85  # per sub-step EMA decay for flow/return

        # deeper-book density: shares available per tick beyond L1
        self.deep_density = liq.deep_liquidity_mult * liq.depth_shares / 10.0

    # ------------------------------------------------------------------ props
    @property
    def sign(self) -> int:
        return self.cfg.sign

    @property
    def mid(self) -> float:
        """Impacted fair mid seen by everyone (agent impact included)."""
        imp = self.cfg.impact.permanent_gamma * self.cum_agent_mkt + self.D
        return self.s0 - self.sign * imp

    @property
    def best_bid(self) -> float:
        return self.mid - 0.5 * self.spread

    @property
    def best_ask(self) -> float:
        return self.mid + 0.5 * self.spread

    @property
    def imbalance(self) -> float:
        tot = self.bid_depth + self.ask_depth
        return (self.bid_depth - self.ask_depth) / tot if tot > 0 else 0.0

    def snapshot(self) -> BookState:
        return BookState(
            t=self.k_sub * self.sub_dt,
            s0=self.s0,
            mid=self.mid,
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            spread=self.spread,
            bid_depth=self.bid_depth,
            ask_depth=self.ask_depth,
            imbalance=self.imbalance,
            D=self.D,
            eps_alpha=self.eps_alpha,
            stress=self.stress,
            recent_flow=self.recent_flow,
            recent_return=self.recent_return,
            vol_mult=self._vol_mult_episode,
        )

    # ------------------------------------------------------------- agent side
    def market_order(self, q: float) -> tuple[float, float, dict[str, float]]:
        """Execute an agent market order of q shares (selling hits the bid).

        Returns (executed_qty, cash_proceeds_or_cost, detail). ``detail``
        carries the latent cost decomposition versus the *unaffected* mid.
        In replay mode the book state is left untouched.
        """
        if q <= 0:
            return 0.0, 0.0, {"spread": 0.0, "walk": 0.0, "permanent": 0.0, "transient": 0.0}
        cfg = self.cfg
        tick = cfg.tick_size
        sign = self.sign
        depth = self.bid_depth if sign > 0 else self.ask_depth
        touch = self.best_bid if sign > 0 else self.best_ask

        l1 = min(q, depth)
        overflow = q - l1
        # overflow walks the deeper book at deep_density shares per tick;
        # average extra concession = tick * (1 + levels) / 2 beyond one tick.
        levels = overflow / max(self.deep_density, 1.0)
        walk_conc = tick * (1.0 + 0.5 * levels) if overflow > 0 else 0.0
        avg_price = touch - sign * (overflow / max(q, 1e-12)) * walk_conc

        # latent decomposition vs unaffected mid s0 (positive = adverse).
        # Exactly mirrors the executed price: p = s0 -/+ (spread/2 + walk_share
        # + perm_state + D_state); the *own* permanent/transient impact of this
        # trade only moves future prices, so it is charged to later fills.
        pre_half_spread = 0.5 * self.spread
        perm_state = cfg.impact.permanent_gamma * self.cum_agent_mkt
        detail = {
            "spread": pre_half_spread * q,
            "walk": (overflow * walk_conc),
            "permanent": perm_state * q,
            "transient": self.D * q,
        }

        if self.reactive:
            # consume visible liquidity and register impact
            if sign > 0:
                self.bid_depth = max(self.bid_depth - l1, 50.0)
            else:
                self.ask_depth = max(self.ask_depth - l1, 50.0)
            self.D += cfg.impact.transient_eta * q
            self.cum_agent_mkt += q
            # depletion widens the spread until replenishment catches up
            deficit = max(0.0, 1.0 - min(self.bid_depth, self.ask_depth) / self.target_depth)
            self.spread = max(self.spread * (1.0 + 0.6 * deficit), tick)

        cash = q * avg_price
        return q, cash, detail

    def agent_improve_quote(self) -> None:
        """An improving limit order tightens the touch by one tick (reactive)."""
        if self.reactive:
            self.spread = max(self.spread - self.cfg.tick_size, self.cfg.tick_size)

    # -------------------------------------------------------------- evolution
    def _intensity(self, base: float, tilt: float) -> float:
        lob = self.cfg.lob
        lam = base * float(np.exp(min(tilt, 10.0)))
        return min(lam, lob.intensity_cap_mult * base)

    def evolve_substep(self, order: AgentLimitOrder | None) -> SubStepFlow:
        """Advance one sub-step: flow, fills, depths, spread, mid, alpha."""
        cfg, lob, liq = self.cfg, self.cfg.lob, self.cfg.liquidity
        k = self.k_sub
        ds = self.sub_dt
        flow = SubStepFlow()

        # 1) latent alpha AR(1) (currency units via bps of arrival)
        a_scale = lob.adverse_alpha_sigma_bps * 1e-4 * cfg.arrival_price
        self.eps_alpha = lob.adverse_alpha_phi * self.eps_alpha + a_scale * self._z_alpha[k]

        # 2) stress regime (persistent)
        if liq.stress_prob_per_step > 0:
            p = liq.stress_prob_per_step / max(lob.sub_steps_per_decision, 1)
            if self.stress == 0.0 and self._u_stress[k] < p:
                self.stress = 1.0
            elif self.stress == 1.0 and self._u_stress[k] > 0.9:
                self.stress = 0.0

        # 3) state-dependent exogenous market-order flow
        eps_norm = np.tanh(self.eps_alpha / max(a_scale * 3.0, 1e-12))
        ret_norm = self.recent_return / max(cfg.arrival_price * 1e-4, 1e-12)  # in bps
        base_tilt = (
            lob.imbalance_beta0
            + lob.imbalance_beta2 * 1e-2 * ret_norm
            + lob.imbalance_beta3 * self.stress
            + lob.adverse_alpha_to_flow * eps_norm
        )
        vol_season = self._vol_weights[k] * self._vol_mult_episode
        mo_rate = cfg.mo_rate_per_side
        lam_buy = self._intensity(
            mo_rate * vol_season, base_tilt + lob.imbalance_beta1 * self.imbalance
        )
        lam_sell = self._intensity(
            mo_rate * vol_season, -base_tilt - lob.imbalance_beta1 * self.imbalance
        )
        n_buy = inverse_poisson(self._u_buy[k], lam_buy * ds)
        n_sell = inverse_poisson(self._u_sell[k], lam_sell * ds)
        v_buy = n_buy * lob.market_order_size_mean
        v_sell = n_sell * lob.market_order_size_mean
        flow.buy_mo_count, flow.sell_mo_count = n_buy, n_sell
        flow.buy_mo_volume, flow.sell_mo_volume = v_buy, v_sell

        # 4) agent passive order interacts with opposite flow (fills.py logic
        #    is inlined for the queue mechanics; see fills.match_passive)
        if order is not None and order.qty - order.filled > 1e-9:
            from .fills import match_passive  # local import to avoid cycle

            fill_qty, crossed = match_passive(self, order, v_buy if self.sign > 0 else v_sell)
            if fill_qty > 0:
                flow.agent_limit_fill = fill_qty
                flow.agent_fill_price = order.price
                flow.crossed = crossed
                flow.fill_s0 = self.s0
                flow.fill_mid = self.mid
                flow.fill_perm = cfg.impact.permanent_gamma * self.cum_agent_mkt
                flow.fill_D = self.D
            order.age_sub_steps += 1

        # 5) market orders consume opposite depth (exogenous consumption)
        self.ask_depth = max(self.ask_depth - v_buy, 50.0)
        self.bid_depth = max(self.bid_depth - v_sell, 50.0)

        # 6) limit-order arrivals and cancellations reshape depth
        lam_lo = lob.limit_order_rate_mult * cfg.mo_rate_per_side * vol_season
        lam_cx = lob.cancel_rate_mult * cfg.mo_rate_per_side
        n_lo = inverse_poisson(self._u_lo[k], 2.0 * lam_lo * ds)  # both sides pooled
        n_cx = inverse_poisson(self._u_cancel[k], 2.0 * lam_cx * ds)
        flow.lo_count, flow.cancel_count = n_lo, n_cx
        # mean-reversion toward target + stochastic reshaping
        rep = liq.replenish_rate
        noise = np.exp(liq.depth_sigma * 0.3 * self._z_depth[k])
        self.bid_depth = max(
            (self.bid_depth + rep * (self.target_depth - self.bid_depth)) * noise[0]
            + 0.5 * (n_lo - n_cx) * lob.limit_order_size_mean,
            50.0,
        )
        self.ask_depth = max(
            (self.ask_depth + rep * (self.target_depth - self.ask_depth)) * noise[1]
            + 0.5 * (n_lo - n_cx) * lob.limit_order_size_mean,
            50.0,
        )

        # 7) unaffected mid evolves (exogenous only): diffusion + alpha drift
        drift = self._alpha_sub[k] + lob.adverse_alpha_to_drift * self.eps_alpha / max(
            cfg.horizon_seconds / cfg.n_decision_steps, 1.0
        )
        d_mid = drift * ds + self._sigma_sub[k] * np.sqrt(ds) * self._z_mid[k]
        prev_mid = self.mid
        self.s0 += d_mid

        # 8) transient displacement decays; spread relaxes toward base level
        self.D *= float(np.exp(-cfg.impact.resilience_rho * ds))
        u_spread = self._u_shape_sub[k]
        stress_mult = 1.0 + (liq.spread_stress_mult - 1.0) * self.stress
        target_spread = max(self._base_spread * u_spread * stress_mult, cfg.tick_size)
        self.spread += 0.3 * (target_spread - self.spread)
        deficit = max(0.0, 1.0 - min(self.bid_depth, self.ask_depth) / self.target_depth)
        self.spread = max(self.spread * (1.0 + 0.15 * deficit), cfg.tick_size)

        # 9) EMAs for observation features
        lam_e = self._ema_lambda
        self.recent_flow = lam_e * self.recent_flow + (1 - lam_e) * (v_buy - v_sell)
        self.recent_return = lam_e * self.recent_return + (1 - lam_e) * (self.mid - prev_mid)

        self.k_sub += 1
        return flow
