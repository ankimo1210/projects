"""PokerStars cash-game hand history parser (Hold'em No Limit, 2-9 handed).

Parses one or many concatenated hands from raw text. Each hand is parsed
inside its own try/except so malformed input never crashes the caller;
failures are reported per hand via ParseResult.errors.

Also attaches a preflop deviation flag for hero's first preflop decision,
reusing the trainer's hardcoded GTO frequency tables (RFI + BB facing).
"""

from __future__ import annotations

import re
from datetime import datetime

from gto.trainer.preflop_data import (
    FACING_RANGES,
    RFI_BY_POS,
    get_facing_spot,
    get_rfi_spot,
    hand_label,
)

from .models import (
    STREETS,
    Action,
    BlindPost,
    DeviationFlag,
    ParsedHand,
    ParseError,
    ParseResult,
    Player,
    ShowdownEntry,
    Stakes,
    UncalledBet,
    Winner,
)

# ---------------------------------------------------------------------------
# Line patterns
# ---------------------------------------------------------------------------

_HAND_START_RE = re.compile(r"^PokerStars (?:Zoom )?Hand #", re.MULTILINE)

_HEADER_RE = re.compile(
    r"^PokerStars (?P<zoom>Zoom )?Hand #(?P<hand_id>\d+):\s+"
    r"Hold'em No Limit\s+"
    r"\((?P<symbol>[$€£])(?P<sb>[\d,.]+)/[$€£](?P<bb>[\d,.]+)(?: (?P<currency>[A-Z]{3}))?\)\s+-\s+"
    r"(?P<dt>\d{4}/\d{2}/\d{2} \d{1,2}:\d{2}:\d{2})(?: (?P<tz>[A-Z]{1,4}))?"
)

_TABLE_RE = re.compile(
    r"^Table '(?P<name>[^']+)'(?: (?P<max>\d+)-max)? Seat #(?P<button>\d+) is the button"
)

_SEAT_RE = re.compile(
    r"^Seat (?P<seat>\d+): (?P<name>.+?) \([$€£](?P<stack>[\d,.]+) in chips\)"
    r"(?P<out> is sitting out)?$"
)

_POST_RE = re.compile(
    r"^(?P<name>.+?): posts "
    r"(?P<kind>small blind|big blind|small & big blinds|the ante) "
    r"[$€£](?P<amount>[\d,.]+)(?: and is all-in)?$"
)

_SECTION_RE = re.compile(
    r"^\*\*\* (?P<section>HOLE CARDS|FLOP|TURN|RIVER|SHOW DOWN|SUMMARY) \*\*\*"
)

_DEALT_RE = re.compile(r"^Dealt to (?P<name>.+?) \[(?P<cards>[^\]]+)\]$")

_ACTION_RE = re.compile(
    r"^(?P<name>.+?): (?P<verb>folds|checks|calls|bets|raises)"
    r"(?: [$€£](?P<amount>[\d,.]+))?(?: to [$€£](?P<to>[\d,.]+))?"
    r"(?P<allin> and is all-in)?$"
)

_UNCALLED_RE = re.compile(r"^Uncalled bet \([$€£](?P<amount>[\d,.]+)\) returned to (?P<name>.+)$")

_COLLECTED_RE = re.compile(
    r"^(?P<name>.+?) collected [$€£](?P<amount>[\d,.]+) from "
    r"(?P<pot>pot|main pot|side pot(?:-\d+)?)$"
)

_SHOWS_RE = re.compile(r"^(?P<name>.+?): shows \[(?P<cards>[^\]]+)\](?: \((?P<desc>.+)\))?$")
_MUCKS_RE = re.compile(r"^(?P<name>.+?): mucks hand$")

_TOTAL_RE = re.compile(r"^Total pot [$€£](?P<pot>[\d,.]+).*?\|\s*Rake [$€£](?P<rake>[\d,.]+)")
_BOARD_RE = re.compile(r"^Board \[(?P<cards>[^\]]+)\]$")
_SUMMARY_MUCKED_RE = re.compile(
    r"^Seat \d+: (?P<name>.+?)(?: \([^)]+\))? mucked \[(?P<cards>[^\]]+)\]"
)

_BRACKETS_RE = re.compile(r"\[([^\]]+)\]")

_POST_KIND = {
    "small blind": "small",
    "big blind": "big",
    "small & big blinds": "small_and_big",
    "the ante": "ante",
}

# Fallback when the header carries a currency symbol but no 3-letter code.
_CURRENCY_BY_SYMBOL = {"$": "USD", "€": "EUR", "£": "GBP"}

_VERB_TO_ACTION = {
    "folds": "fold",
    "checks": "check",
    "calls": "call",
    "bets": "bet",
    "raises": "raise",
}


def _money(text: str) -> float:
    return float(text.replace(",", ""))


def _cards(text: str) -> list[str]:
    return text.split()


# ---------------------------------------------------------------------------
# Splitting concatenated hands
# ---------------------------------------------------------------------------


def split_hands(text: str) -> list[str]:
    """Split raw text into per-hand chunks at PokerStars headers.

    Leading text before the first header becomes its own (failing) chunk so
    garbage is reported rather than silently dropped.
    """
    starts = [m.start() for m in _HAND_START_RE.finditer(text)]
    if not starts:
        return [text] if text.strip() else []
    chunks: list[str] = []
    head = text[: starts[0]]
    if head.strip():
        chunks.append(head)
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunks.append(text[start:end])
    return chunks


# ---------------------------------------------------------------------------
# Position assignment
# ---------------------------------------------------------------------------


def _compute_positions(
    players: list[Player], button_seat: int, sb_name: str | None, bb_name: str | None
) -> dict[str, str]:
    """Assign position labels (SB, BB, UTG..., HJ, CO, BTN) to dealt-in players."""
    dealt = [p for p in players if not p.sitting_out]
    n = len(dealt)
    if n < 2:
        return {}
    ordered = sorted(dealt, key=lambda p: p.seat)
    if n == 2:
        # Heads-up: the button posts the small blind.
        btn = next((p for p in ordered if p.seat == button_seat), ordered[0])
        other = next(p for p in ordered if p.name != btn.name)
        return {btn.name: "SB", other.name: "BB"}
    names = [p.name for p in ordered]
    if sb_name in names:
        start, blinds = names.index(sb_name), ["SB", "BB"]
    elif bb_name in names:
        # Dead small blind: anchor on the big-blind poster; no seat is the SB.
        start, blinds = names.index(bb_name), ["BB"]
    else:
        # No blind posts at all: assume the first seat after the button is the SB.
        start = next((i for i, p in enumerate(ordered) if p.seat > button_seat), 0)
        blinds = ["SB", "BB"]
    ordered = ordered[start:] + ordered[:start]
    middle = n - len(blinds)  # seats between the blinds and BTN, inclusive of BTN
    back = ["HJ", "CO", "BTN"][-min(middle, 3) :]
    front = [f"UTG+{i}" if i else "UTG" for i in range(middle - len(back))]
    labels = [*blinds, *front, *back]
    return {p.name: label for p, label in zip(ordered, labels, strict=True)}


# ---------------------------------------------------------------------------
# Preflop deviation flag
# ---------------------------------------------------------------------------

_RFI_ENCODE = {"raise": "R", "call": "C", "check": "C", "fold": "F"}
_FACING_ENCODE = {"raise": "3B", "call": "C", "fold": "F"}
_AGGRESSION = {"F": 0, "C": 1, "R": 2, "3B": 2}


def preflop_deviation(hand: ParsedHand) -> DeviationFlag:
    """Classify hero's first preflop decision against the trainer GTO tables.

    Returns flag "ok" | "loose" | "tight", or "missing_data" with a reason
    when the spot is not covered by the hardcoded preflop ranges.
    """

    def missing(reason: str, **kwargs: str) -> DeviationFlag:
        return DeviationFlag(flag="missing_data", reason=reason, **kwargs)

    if not hand.hero_name or not hand.hero_cards:
        return missing("hero hole cards unknown")
    card_a, card_b = hand.hero_cards
    try:
        label = hand_label(card_a[0], card_b[0], suited=card_a[1] == card_b[1])
    except (KeyError, IndexError):
        return missing(f"invalid hero cards: {hand.hero_cards}")
    position = hand.positions.get(hand.hero_name)
    if position is None:
        return missing("hero position unknown", hand=label)

    preflop = hand.actions["preflop"]
    hero_idx = next((i for i, a in enumerate(preflop) if a.actor == hand.hero_name), None)
    if hero_idx is None:
        return missing("hero had no preflop decision", hand=label, position=position)
    hero_act = preflop[hero_idx]
    prior = preflop[:hero_idx]
    raises = [a for a in prior if a.action in ("raise", "bet")]
    limps = [a for a in prior if a.action == "call"]

    if not raises and not limps:
        if position not in RFI_BY_POS:
            return missing(f"no RFI data for position {position}", hand=label, position=position)
        spot_type, scenario = "RFI", position
        encoded = _RFI_ENCODE.get(hero_act.action)
        spot = get_rfi_spot(position, label)
    elif len(raises) == 1 and not limps and position == "BB":
        raiser_pos = hand.positions.get(raises[0].actor)
        scenario = f"BB_vs_{raiser_pos}"
        if scenario not in FACING_RANGES:
            return missing(f"no facing data for scenario {scenario}", hand=label, position=scenario)
        spot_type = "FACING"
        encoded = _FACING_ENCODE.get(hero_act.action)
        spot = get_facing_spot(scenario, label)
    else:
        return missing(
            "unsupported preflop spot (limped or multi-raised pot)",
            hand=label,
            position=position,
        )

    if encoded is None:
        return missing(f"unmapped hero action {hero_act.action!r}", hand=label, position=scenario)
    freqs = spot.freqs
    gto = spot.gto_action()
    hero_freq = freqs.get(encoded, 0)
    if encoded == gto or hero_freq >= 40:
        flag = "ok"
    elif _AGGRESSION[encoded] > _AGGRESSION[gto]:
        flag = "loose"
    else:
        flag = "tight"
    return DeviationFlag(
        flag=flag,
        hand=label,
        spot_type=spot_type,
        position=scenario,
        hero_action=encoded,
        gto_action=gto,
        gto_frequencies=dict(freqs),
        ev_loss=spot.ev_loss(encoded),
    )


# ---------------------------------------------------------------------------
# Single-hand parsing
# ---------------------------------------------------------------------------


def parse_hand(text: str) -> ParsedHand:
    """Parse a single PokerStars hand. Raises ValueError on malformed input."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty hand text")
    header = _HEADER_RE.match(lines[0])
    if header is None:
        raise ValueError(f"unrecognized hand header: {lines[0][:80]!r}")

    stakes = Stakes(
        small_blind=_money(header["sb"]),
        big_blind=_money(header["bb"]),
        currency=header["currency"] or _CURRENCY_BY_SYMBOL.get(header["symbol"], "USD"),
    )
    played_at = datetime.strptime(header["dt"], "%Y/%m/%d %H:%M:%S")

    table_name: str | None = None
    max_players: int | None = None
    button_seat: int | None = None
    players: list[Player] = []
    posts: list[BlindPost] = []
    actions: dict[str, list[Action]] = {street: [] for street in STREETS}
    board: list[str] = []
    showdown: dict[str, ShowdownEntry] = {}
    uncalled_bets: list[UncalledBet] = []
    winners: list[Winner] = []
    total_pot: float | None = None
    rake: float | None = None
    hero_name: str | None = None
    hero_cards: tuple[str, str] | None = None
    section = "setup"

    for line in lines[1:]:
        sm = _SECTION_RE.match(line)
        if sm:
            name = sm["section"]
            if name == "HOLE CARDS":
                section = "preflop"
            elif name == "FLOP":
                section = "flop"
                groups = _BRACKETS_RE.findall(line)
                if groups:
                    board = _cards(groups[0])
            elif name in ("TURN", "RIVER"):
                section = name.lower()
                groups = _BRACKETS_RE.findall(line)
                if groups:
                    board.extend(_cards(groups[-1]))
            elif name == "SHOW DOWN":
                section = "showdown"
            elif name == "SUMMARY":
                section = "summary"
            continue

        # Lines meaningful in any section.
        m = _UNCALLED_RE.match(line)
        if m:
            uncalled_bets.append(UncalledBet(player=m["name"], amount=_money(m["amount"])))
            continue
        m = _COLLECTED_RE.match(line)
        if m:
            winners.append(Winner(player=m["name"], amount=_money(m["amount"]), pot=m["pot"]))
            continue

        if section == "setup":
            m = _SEAT_RE.match(line)
            if m:
                players.append(
                    Player(
                        seat=int(m["seat"]),
                        name=m["name"],
                        stack=_money(m["stack"]),
                        sitting_out=m["out"] is not None,
                    )
                )
                continue
            m = _TABLE_RE.match(line)
            if m:
                table_name = m["name"]
                max_players = int(m["max"]) if m["max"] else None
                button_seat = int(m["button"])
                continue

        if section in ("setup", "preflop"):
            m = _POST_RE.match(line)
            if m:
                posts.append(
                    BlindPost(
                        player=m["name"],
                        blind_type=_POST_KIND[m["kind"]],
                        amount=_money(m["amount"]),
                    )
                )
                continue

        if section == "preflop":
            m = _DEALT_RE.match(line)
            if m:
                cards = _cards(m["cards"])
                if len(cards) == 2:
                    hero_name = m["name"]
                    hero_cards = (cards[0], cards[1])
                continue

        if section in STREETS:
            m = _ACTION_RE.match(line)
            if m:
                actions[section].append(
                    Action(
                        street=section,
                        actor=m["name"],
                        action=_VERB_TO_ACTION[m["verb"]],
                        amount=_money(m["amount"]) if m["amount"] else None,
                        raise_to=_money(m["to"]) if m["to"] else None,
                        all_in=m["allin"] is not None,
                    )
                )
                continue

        if section == "showdown":
            m = _SHOWS_RE.match(line)
            if m:
                cards = _cards(m["cards"])
                showdown[m["name"]] = ShowdownEntry(
                    player=m["name"],
                    cards=(cards[0], cards[1]) if len(cards) == 2 else None,
                    mucked=False,
                    description=m["desc"],
                )
                continue
            m = _MUCKS_RE.match(line)
            if m:
                showdown.setdefault(
                    m["name"], ShowdownEntry(player=m["name"], cards=None, mucked=True)
                )
                continue

        if section == "summary":
            m = _TOTAL_RE.match(line)
            if m:
                total_pot = _money(m["pot"])
                rake = _money(m["rake"])
                continue
            m = _BOARD_RE.match(line)
            if m:
                board = _cards(m["cards"])
                continue
            m = _SUMMARY_MUCKED_RE.match(line)
            if m:
                cards = _cards(m["cards"])
                entry = showdown.setdefault(
                    m["name"], ShowdownEntry(player=m["name"], cards=None, mucked=True)
                )
                if entry.cards is None and len(cards) == 2:
                    entry.cards = (cards[0], cards[1])
                continue

        # Unknown lines (chat, joins/leaves, timeouts, ...) are tolerated.

    if table_name is None or button_seat is None:
        raise ValueError("missing table line")
    if not players:
        raise ValueError("no seated players found")

    sb_name = next((p.player for p in posts if p.blind_type == "small"), None)
    bb_name = next((p.player for p in posts if p.blind_type == "big"), None)
    hand = ParsedHand(
        hand_id=header["hand_id"],
        stakes=stakes,
        played_at=played_at,
        timezone=header["tz"],
        table_name=table_name,
        max_players=max_players,
        button_seat=button_seat,
        players=players,
        hero_name=hero_name,
        hero_cards=hero_cards,
        posts=posts,
        actions=actions,
        board=board,
        showdown=list(showdown.values()),
        uncalled_bets=uncalled_bets,
        winners=winners,
        total_pot=total_pot,
        rake=rake,
        zoom=header["zoom"] is not None,
        positions=_compute_positions(players, button_seat, sb_name, bb_name),
    )
    try:
        hand.preflop_deviation = preflop_deviation(hand)
    except Exception as exc:  # never let flagging break parsing
        hand.preflop_deviation = DeviationFlag(
            flag="missing_data", reason=f"deviation computation failed: {exc}"
        )
    return hand


# ---------------------------------------------------------------------------
# Multi-hand parsing
# ---------------------------------------------------------------------------


def parse_hands(text: str) -> ParseResult:
    """Parse concatenated hands; malformed hands become ParseError entries."""
    hands: list[ParsedHand] = []
    errors: list[ParseError] = []
    for index, chunk in enumerate(split_hands(text)):
        try:
            hands.append(parse_hand(chunk))
        except Exception as exc:
            first_line = chunk.strip().splitlines()[0] if chunk.strip() else ""
            errors.append(ParseError(index=index, message=str(exc), snippet=first_line[:120]))
    return ParseResult(hands=hands, errors=errors)
