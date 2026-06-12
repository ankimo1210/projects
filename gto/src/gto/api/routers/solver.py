"""Live solve for the /solver page (M2: migrated to gto-hu).

Board with 4/5 cards -> gto-hu turn+river / river equilibrium (exact
exploitability, `equilibrium_claim=true`). Board with 3 cards -> the
gto-cuda instant-preview tier (single-street call->showdown approximation,
`equilibrium_claim=false`); the correct flop equilibrium is the async tier
on POST /api/solve. The old gto-core `solve_spot` CPU fallback was retired —
if the GPU preview is unavailable the endpoint returns 503 instead of
silently serving the same approximation from a slower engine.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from gto.api.auth import require_local
from gto.api.ratelimit import rate_limited_user

router = APIRouter(dependencies=[Depends(rate_limited_user)])  # E1 gate
_executor = ThreadPoolExecutor(max_workers=2)


class SolveRequest(BaseModel):
    pot_bb: float = 3.0
    effective_stack_bb: float = 50.0
    board: list[str]
    iterations: int = 100
    max_bets: int = 2  # preview tier only; gto-hu trees use their own config


class ActionFreq(BaseModel):
    action: str
    freq: float


class SolveResponse(BaseModel):
    strategy: list[ActionFreq]
    exploitability: float
    iterations: int
    backend: str           # "gto-hu" | "gpu-preview"
    equilibrium_claim: bool


# gto-hu runs more iterations comfortably within the page's sync budget.
HU_ITER_CLAMP = {"river": (100, 10_000), "turn_river": (100, 5_000)}


@router.post("/solver/solve", response_model=SolveResponse)
async def solve(req: SolveRequest):
    if not 3 <= len(req.board) <= 5:
        raise HTTPException(422, "board must have 3-5 cards")
    if req.iterations < 10 or req.iterations > 10_000:
        raise HTTPException(422, "iterations must be 10-10000")

    loop = asyncio.get_event_loop()

    if len(req.board) in (4, 5):
        # Equilibrium tier: gto-hu with exact exploitability.
        import gto_py

        street = "river" if len(req.board) == 5 else "turn_river"
        lo, hi = HU_ITER_CLAMP[street]
        iters = max(lo, min(hi, req.iterations))
        try:
            if street == "river":
                raw = await loop.run_in_executor(
                    _executor,
                    lambda: gto_py.solve_hu_river(
                        req.board, req.pot_bb, req.effective_stack_bb, iters
                    ),
                )
            else:
                raw = await loop.run_in_executor(
                    _executor,
                    lambda: gto_py.solve_hu_turn_river(
                        req.board, req.pot_bb, req.effective_stack_bb, iters
                    ),
                )
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        return SolveResponse(
            strategy=[ActionFreq(**a) for a in raw["strategy"]],
            exploitability=raw["exploitability"],
            iterations=raw["iterations"],
            backend="gto-hu",
            equilibrium_claim=True,
        )

    # Flop: instant-preview tier (gto-cuda single-street approximation) —
    # needs the local GPU; 503 on public deploys (E1 rev 2).
    await require_local()
    spot = {
        "board": req.board,
        "pot_bb": req.pot_bb,
        "effective_stack_bb": req.effective_stack_bb,
    }
    try:
        import gto_cuda

        results = await loop.run_in_executor(
            _executor,
            lambda: gto_cuda.batch_solve_rust(
                [spot], min(req.iterations, 1000), req.max_bets
            ),
        )
        result = results[0]
    except Exception as e:
        raise HTTPException(
            503,
            "flop instant preview needs the local GPU build (gto_cuda); "
            "use POST /api/solve for the exact async flop solve",
        ) from e
    return SolveResponse(
        strategy=[ActionFreq(**a) for a in result["strategy"]],
        exploitability=result["exploitability"],
        iterations=result["iterations"],
        backend="gpu-preview",
        equilibrium_claim=False,
    )
