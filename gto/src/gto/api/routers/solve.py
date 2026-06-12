"""GameSpec solve endpoint (mode-matrix spec section 4.1/4.5).

POST /api/solve                 — HU NLHE cash postflop custom solves.
                                  river / turn+river run synchronously;
                                  flop is submitted to the async job tier
                                  (M1b) and returns 202 + a job handle.
GET  /api/solve/capabilities    — supported sub-matrix, iteration clamps,
                                  cost classes; the UI's source of truth.
GET  /api/solve/jobs/{job_id}   — async job status (+ result envelope when done).
DELETE /api/solve/jobs/{job_id} — cancel a queued (or best-effort running) job.

The legacy /api/hu/* endpoints are deprecated aliases of the river /
turn_river paths through this contract.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from gto.api.auth import require_local
from gto.api.jobs import JobStatus, job_manager
from gto.api.ratelimit import rate_limited_user
from gto.library.chart_ranges import CHART_OPENERS, chart_ranges
from gto.library.range_notation import parse_range_notation

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)

ITER_CLAMP = {
    "river": (100, 50_000, 2_000),
    "turn_river": (100, 30_000, 10_000),
    "flop": (100, 20_000, 3_000),
}

RAKE_PRESETS = {
    "none": (0.0, 0.0),
    "site": (0.05, 3.0),
    "live": (0.10, 5.0),
}

# Flop-tier defaults (spec section 4.4). Bucketing is mandatory on flop: an
# exact (K=0) full SRP 100bb solve is 105 GB.
FLOP_DEFAULT_BUCKETS_RIVER = 128
FLOP_DEFAULT_BUCKETS_TURN = 0
FLOP_DEFAULT_MAX_TABLE_GB = 12.0


class RakeSpec(BaseModel):
    model: Literal["none", "site", "live", "custom"] = "none"
    pct: float | None = None      # custom only
    cap_bb: float | None = None   # custom only


class AbstractionSpec(BaseModel):
    buckets_river: int = FLOP_DEFAULT_BUCKETS_RIVER
    buckets_turn: int = FLOP_DEFAULT_BUCKETS_TURN
    max_table_gb: float = FLOP_DEFAULT_MAX_TABLE_GB


class SolveConfig(BaseModel):
    positions: list[str] = ["SB", "BB"]
    pot_type: Literal["srp", "3bet", "4bet"] = "srp"
    pot_bb: float = Field(gt=0)
    board: list[str]
    ranges: dict[str, str | list[float]] = {}     # keys: ip / oop
    action_tree: dict | None = None               # {bet_sizes_pct, max_raises}
    abstraction: AbstractionSpec = AbstractionSpec()  # flop solves only


class GameSpec(BaseModel):
    game: Literal["cash", "tournament"] = "cash"
    variant: Literal["nlhe", "plo"] = "nlhe"
    table: Literal["hu", "6max", "9max"] = "hu"
    stack_bb: float = Field(gt=0)
    rake: RakeSpec = RakeSpec()
    spot: Literal["preflop", "postflop", "full_hand"] = "postflop"
    config: SolveConfig
    iterations: int | None = None


CAPABILITIES = {
    "game": ["cash", "tournament"],
    "variant": ["nlhe"],
    "table": ["hu", "6max"],
    "spot": ["postflop"],
    "rake_models": [*list(RAKE_PRESETS), "custom"],
    "pot_types": ["srp", "3bet", "4bet"],
    "tournament": {
        # F2: with 2 players ICM $EV is linear in stack, so HU tournament ==
        # chip EV. Antes are folded into pot_bb by the caller; rake is none.
        "tables": ["hu", "6max"],
        "rake": ["none"],
        "note": "antes/BB-ante go into pot_bb; shallow stacks via stack_bb",
        "stack_presets_bb": [10, 15, 20, 25, 30, 40],
    },
    "table_6max": {
        # 2-player position-pair subgames with chart-fixed ranges (F1).
        "positions": [[o, "BB"] for o in CHART_OPENERS],
        "pot_types": ["srp", "3bet"],
        "range_source": "chart (default; explicit notation/weights override)",
        "note": "SB opener is OOP postflop (6max), unlike HU where SB is IP",
    },
    "streets": {
        "river": {"board_cards": 5, "cost": "sync", "iterations": ITER_CLAMP["river"]},
        "turn_river": {"board_cards": 4, "cost": "sync_capped", "iterations": ITER_CLAMP["turn_river"]},
        "flop": {
            "board_cards": 3,
            "cost": "async",
            "iterations": ITER_CLAMP["flop"],
            "pot_types": ["srp", "3bet"],   # FlopTreeConfig has no 4bet preset
            "rake": ["none"],               # FlopSolver has no rake path yet
            "abstraction": {
                "buckets_river_default": FLOP_DEFAULT_BUCKETS_RIVER,
                "buckets_turn_default": FLOP_DEFAULT_BUCKETS_TURN,
                "max_table_gb_default": FLOP_DEFAULT_MAX_TABLE_GB,
            },
        },
    },
    "positions": [["SB", "BB"], ["BTN", "BB"]],
}


@router.get("/solve/capabilities")
async def capabilities():
    return CAPABILITIES


def _reject_unsupported(spec: GameSpec) -> None:
    if spec.table == "6max":
        pos_ok = (
            len(spec.config.positions) == 2
            and "BB" in spec.config.positions
            and _opener_of(spec) in CHART_OPENERS
        )
        table_checks = [
            (not pos_ok, f"6max positions={spec.config.positions} (need [opener, BB])"),
            (spec.config.pot_type not in ("srp", "3bet"),
             f"6max pot_type={spec.config.pot_type} (charts cover srp / 3bet)"),
        ]
    else:
        table_checks = [
            (spec.table != "hu", f"table={spec.table}"),
            (sorted(spec.config.positions) not in (["BB", "SB"], ["BB", "BTN"]),
             f"positions={spec.config.positions}"),
        ]
    checks = [
        (spec.game == "tournament" and spec.rake.model != "none",
         "tournament solves take no rake"),
        (spec.variant != "nlhe", f"variant={spec.variant}"),
        *table_checks,
        (spec.spot != "postflop", f"spot={spec.spot}"),
        (len(spec.config.board) not in (3, 4, 5), f"board must have 3, 4 or 5 cards, got {len(spec.config.board)}"),
    ]
    for failed, what in checks:
        if failed:
            raise HTTPException(
                422,
                detail={"unsupported": what, "see": "/api/solve/capabilities"},
            )


def _opener_of(spec: GameSpec) -> str | None:
    others = [p for p in spec.config.positions if p != "BB"]
    return others[0] if len(others) == 1 else None


def _apply_chart_presets(spec: GameSpec) -> None:
    """6max: fill unset/'chart' ranges from the preflop charts (F1 — ranges
    fixed by the chart; explicit notation/weights inputs override)."""
    derived = chart_ranges(_opener_of(spec), spec.config.pot_type)
    for side in ("ip", "oop"):
        v = spec.config.ranges.get(side)
        if v is None or v in ("chart", "preset"):
            spec.config.ranges[side] = derived[side]


def _resolve_rake(r: RakeSpec) -> tuple[float, float]:
    if r.model == "custom":
        if r.pct is None or r.cap_bb is None:
            raise HTTPException(422, "custom rake requires pct and cap_bb")
        # A positive rake needs a positive cap (the binding rejects cap<=0);
        # validate it here too so both layers agree on the boundary.
        if not 0.0 <= r.pct < 0.5 or (r.pct > 0.0 and r.cap_bb <= 0.0) or r.cap_bb < 0.0:
            raise HTTPException(422, "rake pct must be in [0, 0.5); cap_bb must be > 0 when pct > 0")
        return r.pct, r.cap_bb
    return RAKE_PRESETS[r.model]


def _resolve_range(v: str | list[float] | None) -> list[float] | None:
    if v is None or v == "preset" or v == "uniform":
        return None  # binding default: uniform minus blockers
    if v == "chart":
        raise HTTPException(422, "chart ranges require table=6max (positions [opener, BB])")
    if isinstance(v, str):
        try:
            return parse_range_notation(v).tolist()
        except ValueError as e:
            raise HTTPException(422, f"bad range notation: {e}") from e
    if len(v) != 1326:
        raise HTTPException(422, f"range weight vector must have 1326 entries, got {len(v)}")
    return v


@router.post("/solve")
async def solve(spec: GameSpec, user: str = Depends(rate_limited_user)):
    _reject_unsupported(spec)
    if spec.table == "6max":
        _apply_chart_presets(spec)
    n = len(spec.config.board)
    if n == 3:
        # The flop async tier pins ~12 GB for tens of minutes — local-only
        # (E1 rev 2 gating); sync tiers below are auth + rate limited.
        await require_local()
        return _submit_flop(spec)
    street = "river" if n == 5 else "turn_river"
    lo, hi, default = ITER_CLAMP[street]
    iters = max(lo, min(hi, spec.iterations or default))
    pct, cap_bb = _resolve_rake(spec.rake)
    ip = _resolve_range(spec.config.ranges.get("ip"))
    oop = _resolve_range(spec.config.ranges.get("oop"))
    tree = spec.config.action_tree or {}
    bet_pcts = tree.get("bet_sizes_pct")
    max_raises = tree.get("max_raises")

    loop = asyncio.get_event_loop()
    try:
        import gto_py

        if street == "river":
            raw = await loop.run_in_executor(
                _executor,
                lambda: gto_py.solve_hu_river(
                    spec.config.board, spec.config.pot_bb, spec.stack_bb, iters,
                    ip, oop, bet_pcts, max_raises, spec.config.pot_type,
                    pct or None, cap_bb if pct else None,
                ),
            )
        else:
            raw = await loop.run_in_executor(
                _executor,
                lambda: gto_py.solve_hu_turn_river(
                    spec.config.board, spec.config.pot_bb, spec.stack_bb, iters,
                    None, ip, oop, bet_pcts, bet_pcts, max_raises,
                    spec.config.pot_type, pct or None, cap_bb if pct else None,
                ),
            )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    return _envelope(raw, spec, street, iters, pct, cap_bb)


def _submit_flop(spec: GameSpec):
    """Validate a flop GameSpec, reserve memory by its (pre-computed) dense
    table size, and submit it to the async job tier. Returns 202 + handle."""
    import gto_py

    if spec.rake.model != "none":
        raise HTTPException(422, "rake is not supported on flop solves yet (FlopSolver has no rake path)")
    if spec.config.pot_type not in ("srp", "3bet"):
        raise HTTPException(422, f"flop pot_type must be srp or 3bet, got {spec.config.pot_type}")

    lo, hi, default = ITER_CLAMP["flop"]
    iters = max(lo, min(hi, spec.iterations or default))
    abs_ = spec.config.abstraction
    ip = _resolve_range(spec.config.ranges.get("ip"))
    oop = _resolve_range(spec.config.ranges.get("oop"))
    tree = spec.config.action_tree or {}
    bet_pcts = tree.get("bet_sizes_pct")
    max_raises = tree.get("max_raises")

    # Estimate the dense-table footprint up front: reject infeasible configs
    # immediately (instead of letting the job error out), and use the estimate
    # as the memory reservation so the manager admits at most what fits.
    try:
        dense_gb = gto_py.flop_dense_table_gb(
            spec.config.pot_bb, spec.stack_bb, spec.config.pot_type,
            abs_.buckets_river, abs_.buckets_turn, bet_pcts, max_raises,
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    if dense_gb > abs_.max_table_gb:
        raise HTTPException(
            422,
            f"dense tables {dense_gb:.2f} GB exceed max_table_gb {abs_.max_table_gb:.1f} — "
            f"raise buckets_river (e.g. 128), reduce the tree (pot_type 3bet, smaller "
            f"stack), or raise abstraction.max_table_gb if you have the RAM",
        )
    if dense_gb > job_manager.budget_gb:
        raise HTTPException(
            422,
            f"dense tables {dense_gb:.2f} GB exceed the server job memory budget "
            f"{job_manager.budget_gb:.1f} GB — this solve cannot run on this host",
        )

    board = spec.config.board
    pot_bb = spec.config.pot_bb
    stack_bb = spec.stack_bb
    pot_type = spec.config.pot_type
    br, bt = abs_.buckets_river, abs_.buckets_turn
    max_gb = abs_.max_table_gb

    def run_flop() -> dict:
        import gto_py as _g

        raw = _g.solve_hu_flop(
            board, pot_bb, stack_bb, iters, None, ip, oop,
            bet_pcts, max_raises, pot_type, br, bt, max_gb, "sample",
        )
        return _envelope(raw, spec, "flop", iters, 0.0, 0.0)

    job_id = job_manager.submit("flop", est_gb=max(dense_gb, 0.1), fn=run_flop)
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "kind": "flop",
            "status": "queued",
            "est_gb": round(dense_gb, 2),
            "poll": f"/api/solve/jobs/{job_id}",
            "note": "flop solves are async (async tier) — poll the job for the result",
        },
    )


@router.get("/solve/jobs/{job_id}", dependencies=[Depends(require_local)])
async def job_status(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown or expired job id")
    body = job.snapshot()
    if job.status == JobStatus.DONE:
        body["result"] = job.result
    return body


@router.delete("/solve/jobs/{job_id}", dependencies=[Depends(require_local)])
async def job_cancel(job_id: str):
    if job_manager.get(job_id) is None:
        raise HTTPException(404, "unknown or expired job id")
    cancelled = job_manager.cancel(job_id)
    return {"job_id": job_id, "cancelled": cancelled, "status": job_manager.status(job_id)["status"]}


def _envelope(raw: dict, spec: GameSpec, street: str, iters: int, pct: float, cap_bb: float) -> dict:
    """Unified SolveResult (spec section 4.5). Provenance: ev <- game values,
    per-combo ev <- avg-strategy values, equity <- separate range-vs-range
    computation in the solver, exploitability <- general-sum NashConv.

    Field presence varies by tier: flop solves carry meta.abstraction and omit
    equity (no flop range-vs-range equity is computed)."""
    has_equity = "equity_sb" in raw
    abstraction = (
        {"buckets_river": raw["buckets_river"], "buckets_turn": raw["buckets_turn"]}
        if street == "flop"
        else None
    )
    return {
        "strategy": raw["strategy"],
        "actions": raw["actions"],
        "combo_strategies": raw["combos"],
        "ev": {
            "ip": raw["game_value_sb"],
            "oop": raw["game_value_bb"],
            "per_combo": [{"card_a": c["card_a"], "card_b": c["card_b"], "ev": c["ev"]} for c in raw["combos"]],
        },
        "equity": {"ip": raw["equity_sb"], "oop": raw["equity_bb"]} if has_equity else None,
        "frequencies": {a["action"]: a["freq"] for a in raw["strategy"]},
        "exploitability": {
            "nashconv_bb": raw["nashconv"],
            "per_hand_bb": raw["exploitability"],
            "br_gain_ip": raw["br_gain_sb"],
            "br_gain_oop": raw["br_gain_bb"],
        },
        "meta": {
            "solver": "gto-hu",
            "street": street,
            "iterations": iters,
            "elapsed_s": raw["elapsed_secs"],
            "abstraction": abstraction,
            "table_gb": raw.get("table_bytes_gb"),
            "rake": {"pct": pct, "cap_bb": cap_bb},
            "equilibrium_claim": True,
            "game_spec": spec.model_dump(),
        },
    }
