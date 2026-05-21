"""
6-max NLHE 100bb GTO-approximate preflop ranges.
Action frequencies: {"R": raise%, "C": call%, "F": fold%}
RFI = Raise First In (open).
Facing = facing a single open, response is 3bet/call/fold.
"""

from __future__ import annotations

from dataclasses import dataclass

RANKS = "AKQJT98765432"

# ---------------------------------------------------------------------------
# Hand combo helpers
# ---------------------------------------------------------------------------


def hand_label(r1: str, r2: str, suited: bool) -> str:
    """Return canonical hand label, e.g. 'AKs', 'AKo', 'AA'."""
    order = {r: i for i, r in enumerate(RANKS)}
    if r1 == r2:
        return f"{r1}{r2}"
    a, b = (r1, r2) if order[r1] < order[r2] else (r2, r1)
    return f"{a}{b}{'s' if suited else 'o'}"


ALL_HANDS: list[str] = []
for i, r1 in enumerate(RANKS):
    for j, r2 in enumerate(RANKS):
        if i < j:
            ALL_HANDS.append(hand_label(r1, r2, suited=True))
            ALL_HANDS.append(hand_label(r1, r2, suited=False))
        elif i == j:
            ALL_HANDS.append(f"{r1}{r2}")


# ---------------------------------------------------------------------------
# RFI ranges — each hand maps to {"R": %, "F": %}
# Source: GTO-approximate 6-max 100bb cash game
# ---------------------------------------------------------------------------


def _rfi(raise_hands: set[str], mixed: dict[str, float] | None = None) -> dict[str, dict]:
    """Build RFI freq dict. mixed = {hand: raise_freq} for mixed-strategy hands."""
    result = {}
    for h in ALL_HANDS:
        if h in raise_hands:
            result[h] = {"R": 100, "F": 0}
        elif mixed and h in mixed:
            r = mixed[h]
            result[h] = {"R": r, "F": 100 - r}
        else:
            result[h] = {"R": 0, "F": 100}
    return result


# UTG opens ~14% of hands
_UTG_RAISE = {
    "AA",
    "KK",
    "QQ",
    "JJ",
    "TT",
    "99",
    "88",
    "77",
    "AKs",
    "AQs",
    "AJs",
    "ATs",
    "A9s",
    "A8s",
    "A5s",
    "A4s",
    "A3s",
    "A2s",
    "KQs",
    "KJs",
    "KTs",
    "K9s",
    "QJs",
    "QTs",
    "Q9s",
    "JTs",
    "J9s",
    "T9s",
    "T8s",
    "98s",
    "97s",
    "87s",
    "86s",
    "76s",
    "75s",
    "65s",
    "64s",
    "54s",
    "AKo",
    "AQo",
    "AJo",
    "ATo",
    "KQo",
    "KJo",
}
_UTG_MIXED = {"66": 50, "55": 30, "A9o": 40, "KTo": 40, "QJo": 50}
RFI_UTG = _rfi(_UTG_RAISE, _UTG_MIXED)

# HJ opens ~18%
_HJ_RAISE = _UTG_RAISE | {
    "66",
    "55",
    "44",
    "A6s",
    "A7s",
    "K8s",
    "K7s",
    "Q8s",
    "J8s",
    "T7s",
    "96s",
    "85s",
    "74s",
    "63s",
    "A9o",
    "A8o",
    "KTo",
    "K9o",
    "QJo",
    "QTo",
    "JTo",
}
_HJ_MIXED = {"33": 40, "A7o": 50, "KTo": 80}
RFI_HJ = _rfi(_HJ_RAISE, _HJ_MIXED)

# CO opens ~25%
_CO_RAISE = _HJ_RAISE | {
    "33",
    "22",
    "K6s",
    "K5s",
    "K4s",
    "K3s",
    "K2s",
    "Q7s",
    "Q6s",
    "Q5s",
    "J7s",
    "J6s",
    "T6s",
    "95s",
    "84s",
    "83s",
    "73s",
    "72s",
    "62s",
    "53s",
    "52s",
    "43s",
    "42s",
    "32s",
    "A7o",
    "A6o",
    "A5o",
    "A4o",
    "A3o",
    "A2o",
    "K9o",
    "K8o",
    "Q9o",
    "Q8o",
    "J9o",
    "J8o",
    "T9o",
    "T8o",
}
_CO_MIXED = {"K7o": 40, "Q7o": 30}
RFI_CO = _rfi(_CO_RAISE, _CO_MIXED)

# BTN opens ~40%
_BTN_RAISE = set(ALL_HANDS) - {
    "32s",
    "42s",
    "52s",
    "62s",
    "72s",
    "82s",
    "92s",
    "T2s",
    "J2s",
    "Q2s",
    "K2s",
    "43s",
    "53s",
    "63s",
    "73s",
    "83s",
    "93s",
    "32o",
    "42o",
    "52o",
    "62o",
    "72o",
    "82o",
    "92o",
    "T2o",
    "J2o",
    "Q2o",
    "K2o",
    "A2o",
    "43o",
    "53o",
    "63o",
    "73o",
    "83o",
    "93o",
    "T3o",
    "J3o",
    "Q3o",
    "K3o",
    "54o",
    "64o",
    "74o",
    "84o",
    "94o",
    "T4o",
    "J4o",
    "Q4o",
    "K4o",
    "65o",
    "75o",
    "85o",
    "95o",
    "T5o",
    "J5o",
    "Q5o",
    "76o",
    "86o",
    "96o",
    "T6o",
    "J6o",
    "Q6o",
    "87o",
    "97o",
    "T7o",
    "J7o",
    "98o",
    "T8o",
    "J8o",
    "T9o",
}
_BTN_MIXED = {"32s": 60, "42s": 70, "52s": 80}
RFI_BTN = _rfi(_BTN_RAISE, _BTN_MIXED)

# SB opens ~38% (vs BB only)
_SB_RAISE = _BTN_RAISE - {
    "32s",
    "42s",
    "52s",
    "62s",
    "43s",
    "53s",
    "32o",
    "42o",
    "52o",
    "62o",
    "72o",
    "82o",
    "43o",
    "53o",
    "63o",
    "73o",
    "54o",
    "64o",
    "74o",
    "84o",
}
_SB_MIXED = {"J2s": 50, "Q2s": 70}
RFI_SB = _rfi(_SB_RAISE, _SB_MIXED)

RFI_BY_POS: dict[str, dict] = {
    "UTG": RFI_UTG,
    "HJ": RFI_HJ,
    "CO": RFI_CO,
    "BTN": RFI_BTN,
    "SB": RFI_SB,
}

# ---------------------------------------------------------------------------
# Facing RFI: 3bet / call / fold  (BB vs BTN open as representative)
# ---------------------------------------------------------------------------


def _face(
    threeb: set[str], call: set[str], mixed3: dict[str, float] | None = None
) -> dict[str, dict]:
    result = {}
    for h in ALL_HANDS:
        if h in threeb:
            f3 = mixed3.get(h, 100) if mixed3 else 100
            result[h] = {"3B": f3, "C": 0, "F": 100 - f3}
        elif h in call:
            result[h] = {"3B": 0, "C": 100, "F": 0}
        else:
            result[h] = {"3B": 0, "C": 0, "F": 100}
    return result


# BB vs BTN open
_BB_BTN_3BET = {
    "AA",
    "KK",
    "QQ",
    "JJ",
    "AKs",
    "AQs",
    "AJs",
    "ATs",
    "KQs",
    "KJs",
    "QJs",
    "AKo",
    "AQo",
    # Bluff 3bets
    "A5s",
    "A4s",
    "A3s",
    "A2s",
    "K2s",
    "K3s",
    "K4s",
    "J9s",
    "T9s",
    "98s",
    "87s",
    "76s",
    "65s",
}
_BB_BTN_CALL = {
    "TT",
    "99",
    "88",
    "77",
    "66",
    "55",
    "44",
    "33",
    "22",
    "A9s",
    "A8s",
    "A7s",
    "A6s",
    "K9s",
    "K8s",
    "K7s",
    "K6s",
    "K5s",
    "Q9s",
    "Q8s",
    "Q7s",
    "QTs",
    "J8s",
    "JTs",
    "T8s",
    "T7s",
    "97s",
    "96s",
    "86s",
    "85s",
    "75s",
    "74s",
    "64s",
    "63s",
    "53s",
    "54s",
    "43s",
    "AJo",
    "ATo",
    "A9o",
    "KQo",
    "KJo",
    "KTo",
    "QJo",
    "QTo",
    "JTo",
    "J9o",
    "T9o",
    "98o",
}
_BB_BTN_3BET_MIXED = {"QQ": 70, "JJ": 60, "TT": 30, "AJs": 60, "KQs": 60}
FACING_BB_VS_BTN = _face(_BB_BTN_3BET, _BB_BTN_CALL, _BB_BTN_3BET_MIXED)

# BB vs CO open (tighter 3bet range)
_BB_CO_3BET = {
    "AA",
    "KK",
    "QQ",
    "AKs",
    "AQs",
    "AJs",
    "AKo",
    "AQo",
    "A5s",
    "A4s",
    "A3s",
    "A2s",
    "K2s",
    "K3s",
    "J9s",
    "T9s",
    "98s",
    "87s",
}
_BB_CO_CALL = {
    "JJ",
    "TT",
    "99",
    "88",
    "77",
    "66",
    "55",
    "44",
    "33",
    "22",
    "ATs",
    "A9s",
    "A8s",
    "A7s",
    "A6s",
    "KQs",
    "KJs",
    "KTs",
    "K9s",
    "K8s",
    "K7s",
    "QJs",
    "QTs",
    "Q9s",
    "Q8s",
    "JTs",
    "J8s",
    "T8s",
    "T7s",
    "97s",
    "96s",
    "86s",
    "85s",
    "75s",
    "64s",
    "54s",
    "43s",
    "AJo",
    "ATo",
    "A9o",
    "A8o",
    "KQo",
    "KJo",
    "KTo",
    "QJo",
    "QTo",
    "JTo",
    "J9o",
    "T9o",
    "98o",
}
FACING_BB_VS_CO = _face(_BB_CO_3BET, _BB_CO_CALL)

FACING_RANGES: dict[str, dict] = {
    "BB_vs_BTN": FACING_BB_VS_BTN,
    "BB_vs_CO": FACING_BB_VS_CO,
}

# ---------------------------------------------------------------------------
# Quiz spot definitions
# ---------------------------------------------------------------------------


@dataclass
class QuizSpot:
    spot_type: str  # "RFI" | "FACING"
    position: str  # e.g. "BTN", "BB_vs_BTN"
    hand: str  # e.g. "AKs"
    freqs: dict[str, float]  # action -> %
    description: str  # human-readable

    def gto_action(self) -> str:
        """Return the highest-frequency action."""
        return max(self.freqs, key=lambda a: self.freqs[a])

    def ev_loss(self, chosen: str) -> float:
        """Rough EV loss estimate in bb (heuristic)."""
        best = self.gto_action()
        if chosen == best:
            return 0.0
        # weight by frequency difference
        diff = (self.freqs.get(best, 0) - self.freqs.get(chosen, 0)) / 100
        return round(diff * 0.8, 2)  # rough scaling


def get_rfi_spot(position: str, hand: str) -> QuizSpot:
    freqs = RFI_BY_POS[position][hand]
    return QuizSpot(
        spot_type="RFI",
        position=position,
        hand=hand,
        freqs=freqs,
        description=f"{position} open (100bb, 6-max)",
    )


def get_facing_spot(scenario: str, hand: str) -> QuizSpot:
    freqs = FACING_RANGES[scenario][hand]
    pos, _, opp = scenario.partition("_vs_")
    return QuizSpot(
        spot_type="FACING",
        position=scenario,
        hand=hand,
        freqs=freqs,
        description=f"{pos} vs {opp} open (100bb, 6-max)",
    )
