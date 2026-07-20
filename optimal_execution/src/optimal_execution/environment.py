"""Gym-style execution environment on top of the reactive LOB simulator.

One episode = one parent order (default: sell X shares over T seconds) with
``n_decision_steps`` agent decisions; between decisions the book evolves for
``lob.sub_steps_per_decision`` sub-steps.

Action space (discrete, 15 = 5 x 3):

    market multiplier  m in {0, 0.5, 1, 1.5, 2}   x baseline slice q_k^base
    limit directive    l in {none, join, improve}

* ``baseline`` defaults to the TWAP slice X/N; passing an Almgren–Chriss
  schedule turns any policy into a *residual* policy around that baseline.
* Scripted strategies may bypass the grid with a dict action
  ``{"market_qty": float, "limit": "none"|"join"|"improve", "limit_qty": float}``
  — the same safety layer applies either way.

Safety layer (hard constraints, violations are counted and penalised):
  inventory (never over-execute), max child order, max participation vs an
  EMA of realised market volume, price collar for market orders, deadline
  with forced terminal liquidation (exempt from cap/collar, punitive because
  it walks the book), finite actions only.

Reward (shaped) vs economics: the environment accumulates the *economic*
implementation shortfall exactly (latent decomposition included) and reports
it separately from the shaped training reward — the two must never be
conflated in reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import Config
from .order_book import AgentLimitOrder, OrderBook
from .random import scenario_rng
from .volume import expected_step_volume

MARKET_MULTS: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0)
LIMIT_MODES: tuple[str, ...] = ("none", "join", "improve")
N_ACTIONS: int = len(MARKET_MULTS) * len(LIMIT_MODES)

FEATURE_NAMES: tuple[str, ...] = (
    "time",
    "inventory",
    "spread",
    "bid_depth",
    "ask_depth",
    "imbalance",
    "recent_return",
    "recent_flow",
    "vol_state",
    "transient_impact",
    "volume_state",
    "outstanding",
)
OBS_DIM: int = len(FEATURE_NAMES)

# ablation name -> observation indices to zero out
ABLATION_FEATURES: dict[str, tuple[int, ...]] = {
    "imbalance": (5,),
    "recent_flow": (7,),
    "transient_impact": (9,),
    "volume_state": (10,),
    "vol_state": (8,),
}


def decode_action(action: int) -> tuple[float, str]:
    if not 0 <= action < N_ACTIONS:
        raise ValueError(f"action {action} outside [0, {N_ACTIONS})")
    return MARKET_MULTS[action % 5], LIMIT_MODES[action // 5]


@dataclass
class StepTrace:
    """Per-decision-step trace for example-episode plots."""

    t: float
    inventory: float
    q_market: float
    q_limit_fill: float
    spread: float
    bid_depth: float
    ask_depth: float
    imbalance: float
    D: float
    mid: float
    s0: float
    best_bid: float
    best_ask: float
    market_volume: float
    exec_price: float  # avg agent execution price this step (0 if none)


COMPONENT_KEYS = (
    "timing",
    "spread",
    "walk_temporary",
    "permanent",
    "transient",
    "spread_capture",
    "adverse_selection",
    "fees",
    "cleanup",
)


class ExecutionEnv:
    """Reactive (or replay) execution environment. Not thread-safe; one
    episode at a time."""

    def __init__(
        self,
        cfg: Config,
        reactive: bool = True,
        baseline: np.ndarray | None = None,
        feature_mask: np.ndarray | None = None,
        record_trace: bool = False,
    ) -> None:
        self.cfg = cfg
        self.reactive = reactive
        self.N = cfg.n_decision_steps
        self.dt = cfg.horizon_seconds / self.N
        self.n_sub = cfg.lob.sub_steps_per_decision
        X = cfg.initial_inventory
        self.baseline = (
            np.asarray(baseline, dtype=float)
            if baseline is not None
            else np.full(self.N, X / self.N)
        )
        if len(self.baseline) != self.N:
            raise ValueError("baseline schedule length must equal n_decision_steps")
        self.feature_mask = (
            np.asarray(feature_mask, dtype=float) if feature_mask is not None else np.ones(OBS_DIM)
        )
        self.record_trace = record_trace
        self._exp_step_vol = float(expected_step_volume(cfg).mean())
        self.book: OrderBook | None = None

    # ------------------------------------------------------------------ reset
    def reset(self, scenario_seed: int) -> np.ndarray:
        cfg = self.cfg
        rng = scenario_rng(scenario_seed, "lob")
        self.book = OrderBook(cfg, rng, self.N * self.n_sub, reactive=self.reactive)
        self.x = float(cfg.initial_inventory)
        self.k = 0
        self.order: AgentLimitOrder | None = None
        self.arrival_s0 = self.book.s0
        self.cash = 0.0
        self.fees = 0.0
        self.components = dict.fromkeys(COMPONENT_KEYS, 0.0)
        self.vol_ema = self._exp_step_vol
        self.violations = 0
        self.n_orders = 0
        self.n_cancels = 0
        self.mkt_shares = 0.0
        self.limit_shares = 0.0
        self.limit_posted = 0.0
        self.crossed_shares = 0.0
        self.cleanup_qty = 0.0
        self.completion_step = self.N
        self.spread_paid_sum = 0.0
        self.participation_num = 0.0
        self.participation_den = 0.0
        self.d_sum = 0.0
        self.max_exposure = 0.0
        self.shaped_total = 0.0
        self.risk_penalty_total = 0.0
        self._is_prev = 0.0
        self._viol_prev = 0
        self.traces: list[StepTrace] = []
        return self._obs()

    # ------------------------------------------------------------ observation
    def _obs(self) -> np.ndarray:
        cfg, book = self.cfg, self.book
        assert book is not None
        base_spread = cfg.spread_bps * 1e-4 * cfg.arrival_price
        slice_mean = cfg.initial_inventory / self.N
        sig_now = book._sigma_sub[min(book.k_sub, book.n_sub_total - 1)]
        outstanding = (self.order.qty - self.order.filled) if self.order else 0.0
        obs = np.array(
            [
                self.k / self.N,
                self.x / cfg.initial_inventory,
                np.clip(book.spread / base_spread - 1.0, -3, 3),
                np.clip(book.bid_depth / book.target_depth - 1.0, -3, 3),
                np.clip(book.ask_depth / book.target_depth - 1.0, -3, 3),
                book.imbalance,
                np.clip(book.recent_return / (cfg.arrival_price * 1e-3), -3, 3),
                np.clip(book.recent_flow / (3.0 * cfg.lob.market_order_size_mean), -3, 3),
                np.clip(sig_now / cfg.sigma_abs - 1.0, -3, 3),
                np.clip(book.D / max(0.5 * base_spread, 1e-9), -3, 3),
                np.clip(self.vol_ema / self._exp_step_vol - 1.0, -3, 3),
                np.clip(outstanding / max(slice_mean, 1e-9), 0, 3),
            ],
            dtype=np.float64,
        )
        return obs * self.feature_mask

    # ---------------------------------------------------------------- helpers
    def _safety_market_qty(self, desired: float, terminal: bool = False) -> float:
        """Clip a desired market quantity through the hard-constraint stack."""
        cfg = self.cfg
        assert self.book is not None
        if not np.isfinite(desired) or desired < 0:
            self.violations += 1
            desired = 0.0
        outstanding = (self.order.qty - self.order.filled) if self.order else 0.0
        q = min(desired, max(self.x - outstanding, 0.0))
        if terminal:
            return q
        clipped = False
        cap_child = cfg.max_child_order_frac * cfg.initial_inventory
        if q > cap_child:
            q, clipped = cap_child, True
        cap_part = cfg.max_participation_rate * self.vol_ema
        if q > cap_part:
            q, clipped = cap_part, True
        # Price collar: cap quantity against the estimated block-average price,
        # including book walk and the current block's own impact.
        collar = cfg.price_collar_bps * 1e-4 * self.arrival_s0
        if q > 0:
            avg_price, _, _ = self.book.market_order_quote(q)
            if cfg.sign * (self.arrival_s0 - avg_price) > collar:
                touch_price, _, _ = self.book.market_order_quote(0.0)
                if cfg.sign * (self.arrival_s0 - touch_price) > collar:
                    q = 0.0
                else:
                    lo, hi = 0.0, q
                    for _ in range(50):
                        mid = 0.5 * (lo + hi)
                        price, _, _ = self.book.market_order_quote(mid)
                        if cfg.sign * (self.arrival_s0 - price) <= collar:
                            lo = mid
                        else:
                            hi = mid
                    q = lo if lo > 1e-9 else 0.0
                clipped = True
        if clipped and desired > 0:
            self.violations += 1
        return q

    def _register_market_execution(
        self, q: float, cash: float, detail: dict[str, float], cleanup: bool
    ) -> None:
        cfg = self.cfg
        assert self.book is not None
        s0_now = self.book.s0
        self.cash += cash
        self.fees += cfg.fee_per_share * q
        self.components["fees"] += cfg.fee_per_share * q
        self.components["timing"] += cfg.sign * q * (self.arrival_s0 - s0_now)
        if cleanup:
            # everything beyond timing goes to the cleanup bucket
            self.components["cleanup"] += (
                detail["spread"] + detail["walk"] + detail["permanent"] + detail["transient"]
            )
        else:
            self.components["spread"] += detail["spread"]
            self.components["walk_temporary"] += detail["walk"]
            self.components["permanent"] += detail["permanent"]
            self.components["transient"] += detail["transient"]
        self.mkt_shares += q
        self.spread_paid_sum += detail["spread"]

    def _register_limit_fill(
        self,
        q: float,
        price: float,
        s0_f: float,
        mid_f: float,
        perm_f: float,
        d_f: float,
        crossed: bool,
    ) -> None:
        cfg = self.cfg
        sign = cfg.sign
        self.cash += q * price
        self.fees += cfg.fee_per_share * q
        self.components["fees"] += cfg.fee_per_share * q
        self.components["timing"] += sign * q * (self.arrival_s0 - s0_f)
        self.components["permanent"] += perm_f * q
        self.components["transient"] += d_f * q
        edge = sign * (mid_f - price) * q  # negative = spread captured
        if crossed:
            self.components["adverse_selection"] += edge
        else:
            self.components["spread_capture"] += edge
        self.limit_shares += q
        if crossed:
            self.crossed_shares += q

    # ------------------------------------------------------------------- step
    def step(self, action: int | dict[str, Any]) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        if self.book is None:
            raise RuntimeError("call reset() first")
        if self.k >= self.N:
            raise RuntimeError("episode finished; call reset()")
        cfg, book = self.cfg, self.book
        rw = cfg.rl.reward
        k = self.k
        x_start = self.x

        # ---- decode action --------------------------------------------------
        if isinstance(action, dict):
            try:
                desired_mkt = float(action.get("market_qty", 0.0))
            except (TypeError, ValueError):
                desired_mkt = float("nan")
            limit_mode = str(action.get("limit", "none"))
            if limit_mode not in LIMIT_MODES:
                self.violations += 1
                limit_mode = "none"
            raw_limit_qty = action.get("limit_qty", None)
            limit_qty_req: float | None
            if raw_limit_qty is None:
                limit_qty_req = None
            else:
                try:
                    limit_qty_req = float(raw_limit_qty)
                except (TypeError, ValueError):
                    limit_qty_req = float("nan")
                if not np.isfinite(limit_qty_req) or limit_qty_req < 0:
                    self.violations += 1
                    limit_qty_req = 0.0
        else:
            mult, limit_mode = decode_action(int(action))
            desired_mkt = mult * self.baseline[k]
            limit_qty_req = None

        # ---- market order through the safety layer -------------------------
        q_m = self._safety_market_qty(desired_mkt)
        exec_cash = 0.0
        if q_m > 0:
            q_exec, cash, detail = book.market_order(q_m)
            self._register_market_execution(q_exec, cash, detail, cleanup=False)
            self.x -= q_exec
            exec_cash += cash
            self.n_orders += 1

        # ---- limit-order management -----------------------------------------
        sign = cfg.sign
        if limit_mode == "none":
            if self.order is not None and self.order.qty - self.order.filled > 1e-9:
                self.n_cancels += 1
            self.order = None
        else:
            improve = limit_mode == "improve"
            tick = cfg.tick_size
            target_price = (
                (book.best_ask - tick if improve else book.best_ask)
                if sign > 0
                else (book.best_bid + tick if improve else book.best_bid)
            )
            outstanding = (self.order.qty - self.order.filled) if self.order else 0.0
            want_qty = limit_qty_req if limit_qty_req is not None else self.baseline[k]
            want_qty = min(max(want_qty, 0.0), max(self.x, 0.0))
            same_level = (
                self.order is not None
                and abs(self.order.price - target_price) < 0.5 * tick
                and abs((self.order.qty - self.order.filled) - want_qty) < 1.0
            )
            if not same_level:
                if self.order is not None and outstanding > 1e-9:
                    self.n_cancels += 1
                if want_qty > 1e-9:
                    queue_ahead = (
                        0.0 if improve else (book.ask_depth if sign > 0 else book.bid_depth)
                    )
                    self.order = AgentLimitOrder(
                        price=target_price, qty=want_qty, queue_ahead=queue_ahead
                    )
                    self.limit_posted += want_qty
                    self.n_orders += 1
                    if improve:
                        book.agent_improve_quote()
                else:
                    self.order = None

        # ---- evolve the book over sub-steps ---------------------------------
        step_mkt_volume = 0.0
        for _ in range(self.n_sub):
            flow = book.evolve_substep(self.order)
            step_mkt_volume += flow.buy_mo_volume + flow.sell_mo_volume
            if flow.agent_limit_fill > 0:
                fill = min(flow.agent_limit_fill, self.x)
                self._register_limit_fill(
                    fill,
                    flow.agent_fill_price,
                    flow.fill_s0,
                    flow.fill_mid,
                    flow.fill_perm,
                    flow.fill_D,
                    flow.crossed,
                )
                self.x -= fill
            if self.order is not None and self.order.qty - self.order.filled <= 1e-9:
                self.order = None

        # ---- terminal forced liquidation -------------------------------------
        terminal = k == self.N - 1
        forced_qty = 0.0
        if terminal:
            if self.order is not None and self.order.qty - self.order.filled > 1e-9:
                self.n_cancels += 1
            self.order = None
            if self.x > 1e-9:
                forced_qty = self.x
                q_exec, cash, detail = book.market_order(forced_qty)
                self._register_market_execution(q_exec, cash, detail, cleanup=True)
                self.cleanup_qty += q_exec
                self.x -= q_exec
                self.n_orders += 1

        # ---- bookkeeping -----------------------------------------------------
        executed_step = x_start - self.x
        if self.x <= 1e-9 and self.completion_step == self.N:
            self.completion_step = k + 1
        self.vol_ema = 0.7 * self.vol_ema + 0.3 * step_mkt_volume
        self.participation_num += executed_step if not terminal else executed_step - forced_qty
        self.participation_den += max(step_mkt_volume, 1e-9)
        self.d_sum += book.D
        remaining_time = cfg.horizon_seconds - (k + 1) * self.dt
        exposure = abs(self.x) * cfg.sigma_abs * np.sqrt(max(remaining_time, 0.0))
        self.max_exposure = max(self.max_exposure, exposure)

        # ---- rewards ----------------------------------------------------------
        # economic increment: change in IS-so-far is implicit; shaped reward
        # uses the step's cost components + risk penalties (all in currency).
        step_cost = self._is_running() - getattr(self, "_is_prev", 0.0)
        self._is_prev = self._is_running()
        sub_start = k * self.n_sub
        sub_stop = (k + 1) * self.n_sub
        sigma_sq = float(np.mean(book._sigma_sub[sub_start:sub_stop] ** 2))
        risk_pen = rw.inventory_penalty * (self.x**2) * sigma_sq * self.dt
        impact_pen = rw.impact_penalty * (book.D**2)
        constr_pen = rw.constraint_penalty * (
            1.0 if self.violations > getattr(self, "_viol_prev", 0) else 0.0
        )
        self._viol_prev = self.violations
        self.risk_penalty_total += risk_pen
        reward = -rw.cost_scale * (step_cost + risk_pen + impact_pen) - constr_pen
        if terminal and forced_qty > 0:
            reward -= cfg.terminal_inventory_penalty * (forced_qty / cfg.initial_inventory) ** 2
        self.shaped_total += reward

        # ---- trace ------------------------------------------------------------
        if self.record_trace:
            snap = book.snapshot()
            self.traces.append(
                StepTrace(
                    t=(k + 1) * self.dt,
                    inventory=self.x,
                    q_market=q_m if q_m > 0 else 0.0,
                    q_limit_fill=max(executed_step - (q_m if q_m > 0 else 0.0) - forced_qty, 0.0),
                    spread=snap.spread,
                    bid_depth=snap.bid_depth,
                    ask_depth=snap.ask_depth,
                    imbalance=snap.imbalance,
                    D=snap.D,
                    mid=snap.mid,
                    s0=snap.s0,
                    best_bid=snap.best_bid,
                    best_ask=snap.best_ask,
                    market_volume=step_mkt_volume,
                    exec_price=(exec_cash / q_m) if q_m > 0 else 0.0,
                )
            )

        self.k += 1
        done = self.k >= self.N
        info: dict[str, Any] = {"executed": executed_step, "forced": forced_qty}
        if done:
            info["episode"] = self.episode_summary()
        return self._obs(), float(reward), done, info

    # ----------------------------------------------------------------- summary
    def _is_running(self) -> float:
        """Economic implementation shortfall so far (currency, + = cost).

        sign=+1 (sell): X_exec * arrival - cash received;
        sign=-1 (buy):  cash paid - X_exec * arrival. One expression covers both.
        """
        executed = self.cfg.initial_inventory - self.x
        return self.cfg.sign * (executed * self.arrival_s0 - self.cash) + self.fees

    def episode_summary(self) -> dict[str, Any]:
        cfg = self.cfg
        X = cfg.initial_inventory
        executed = X - self.x
        is_total = cfg.sign * (executed * self.arrival_s0 - self.cash) + self.fees
        comp_sum = sum(self.components.values())
        return {
            "is_total": is_total,
            "is_bps": is_total / (X * self.arrival_s0) * 1e4,
            "components": dict(self.components),
            "decomposition_residual": is_total - comp_sum,
            "executed": executed,
            "terminal_inventory": self.x,
            "cleanup_qty": self.cleanup_qty,
            "cleanup_cost": self.components["cleanup"],
            "mkt_shares": self.mkt_shares - self.cleanup_qty,
            "limit_shares": self.limit_shares,
            "limit_posted": self.limit_posted,
            "limit_fill_rate": self.limit_shares / self.limit_posted
            if self.limit_posted > 0
            else 0.0,
            "crossed_shares": self.crossed_shares,
            "completion_step": self.completion_step,
            "completion_time_s": self.completion_step * self.dt,
            "participation": self.participation_num / max(self.participation_den, 1e-9),
            "avg_spread_paid": self.spread_paid_sum / max(self.mkt_shares, 1e-9),
            "avg_transient": self.d_sum / self.N,
            "max_exposure": self.max_exposure,
            "n_orders": self.n_orders,
            "n_cancels": self.n_cancels,
            "violations": self.violations,
            "shaped_reward": self.shaped_total,
            "risk_penalty": self.risk_penalty_total,
            "fees": self.fees,
        }
