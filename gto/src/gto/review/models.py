"""Data models for parsed PokerStars hand histories."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

STREETS = ("preflop", "flop", "turn", "river")


@dataclass
class Stakes:
    small_blind: float
    big_blind: float
    currency: str = "USD"


@dataclass
class Player:
    seat: int
    name: str
    stack: float
    sitting_out: bool = False


@dataclass
class BlindPost:
    player: str
    blind_type: str  # "small" | "big" | "small_and_big" | "ante"
    amount: float


@dataclass
class Action:
    street: str  # one of STREETS
    actor: str
    action: str  # "fold" | "check" | "call" | "bet" | "raise"
    amount: float | None = None  # chips added (call/bet amount, raise increment)
    raise_to: float | None = None  # total size for raises ("raises $X to $Y")
    all_in: bool = False


@dataclass
class ShowdownEntry:
    player: str
    cards: tuple[str, str] | None  # None when mucked without reveal
    mucked: bool = False
    description: str | None = None  # e.g. "a pair of Kings"


@dataclass
class UncalledBet:
    player: str
    amount: float


@dataclass
class Winner:
    player: str
    amount: float
    pot: str = "pot"  # "pot" | "main pot" | "side pot" | "side pot-N"


@dataclass
class DeviationFlag:
    flag: str  # "ok" | "loose" | "tight" | "missing_data"
    hand: str | None = None  # 169-grid label, e.g. "AKo"
    spot_type: str | None = None  # "RFI" | "FACING"
    position: str | None = None  # hero position ("HJ") or scenario ("BB_vs_BTN")
    hero_action: str | None = None  # encoded: "R" | "3B" | "C" | "F"
    gto_action: str | None = None
    gto_frequencies: dict[str, float] = field(default_factory=dict)
    ev_loss: float | None = None
    reason: str | None = None  # populated when flag == "missing_data"


@dataclass
class ParsedHand:
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
    actions: dict[str, list[Action]]  # street -> ordered actions
    board: list[str]
    showdown: list[ShowdownEntry]
    uncalled_bets: list[UncalledBet]
    winners: list[Winner]
    total_pot: float | None
    rake: float | None
    zoom: bool = False
    positions: dict[str, str] = field(default_factory=dict)  # player -> position
    preflop_deviation: DeviationFlag | None = None


@dataclass
class ParseError:
    index: int  # 0-based index of the hand chunk within the input
    message: str
    snippet: str  # first line of the failed chunk


@dataclass
class ParseResult:
    hands: list[ParsedHand]
    errors: list[ParseError]
