from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
import asyncio

from gto.library.range_builder import compute_preflop_outcome

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)

POSITIONS = ["BTN", "CO", "SB", "HJ", "UTG"]

FLOP_POT   = {"BTN": 6.5, "CO": 7.0, "SB": 5.0, "HJ": 7.0, "UTG": 7.0}
EFF_STACK  = 97.0
MAX_BETS   = 2


class SimRequest(BaseModel):
    position:   str = "BTN"
    board:      list[str] = []   # 0 = preflop only, 3-5 = postflop solve
    iterations: int = 300


class ActionFreq(BaseModel):
    action: str
    freq:   float


class BBHand(BaseModel):
    hand:          str
    call_freq:     float
    fold_freq:     float
    threebet_freq: float


class PostflopResult(BaseModel):
    strategy:       list[ActionFreq]
    exploitability: float
    backend:        str
    iterations:     int


class SimResponse(BaseModel):
    position:      str
    fold_equity:   float
    call_freq:     float
    threebet_freq: float
    bb_hands:      list[BBHand]
    postflop:      PostflopResult | None = None


@router.post("/simulation/run", response_model=SimResponse)
async def run_simulation(req: SimRequest):
    if req.position not in POSITIONS:
        raise HTTPException(422, f"position must be one of {POSITIONS}")
    if req.board and not (3 <= len(req.board) <= 5):
        raise HTTPException(422, "board must be empty or have 3-5 cards")
    if not (50 <= req.iterations <= 1000):
        raise HTTPException(422, "iterations must be 50-1000")

    outcome = compute_preflop_outcome(req.position, dead_cards=req.board or None)

    bb_hands = [
        BBHand(
            hand=h["hand"],
            call_freq=h["call_freq"],
            fold_freq=h["fold_freq"],
            threebet_freq=h["threebet_freq"],
        )
        for h in outcome["bb_hands"]
        if h["call_freq"] > 0 or h["threebet_freq"] > 0
    ]

    postflop = None
    if req.board:
        loop = asyncio.get_event_loop()
        ip_w  = outcome["ip_weights"].tolist()
        oop_w = outcome["oop_call_weights"].tolist()
        spot = {
            "board":               req.board,
            "pot_bb":              FLOP_POT.get(req.position, 6.5),
            "effective_stack_bb":  EFF_STACK,
        }

        def _solve():
            try:
                import gto_cuda
                results = gto_cuda.batch_solve_rust(
                    [spot], req.iterations, MAX_BETS, ip_w, oop_w,
                )
                result  = results[0]
                backend = "gpu"
            except Exception:
                import gto_py
                result  = gto_py.solve_spot(
                    spot["pot_bb"], spot["effective_stack_bb"],
                    spot["board"], req.iterations, MAX_BETS,
                )
                backend = "cpu"
            return result, backend

        result, backend = await loop.run_in_executor(_executor, _solve)
        postflop = PostflopResult(
            strategy=[ActionFreq(**a) for a in result["strategy"]],
            exploitability=result["exploitability"],
            backend=backend,
            iterations=result["iterations"],
        )

    return SimResponse(
        position=req.position,
        fold_equity=outcome["fold_equity"],
        call_freq=outcome["call_freq"],
        threebet_freq=outcome["threebet_freq"],
        bb_hands=bb_hands,
        postflop=postflop,
    )
