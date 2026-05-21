import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)


class SolveRequest(BaseModel):
    pot_bb: float = 3.0
    effective_stack_bb: float = 50.0
    board: list[str]
    iterations: int = 100
    max_bets: int = 2


class ActionFreq(BaseModel):
    action: str
    freq: float


class SolveResponse(BaseModel):
    strategy: list[ActionFreq]
    exploitability: float
    iterations: int
    backend: str


@router.post("/solver/solve", response_model=SolveResponse)
async def solve(req: SolveRequest):
    if not 3 <= len(req.board) <= 5:
        raise HTTPException(422, "board must have 3-5 cards")
    if req.iterations < 10 or req.iterations > 1000:
        raise HTTPException(422, "iterations must be 10-1000")

    spot = {
        "board": req.board,
        "pot_bb": req.pot_bb,
        "effective_stack_bb": req.effective_stack_bb,
    }

    loop = asyncio.get_event_loop()
    try:
        import gto_cuda

        results = await loop.run_in_executor(
            _executor,
            lambda: gto_cuda.batch_solve_rust([spot], req.iterations, req.max_bets),
        )
        result = results[0]
        backend = "gpu"
    except Exception:
        import gto_py

        result = await loop.run_in_executor(
            _executor,
            lambda: gto_py.solve_spot(
                req.pot_bb,
                req.effective_stack_bb,
                req.board,
                req.iterations,
                req.max_bets,
            ),
        )
        backend = "cpu"

    return SolveResponse(
        strategy=[ActionFreq(**a) for a in result["strategy"]],
        exploitability=result["exploitability"],
        iterations=result["iterations"],
        backend=backend,
    )
