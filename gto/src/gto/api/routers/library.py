"""Solution library lookup API.

M2 disposition: the 19,305-spot gto-cuda library is the INSTANT-PREVIEW tier
(`equilibrium_claim=false` on every row). Its solves are single-street
(flop = call->showdown) and use UNIFORM ranges — position labels differ only
via pot size. The equilibrium-grade surface is gto-hu via POST /api/solve.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from gto.library.flop_canon import board_texture, canonicalize
from gto.library.schema import get_db, spot_id

router = APIRouter()


class ActionFreq(BaseModel):
    action: str
    freq: float


class SpotStrategy(BaseModel):
    spot_id: str
    board: str
    position: str
    opponent: str
    stack_bb: float
    texture: str
    exploitability: float
    strategy: list[ActionFreq]
    # Preview tier: gto-cuda single-street approximation over uniform ranges.
    equilibrium_claim: bool = False
    tier: str = "instant-preview"


class ComboStrategy(BaseModel):
    card_a: int
    card_b: int
    action: str
    freq: float


class FlopReport(BaseModel):
    board: str
    texture: str
    check_freq: float
    bet33_freq: float
    bet75_freq: float
    bet100_freq: float


def _parse_board(board_str: str) -> list[str]:
    """Parse 'Kh7d2c' or 'Kh 7d 2c' into ['Kh','7d','2c'].

    Rejects malformed input (e.g. odd-length 'Kh7d2') with 422 rather than
    letting a 1-char token slip through the card-count check and crash deeper
    in canonicalize() as a 500.
    """
    board_str = board_str.strip()
    if " " in board_str:
        tokens = board_str.split()
    else:
        tokens = [board_str[i : i + 2] for i in range(0, len(board_str), 2)]
    if any(len(t) != 2 for t in tokens):
        raise HTTPException(422, f"malformed board {board_str!r}: each card must be 2 chars")
    return tokens


@router.get("/library/spots", response_model=list[SpotStrategy])
def list_spots(
    position: str | None = None,
    stack_bb: float = 100.0,
    limit: int = Query(50, le=200),
):
    """List available precomputed spots."""
    db = get_db()
    where = "WHERE s.stack_bb = ?"
    params: list = [stack_bb]
    if position:
        where += " AND s.position = ?"
        params.append(position.upper())

    rows = db.execute(
        f"""
        SELECT s.spot_id, s.board, s.position, s.opponent,
               s.stack_bb, s.exploitability,
               r.texture
        FROM spots s
        LEFT JOIN flop_reports r
          ON r.board = s.board AND r.position = s.position
             AND r.opponent = s.opponent AND r.stack_bb = s.stack_bb
        {where}
        ORDER BY s.computed_at DESC
        LIMIT ?
    """,
        [*params, limit],
    ).fetchall()

    result = []
    for row in rows:
        sid, board, pos, opp, stk, expl, tex = row
        agg = db.execute(
            "SELECT action, freq FROM aggregate_strategies WHERE spot_id = ? ORDER BY freq DESC",
            [sid],
        ).fetchall()
        result.append(
            SpotStrategy(
                spot_id=sid,
                board=board,
                position=pos,
                opponent=opp,
                stack_bb=stk,
                texture=tex or "",
                exploitability=expl,
                strategy=[ActionFreq(action=a, freq=f) for a, f in agg],
            )
        )
    return result


@router.get("/library/flop", response_model=SpotStrategy)
def get_flop_solution(
    board: str = Query(..., description="Board cards e.g. 'Kh7d2c'"),
    position: str = Query("BTN"),
    stack_bb: float = Query(100.0),
):
    """Get precomputed GTO strategy for a flop spot."""
    cards = _parse_board(board)
    if len(cards) != 3:
        raise HTTPException(422, "board must have exactly 3 cards for flop")

    canon = canonicalize(cards)
    canon_str = "".join(canon)
    opp = "BB"
    sid = spot_id(position.upper(), opp, stack_bb, canon_str, "flop")

    db = get_db()
    spot = db.execute(
        "SELECT spot_id, board, position, opponent, stack_bb, exploitability FROM spots WHERE spot_id = ?",
        [sid],
    ).fetchone()

    if spot is None:
        raise HTTPException(
            404,
            f"Solution not found for {position} vs {opp} {canon_str} {stack_bb}bb. "
            "Run batch computation first.",
        )

    agg = db.execute(
        "SELECT action, freq FROM aggregate_strategies WHERE spot_id = ? ORDER BY freq DESC", [sid]
    ).fetchall()

    tex = board_texture(canon)
    return SpotStrategy(
        spot_id=sid,
        board=canon_str,
        position=spot[2],
        opponent=spot[3],
        stack_bb=spot[4],
        texture=tex,
        exploitability=spot[5],
        strategy=[ActionFreq(action=a, freq=f) for a, f in agg],
    )


@router.get("/library/flop/combos", response_model=list[ComboStrategy])
def get_combo_strategies(
    board: str = Query(...),
    position: str = Query("BTN"),
    stack_bb: float = Query(100.0),
):
    """Get per-combo GTO strategies for range grid coloring."""
    cards = _parse_board(board)
    if len(cards) != 3:
        raise HTTPException(422, "board must have 3 cards")

    canon = canonicalize(cards)
    canon_str = "".join(canon)
    sid = spot_id(position.upper(), "BB", stack_bb, canon_str, "flop")

    db = get_db()
    rows = db.execute(
        "SELECT card_a, card_b, action, freq FROM combo_strategies WHERE spot_id = ?", [sid]
    ).fetchall()

    if not rows:
        raise HTTPException(404, "Solution not found.")

    return [ComboStrategy(card_a=r[0], card_b=r[1], action=r[2], freq=r[3]) for r in rows]


@router.get("/library/report", response_model=list[FlopReport])
def get_flop_report(
    position: str = Query("BTN"),
    stack_bb: float = Query(100.0),
    texture: str | None = None,
    limit: int = Query(100, le=1755),
):
    """Get aggregated report across all computed flops."""
    db = get_db()
    where = "WHERE position = ? AND stack_bb = ?"
    params: list = [position.upper(), stack_bb]
    if texture:
        where += " AND texture = ?"
        params.append(texture)

    rows = db.execute(
        f"""
        SELECT board, texture, check_freq, bet33_freq, bet75_freq, bet100_freq
        FROM flop_reports {where}
        ORDER BY bet33_freq DESC
        LIMIT ?
    """,
        [*params, limit],
    ).fetchall()

    return [
        FlopReport(
            board=r[0],
            texture=r[1],
            check_freq=r[2] or 0.0,
            bet33_freq=r[3] or 0.0,
            bet75_freq=r[4] or 0.0,
            bet100_freq=r[5] or 0.0,
        )
        for r in rows
    ]
