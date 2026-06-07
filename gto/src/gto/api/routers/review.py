"""Hand history review API: parse PokerStars text into structured hands."""

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gto.review import parse_hands

router = APIRouter()

# Reject pathological pastes before parsing; ~2 MB covers thousands of hands.
MAX_TEXT_CHARS = 2_000_000


class Stakes(BaseModel):
    small_blind: float
    big_blind: float
    currency: str


class Player(BaseModel):
    seat: int
    name: str
    stack: float
    sitting_out: bool


class BlindPost(BaseModel):
    player: str
    blind_type: str
    amount: float


class HandAction(BaseModel):
    street: str
    actor: str
    action: str
    amount: float | None
    raise_to: float | None
    all_in: bool


class ShowdownEntry(BaseModel):
    player: str
    cards: tuple[str, str] | None
    mucked: bool
    description: str | None


class UncalledBet(BaseModel):
    player: str
    amount: float


class Winner(BaseModel):
    player: str
    amount: float
    pot: str


class DeviationFlag(BaseModel):
    flag: str
    hand: str | None
    spot_type: str | None
    position: str | None
    hero_action: str | None
    gto_action: str | None
    gto_frequencies: dict[str, float]
    ev_loss: float | None
    reason: str | None


class ParsedHand(BaseModel):
    hand_id: str
    stakes: Stakes
    played_at: datetime | None
    timezone: str | None
    table_name: str
    max_players: int | None
    button_seat: int
    players: list[Player]
    hero_name: str | None
    hero_cards: tuple[str, str] | None
    posts: list[BlindPost]
    actions: dict[str, list[HandAction]]
    board: list[str]
    showdown: list[ShowdownEntry]
    uncalled_bets: list[UncalledBet]
    winners: list[Winner]
    total_pot: float | None
    rake: float | None
    zoom: bool
    positions: dict[str, str]
    preflop_deviation: DeviationFlag | None


class ParseError(BaseModel):
    index: int
    message: str
    snippet: str


class ParseRequest(BaseModel):
    text: str = Field(max_length=MAX_TEXT_CHARS)


class ParseResponse(BaseModel):
    hands: list[ParsedHand]
    errors: list[ParseError]


@router.post("/review/parse", response_model=ParseResponse)
def parse_hand_history(req: ParseRequest):
    if not req.text.strip():
        raise HTTPException(422, "text must not be empty")
    result = parse_hands(req.text)
    return ParseResponse(
        hands=[ParsedHand(**asdict(h)) for h in result.hands],
        errors=[ParseError(**asdict(e)) for e in result.errors],
    )
