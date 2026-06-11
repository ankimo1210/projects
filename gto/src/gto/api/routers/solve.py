"""GameSpec solve endpoint (mode-matrix spec section 4.1/4.5).

POST /api/solve           — HU NLHE cash postflop custom solves (M1a).
GET  /api/solve/capabilities — the supported sub-matrix, iteration clamps
                               and cost classes; the UI's source of truth.

The legacy /api/hu/* endpoints are deprecated aliases of the river /
turn_river paths through this contract.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gto.library.range_notation import parse_range_notation

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)

ITER_CLAMP = {"river": (100, 50_000, 2_000), "turn_river": (100, 30_000, 10_000)}

RAKE_PRESETS = {
    "none": (0.0, 0.0),
    "site": (0.05, 3.0),
    "live": (0.10, 5.0),
}


class RakeSpec(BaseModel):
    model: Literal["none", "site", "live", "custom"] = "none"
    pct: float | None = None      # custom only
    cap_bb: float | None = None   # custom only


class SolveConfig(BaseModel):
    positions: list[str] = ["SB", "BB"]
    pot_type: Literal["srp", "3bet", "4bet"] = "srp"
    pot_bb: float = Field(gt=0)
    board: list[str]
    ranges: dict[str, str | list[float]] = {}     # keys: ip / oop
    action_tree: dict | None = None               # {bet_sizes_pct, max_raises}


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
    "game": ["cash"],
    "variant": ["nlhe"],
    "table": ["hu"],
    "spot": ["postflop"],
    "rake_models": [*list(RAKE_PRESETS), "custom"],
    "pot_types": ["srp", "3bet", "4bet"],
    "streets": {
        "river": {"board_cards": 5, "cost": "sync", "iterations": ITER_CLAMP["river"]},
        "turn_river": {"board_cards": 4, "cost": "sync_capped", "iterations": ITER_CLAMP["turn_river"]},
        "flop": {"board_cards": 3, "cost": "async", "status": "M1b — not yet available"},
    },
    "positions": [["SB", "BB"], ["BTN", "BB"]],
}


@router.get("/solve/capabilities")
async def capabilities():
    return CAPABILITIES


def _reject_unsupported(spec: GameSpec) -> None:
    checks = [
        (spec.game != "cash", f"game={spec.game}"),
        (spec.variant != "nlhe", f"variant={spec.variant}"),
        (spec.table != "hu", f"table={spec.table}"),
        (spec.spot != "postflop", f"spot={spec.spot}"),
        (sorted(spec.config.positions) not in (["BB", "SB"], ["BB", "BTN"]),
         f"positions={spec.config.positions}"),
        (len(spec.config.board) == 3, "flop boards are M1b (async tier) — not yet available"),
        (len(spec.config.board) not in (3, 4, 5), f"board must have 4 or 5 cards, got {len(spec.config.board)}"),
    ]
    for failed, what in checks:
        if failed:
            raise HTTPException(
                422,
                detail={"unsupported": what, "see": "/api/solve/capabilities"},
            )


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
    if isinstance(v, str):
        try:
            return parse_range_notation(v).tolist()
        except ValueError as e:
            raise HTTPException(422, f"bad range notation: {e}") from e
    if len(v) != 1326:
        raise HTTPException(422, f"range weight vector must have 1326 entries, got {len(v)}")
    return v


@router.post("/solve")
async def solve(spec: GameSpec):
    _reject_unsupported(spec)
    street = "river" if len(spec.config.board) == 5 else "turn_river"
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


def _envelope(raw: dict, spec: GameSpec, street: str, iters: int, pct: float, cap_bb: float) -> dict:
    """Unified SolveResult (spec section 4.5). Provenance: ev <- game values,
    per-combo ev <- avg-strategy values, equity <- separate range-vs-range
    computation in the solver, exploitability <- general-sum NashConv."""
    return {
        "strategy": raw["strategy"],
        "actions": raw["actions"],
        "combo_strategies": raw["combos"],
        "ev": {
            "ip": raw["game_value_sb"],
            "oop": raw["game_value_bb"],
            "per_combo": [{"card_a": c["card_a"], "card_b": c["card_b"], "ev": c["ev"]} for c in raw["combos"]],
        },
        "equity": {"ip": raw["equity_sb"], "oop": raw["equity_bb"]},
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
            "abstraction": None,
            "rake": {"pct": pct, "cap_bb": cap_bb},
            "equilibrium_claim": True,
            "game_spec": spec.model_dump(),
        },
    }
