from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import gto_py

router = APIRouter()


class EquityResponse(BaseModel):
    hero_equity: float
    villain_equity: float
    tie: float
    iterations: int


@router.get("/equity", response_model=EquityResponse)
def get_equity(
    hero: str = Query(..., description="Hero hole cards e.g. 'Ah Kh'"),
    villain: str = Query(..., description="Villain hole cards e.g. 'Qd Qc'"),
    board: str = Query("", description="Board cards e.g. '2c 7d 9h'"),
    iterations: int = Query(10_000, ge=1_000, le=100_000),
):
    try:
        result = gto_py.equity(hero, villain, board, iterations)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return EquityResponse(**result)
