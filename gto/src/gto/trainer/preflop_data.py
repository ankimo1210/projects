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


def _face2(
    threeb: set[str],
    call: set[str],
    mixed3: dict[str, float] | None = None,
    mixed_call: dict[str, float] | None = None,
) -> dict[str, dict]:
    """Facing an open: {"3B": %, "C": %, "F": %}. A mixed-3bet hand that ALSO
    appears in `call` puts its non-3bet remainder on CALL instead of FOLD
    (QQ that doesn't 3bet should call, not fold). `mixed_call` = partial
    pure-call hands ({hand: call%}, remainder folds)."""
    result = {}
    mixed3 = mixed3 or {}
    mixed_call = mixed_call or {}
    for h in ALL_HANDS:
        if h in threeb or h in mixed3:
            f3 = mixed3.get(h, 100)
            c = 100 - f3 if h in call else 0
            result[h] = {"3B": f3, "C": c, "F": 100 - f3 - c}
        elif h in call:
            result[h] = {"3B": 0, "C": 100, "F": 0}
        elif h in mixed_call:
            mc = mixed_call[h]
            result[h] = {"3B": 0, "C": mc, "F": 100 - mc}
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
    "QQ",
    "JJ",
    "AJs",
    "KQs",
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
# _face2: the non-3bet remainder of QQ/JJ/TT/AJs/KQs CALLS (the old _face
# helper folded it — a chart bug: QQ folding 30% to a BTN open).
FACING_BB_VS_BTN = _face2(_BB_BTN_3BET, _BB_BTN_CALL, _BB_BTN_3BET_MIXED)

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
FACING_BB_VS_CO = _face2(_BB_CO_3BET, _BB_CO_CALL)

# BB vs UTG open (tight 3bet ~5%, defend ~33%)
_BB_UTG_3BET = {"AA", "KK", "AKs"}
_BB_UTG_3BET_MIXED = {
    "QQ": 60, "JJ": 30, "AKo": 70, "AQs": 40,
    "A5s": 50, "A4s": 35, "KQs": 25, "76s": 25, "65s": 25,
}
_BB_UTG_CALL = {
    "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "KQs", "KJs", "KTs", "K9s",
    "QJs", "QTs", "Q9s",
    "JTs", "J9s", "T9s", "T8s", "98s", "97s", "87s", "86s",
    "76s", "75s", "65s", "64s", "54s", "53s", "43s",
    "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "QJo", "JTo",
}
FACING_BB_VS_UTG = _face2(_BB_UTG_3BET, _BB_UTG_CALL, _BB_UTG_3BET_MIXED)

# BB vs HJ open
_BB_HJ_3BET = {"AA", "KK", "AKs"}
_BB_HJ_3BET_MIXED = {
    "QQ": 70, "JJ": 40, "TT": 20, "AKo": 80, "AQs": 50, "AJs": 25,
    "KQs": 35, "A5s": 60, "A4s": 45, "A3s": 25,
    "87s": 25, "76s": 30, "65s": 30, "54s": 25,
}
_BB_HJ_CALL = {
    "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s",
    "QJs", "QTs", "Q9s", "Q8s",
    "JTs", "J9s", "J8s", "T9s", "T8s", "T7s",
    "98s", "97s", "96s", "87s", "86s", "85s",
    "76s", "75s", "74s", "65s", "64s", "63s", "54s", "53s", "43s",
    "AKo", "AQo", "AJo", "ATo", "A9o",
    "KQo", "KJo", "KTo", "QJo", "QTo", "JTo", "T9o", "98o",
}
FACING_BB_VS_HJ = _face2(_BB_HJ_3BET, _BB_HJ_CALL, _BB_HJ_3BET_MIXED)

# BB vs SB open (3x; widest defend, polar+linear 3bet ~13%)
_BB_SB_3BET = {"AA", "KK", "QQ", "AKs", "AKo"}
_BB_SB_3BET_MIXED = {
    "JJ": 60, "TT": 40, "99": 25,
    "AQs": 60, "AQo": 50, "AJs": 40, "ATs": 25,
    "KQs": 45, "KJs": 25, "K9s": 25,
    "A5s": 70, "A4s": 60, "A3s": 50, "A2s": 40,
    "Q9s": 20, "J9s": 20, "T9s": 30, "98s": 30,
    "87s": 35, "76s": 35, "65s": 35, "54s": 30,
}
_BB_SB_CALL = {
    "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
    "QJs", "QTs", "Q9s", "Q8s", "Q7s", "Q6s", "Q5s", "Q4s",
    "JTs", "J9s", "J8s", "J7s", "J6s",
    "T9s", "T8s", "T7s", "T6s",
    "98s", "97s", "96s", "95s",
    "87s", "86s", "85s", "84s",
    "76s", "75s", "74s", "65s", "64s", "63s", "54s", "53s", "43s",
    "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o",
    "KQo", "KJo", "KTo", "K9o",
    "QJo", "QTo", "Q9o", "JTo", "J9o", "T9o", "T8o", "98o", "87o",
}
FACING_BB_VS_SB = _face2(_BB_SB_3BET, _BB_SB_CALL, _BB_SB_3BET_MIXED)

FACING_RANGES: dict[str, dict] = {
    "BB_vs_BTN": FACING_BB_VS_BTN,
    "BB_vs_CO": FACING_BB_VS_CO,
    "BB_vs_UTG": FACING_BB_VS_UTG,
    "BB_vs_HJ": FACING_BB_VS_HJ,
    "BB_vs_SB": FACING_BB_VS_SB,
}

# ---------------------------------------------------------------------------
# Opener facing the BB 3bet: 4bet / call / fold
# Every continue (4B or C) hand MUST be inside the opener's RFI support —
# enforced by gto.trainer.chart_validator (M2 consistency validator).
# ---------------------------------------------------------------------------


def _vs3(
    fourb: set[str],
    call: set[str],
    mixed4: dict[str, float] | None = None,
    mixed_call: dict[str, float] | None = None,
) -> dict[str, dict]:
    """Opener response vs a 3bet: {"4B": %, "C": %, "F": %}. A mixed-4bet
    hand that also appears in `call` puts its remainder on CALL.
    `mixed_call` = partial pure-call hands ({hand: call%}, remainder folds)."""
    result = {}
    mixed4 = mixed4 or {}
    mixed_call = mixed_call or {}
    for h in ALL_HANDS:
        if h in fourb or h in mixed4:
            f4 = mixed4.get(h, 100)
            c = 100 - f4 if h in call else 0
            result[h] = {"4B": f4, "C": c, "F": 100 - f4 - c}
        elif h in call:
            result[h] = {"4B": 0, "C": 100, "F": 0}
        elif h in mixed_call:
            mc = mixed_call[h]
            result[h] = {"4B": 0, "C": mc, "F": 100 - mc}
        else:
            result[h] = {"4B": 0, "C": 0, "F": 100}
    return result


# Continue-vs-3bet targets (combo-weighted over the opening range): the
# tighter the open, the higher the continue share — UTG ~55%, BTN/SB ~50%.
VS_3BET_UTG = _vs3(
    {"AA", "KK"},
    {"QQ", "JJ", "TT", "AKs", "AKo", "AQs", "AJs", "ATs", "KQs"},
    {"QQ": 50, "AKs": 60, "AKo": 30, "A5s": 25},
    {"99": 80, "88": 55, "77": 30, "AQo": 60, "AJo": 30, "KQo": 25,
     "A9s": 30, "A8s": 25, "A4s": 35, "A3s": 25, "A2s": 20,
     "KJs": 70, "KTs": 45, "QJs": 55, "QTs": 30, "JTs": 65, "J9s": 30,
     "T9s": 50, "T8s": 25, "98s": 40, "87s": 35, "76s": 30, "65s": 25,
     "54s": 25},
)
VS_3BET_HJ = _vs3(
    {"AA", "KK"},
    {"QQ", "JJ", "TT", "99", "AKs", "AKo", "AQs", "AJs", "ATs", "KQs"},
    {"QQ": 50, "AKs": 50, "AKo": 35, "A5s": 30},
    {"88": 75, "77": 55, "66": 35, "55": 20, "AQo": 60, "AJo": 35,
     "ATo": 15, "KQo": 35, "KJo": 15,
     "A9s": 45, "A8s": 35, "A7s": 30, "A6s": 25, "A4s": 35, "A3s": 30,
     "A2s": 20, "KJs": 75, "KTs": 55, "K9s": 25, "QJs": 65, "QTs": 45,
     "Q9s": 20, "JTs": 70, "J9s": 40, "T9s": 60, "T8s": 30,
     "98s": 50, "97s": 25, "87s": 45, "86s": 20, "76s": 40, "75s": 15,
     "65s": 30, "64s": 15, "54s": 30},
)
VS_3BET_CO = _vs3(
    {"AA", "KK"},
    {"QQ", "JJ", "TT", "99", "AKs", "AKo", "AQs", "AJs", "ATs", "KQs"},
    {"QQ": 60, "AKs": 50, "AKo": 45, "A5s": 35, "A4s": 25},
    {"88": 90, "77": 80, "66": 60, "55": 45, "44": 30, "33": 20, "22": 20,
     "AQo": 90, "AJo": 65, "ATo": 40, "A9o": 20, "KQo": 65, "KJo": 40,
     "QJo": 30, "JTo": 20,
     "A9s": 70, "A8s": 60, "A7s": 50, "A6s": 40, "A3s": 45, "A2s": 35,
     "KJs": 95, "KTs": 80, "K9s": 55, "K8s": 30, "QJs": 90, "QTs": 75,
     "Q9s": 45, "JTs": 90, "J9s": 65, "J8s": 35, "T9s": 80, "T8s": 55,
     "98s": 70, "97s": 45, "87s": 65, "86s": 35, "76s": 60, "75s": 30,
     "65s": 50, "64s": 25, "54s": 45},
)
VS_3BET_BTN = _vs3(
    {"AA", "KK"},
    {"QQ", "JJ", "TT", "99", "AKs", "AKo", "AQs", "AQo", "AJs", "ATs", "KQs"},
    {"QQ": 35, "AKs": 45, "AKo": 30, "A5s": 40, "A4s": 30},
    {"88": 90, "77": 80, "66": 65, "55": 50, "44": 35, "33": 25, "22": 25,
     "AJo": 70, "ATo": 45, "A9o": 15, "KQo": 70, "KJo": 45, "KTo": 25,
     "QJo": 40, "QTo": 20, "JTo": 35,
     "A9s": 80, "A8s": 70, "A7s": 60, "A6s": 50, "A3s": 50, "A2s": 40,
     "KJs": 90, "KTs": 80, "K9s": 55, "K8s": 30, "K7s": 20,
     "QJs": 85, "QTs": 75, "Q9s": 50, "Q8s": 25,
     "JTs": 85, "J9s": 65, "J8s": 35, "T9s": 80, "T8s": 55, "T7s": 25,
     "98s": 70, "97s": 45, "96s": 20, "87s": 65, "86s": 35,
     "76s": 60, "75s": 30, "65s": 55, "64s": 25, "54s": 50},
)
VS_3BET_SB = _vs3(
    {"AA", "KK"},
    {"QQ", "JJ", "TT", "99", "AKs", "AKo", "AQs", "AQo", "AJs", "ATs", "KQs"},
    {"QQ": 45, "AKs": 55, "AKo": 40, "A5s": 40, "A4s": 30},
    {"88": 85, "77": 75, "66": 60, "55": 45, "44": 30, "33": 20, "22": 20,
     "AJo": 60, "ATo": 35, "KQo": 60, "KJo": 35, "KTo": 20,
     "QJo": 30, "QTo": 15, "JTo": 25,
     "A9s": 75, "A8s": 65, "A7s": 55, "A6s": 45, "A3s": 45, "A2s": 35,
     "KJs": 85, "KTs": 75, "K9s": 50, "K8s": 25,
     "QJs": 80, "QTs": 70, "Q9s": 45, "Q8s": 20,
     "JTs": 80, "J9s": 60, "J8s": 30, "T9s": 75, "T8s": 50, "T7s": 20,
     "98s": 65, "97s": 40, "87s": 60, "86s": 30,
     "76s": 55, "75s": 25, "65s": 50, "64s": 20, "54s": 45},
)

VS_3BET_RANGES: dict[str, dict] = {
    "UTG_vs_BB_3bet": VS_3BET_UTG,
    "HJ_vs_BB_3bet": VS_3BET_HJ,
    "CO_vs_BB_3bet": VS_3BET_CO,
    "BTN_vs_BB_3bet": VS_3BET_BTN,
    "SB_vs_BB_3bet": VS_3BET_SB,
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
