"""HU equilibrium solver (gto-hu) — exact river solve with exploitability.

Distinct from /solver/solve (gto-cuda, single-street approximation, no
exploitability): this is a genuinely correct river equilibrium with an
exact exploitability number attached. Fast enough to run live.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)


class RiverRequest(BaseModel):
    board: list[str]  # exactly 5 cards
    pot_bb: float = 20.0
    effective_stack_bb: float = 90.0
    iterations: int = 5000


class TurnRiverRequest(BaseModel):
    board: list[str]  # exactly 4 cards (turn)
    pot_bb: float = 20.0
    effective_stack_bb: float = 90.0
    iterations: int = 10000


class ActionFreq(BaseModel):
    action: str
    freq: float


class ComboStrategy(BaseModel):
    card_a: str
    card_b: str
    freqs: list[float]


class RiverResponse(BaseModel):
    strategy: list[ActionFreq]
    actions: list[str]
    exploitability: float
    br_sb: float
    br_bb: float
    game_value_sb: float
    iterations: int
    elapsed_secs: float
    combos: list[ComboStrategy]


@router.post("/hu/river", response_model=RiverResponse)
async def solve_river(req: RiverRequest, response: Response):
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/solve>; rel="successor-version"'
    if len(req.board) != 5:
        raise HTTPException(422, "river board must have exactly 5 cards")
    if req.iterations < 100 or req.iterations > 50_000:
        raise HTTPException(422, "iterations must be 100-50000")
    if req.pot_bb <= 0 or req.effective_stack_bb <= 0:
        raise HTTPException(422, "pot and stack must be positive")

    loop = asyncio.get_event_loop()
    try:
        import gto_py

        result = await loop.run_in_executor(
            _executor,
            lambda: gto_py.solve_hu_river(
                req.board,
                req.pot_bb,
                req.effective_stack_bb,
                req.iterations,
            ),
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    return _to_response(result)


@router.post("/hu/turn-river", response_model=RiverResponse)
async def solve_turn_river(req: TurnRiverRequest, response: Response):
    """Exact turn+river equilibrium (river enumerated, turn sampled). The
    turn root strategy is OOP (BB). Slow: ~30-40 s at 10k iterations —
    the frontend must call this asynchronously."""
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/solve>; rel="successor-version"'
    if len(req.board) != 4:
        raise HTTPException(422, "turn board must have exactly 4 cards")
    if req.iterations < 100 or req.iterations > 30_000:
        raise HTTPException(422, "iterations must be 100-30000")
    if req.pot_bb <= 0 or req.effective_stack_bb <= 0:
        raise HTTPException(422, "pot and stack must be positive")

    loop = asyncio.get_event_loop()
    try:
        import gto_py

        result = await loop.run_in_executor(
            _executor,
            lambda: gto_py.solve_hu_turn_river(
                req.board,
                req.pot_bb,
                req.effective_stack_bb,
                req.iterations,
            ),
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    return _to_response(result)


def _to_response(result: dict) -> "RiverResponse":
    return RiverResponse(
        strategy=[ActionFreq(**a) for a in result["strategy"]],
        actions=result["actions"],
        exploitability=result["exploitability"],
        br_sb=result["br_sb"],
        br_bb=result["br_bb"],
        game_value_sb=result["game_value_sb"],
        iterations=result["iterations"],
        elapsed_secs=result["elapsed_secs"],
        combos=[ComboStrategy(**c) for c in result["combos"]],
    )
