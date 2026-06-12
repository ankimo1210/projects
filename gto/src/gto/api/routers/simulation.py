import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from gto.api.auth import require_local
from gto.api.ratelimit import rate_limited_user
from gto.library.range_builder import compute_preflop_outcome

router = APIRouter(dependencies=[Depends(rate_limited_user)])  # E1 gate
_executor = ThreadPoolExecutor(max_workers=2)

POSITIONS = ["BTN", "CO", "SB", "HJ", "UTG"]

FLOP_POT = {"BTN": 6.5, "CO": 7.0, "SB": 5.0, "HJ": 7.0, "UTG": 7.0}
EFF_STACK = 97.0
MAX_BETS = 2


class SimRequest(BaseModel):
    position: str = "BTN"
    board: list[str] = []  # 0 = preflop only, 3-5 = postflop solve
    iterations: int = 300


class ActionFreq(BaseModel):
    action: str
    freq: float


class BBHand(BaseModel):
    hand: str
    call_freq: float
    fold_freq: float
    threebet_freq: float


class PostflopResult(BaseModel):
    strategy: list[ActionFreq]
    exploitability: float
    backend: str           # "gto-hu" | "gpu-preview"
    iterations: int
    equilibrium_claim: bool = False


class SimResponse(BaseModel):
    position: str
    fold_equity: float
    call_freq: float
    threebet_freq: float
    bb_hands: list[BBHand]
    postflop: PostflopResult | None = None


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
        # M2: turn/river boards run on gto-hu (exact equilibrium with the
        # chart-derived ranges); flop boards stay on the gto-cuda
        # instant-preview tier (single-street approximation, labeled).
        # The old gto-core solve_spot CPU fallback was retired.
        loop = asyncio.get_event_loop()
        ip_w = outcome["ip_weights"].tolist()
        oop_w = outcome["oop_call_weights"].tolist()
        pot_bb = FLOP_POT.get(req.position, 6.5)

        if len(req.board) in (4, 5):
            import gto_py

            iters = max(100, min(5_000, req.iterations))
            try:
                if len(req.board) == 5:
                    raw = await loop.run_in_executor(
                        _executor,
                        lambda: gto_py.solve_hu_river(
                            req.board, pot_bb, EFF_STACK, iters, ip_w, oop_w
                        ),
                    )
                else:
                    raw = await loop.run_in_executor(
                        _executor,
                        lambda: gto_py.solve_hu_turn_river(
                            req.board, pot_bb, EFF_STACK, iters, None, ip_w, oop_w
                        ),
                    )
            except ValueError as e:
                raise HTTPException(422, str(e)) from e
            postflop = PostflopResult(
                strategy=[ActionFreq(**a) for a in raw["strategy"]],
                exploitability=raw["exploitability"],
                backend="gto-hu",
                iterations=raw["iterations"],
                equilibrium_claim=True,
            )
        else:
            await require_local()  # gto-cuda preview: local GPU only
            spot = {
                "board": req.board,
                "pot_bb": pot_bb,
                "effective_stack_bb": EFF_STACK,
            }
            try:
                import gto_cuda

                results = await loop.run_in_executor(
                    _executor,
                    lambda: gto_cuda.batch_solve_rust(
                        [spot], req.iterations, MAX_BETS, ip_w, oop_w
                    ),
                )
                result = results[0]
            except Exception as e:
                raise HTTPException(
                    503,
                    "flop instant preview needs the local GPU build (gto_cuda)",
                ) from e
            postflop = PostflopResult(
                strategy=[ActionFreq(**a) for a in result["strategy"]],
                exploitability=result["exploitability"],
                backend="gpu-preview",
                iterations=result["iterations"],
                equilibrium_claim=False,
            )

    return SimResponse(
        position=req.position,
        fold_equity=outcome["fold_equity"],
        call_freq=outcome["call_freq"],
        threebet_freq=outcome["threebet_freq"],
        bb_hands=bb_hands,
        postflop=postflop,
    )
