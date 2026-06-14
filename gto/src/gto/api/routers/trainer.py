from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gto.trainer.quiz import random_spot, score_answer

router = APIRouter()


class QuizResponse(BaseModel):
    hand: str
    description: str
    spot_type: str
    position: str


class AnswerRequest(BaseModel):
    hand: str
    position: str
    spot_type: str
    chosen: str


class ActionFreq(BaseModel):
    action: str
    freq: float


class AnswerResponse(BaseModel):
    correct: bool
    chosen: str
    gto_action: str
    gto_freq: float
    all_actions: list[ActionFreq]
    ev_loss: float
    hand: str
    description: str


@router.get("/trainer/quiz", response_model=QuizResponse)
def get_quiz():
    spot = random_spot()
    return QuizResponse(
        hand=spot.hand,
        description=spot.description,
        spot_type=spot.spot_type,
        position=spot.position,
    )


@router.post("/trainer/answer", response_model=AnswerResponse)
def post_answer(req: AnswerRequest):
    from gto.trainer.preflop_data import get_facing_spot, get_rfi_spot

    try:
        if req.spot_type == "RFI":
            spot = get_rfi_spot(req.position, req.hand)
        else:
            spot = get_facing_spot(req.position, req.hand)
    except KeyError as e:
        raise HTTPException(
            422,
            f"unknown spot: spot_type={req.spot_type!r} "
            f"position={req.position!r} hand={req.hand!r}",
        ) from e
    result = score_answer(spot, req.chosen)
    return AnswerResponse(**result)
