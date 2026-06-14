"""
Preflop range builder: converts GTO frequency tables → combo weight arrays.

Card encoding (matches gto-core/src/eval.rs):
  card_int = rank_index * 4 + suit_index
  rank: 0=2, 1=3, ..., 8=T, 9=J, 10=Q, 11=K, 12=A
  suit: 0=c, 1=d, 2=h, 3=s
"""

from __future__ import annotations

import numpy as np

from gto.trainer.preflop_data import (
    ALL_HANDS,
    FACING_BB_VS_BTN,
    FACING_BB_VS_CO,
    FACING_BB_VS_HJ,
    FACING_BB_VS_SB,
    FACING_BB_VS_UTG,
    RFI_BTN,
    RFI_CO,
    RFI_HJ,
    RFI_SB,
    RFI_UTG,
)

NUM_COMBOS = 1326
RANK_STR = "23456789TJQKA"
SUIT_STR = "cdhs"

RFI_TABLE = {
    "BTN": RFI_BTN,
    "CO": RFI_CO,
    "SB": RFI_SB,
    "HJ": RFI_HJ,
    "UTG": RFI_UTG,
}
FACING_TABLE = {
    "BTN": FACING_BB_VS_BTN,
    "CO": FACING_BB_VS_CO,
    "SB": FACING_BB_VS_SB,
    "HJ": FACING_BB_VS_HJ,
    "UTG": FACING_BB_VS_UTG,
}


def card_int(rank_char: str, suit_char: str) -> int:
    return RANK_STR.index(rank_char) * 4 + SUIT_STR.index(suit_char)


def combo_index(a: int, b: int) -> int:
    lo, hi = (a, b) if a < b else (b, a)
    return lo * 51 - lo * (lo - 1) // 2 + hi - lo - 1


def hand_to_combo_indices(hand: str) -> list[int]:
    r1, r2 = hand[0], hand[1]
    indices = []
    if r1 == r2:  # pair
        for i, s1 in enumerate(SUIT_STR):
            for s2 in SUIT_STR[i + 1 :]:
                indices.append(combo_index(card_int(r1, s1), card_int(r2, s2)))
    elif len(hand) == 3 and hand[2] == "s":  # suited
        for s in SUIT_STR:
            indices.append(combo_index(card_int(r1, s), card_int(r2, s)))
    else:  # offsuit
        for s1 in SUIT_STR:
            for s2 in SUIT_STR:
                if s1 != s2:
                    indices.append(combo_index(card_int(r1, s1), card_int(r2, s2)))
    return indices


def build_ip_range_weights(position: str) -> np.ndarray:
    """BTN/CO/SB/HJ/UTG RFI raise-freq → weight array [1326]."""
    table = RFI_TABLE.get(position)
    if table is None:
        raise ValueError(f"Unknown position: {position}")
    w = np.zeros(NUM_COMBOS, dtype=np.float32)
    for hand, freqs in table.items():
        raise_freq = freqs.get("R", 0) / 100.0
        if raise_freq > 0:
            for idx in hand_to_combo_indices(hand):
                w[idx] = raise_freq
    return w


def build_oop_call_range_weights(ip_position: str) -> np.ndarray:
    """BB call-freq vs IP position → weight array [1326]."""
    table = FACING_TABLE.get(ip_position, FACING_BB_VS_BTN)
    w = np.zeros(NUM_COMBOS, dtype=np.float32)
    for hand, freqs in table.items():
        call_freq = freqs.get("C", 0) / 100.0
        if call_freq > 0:
            for idx in hand_to_combo_indices(hand):
                w[idx] = call_freq
    return w


def compute_preflop_outcome(position: str, dead_cards: list[str] | None = None) -> dict:
    """
    Compute preflop action distribution (fold/call/3bet) for BB vs IP open.

    Returns dict with:
      fold_equity     float  weighted average of BB folding
      call_freq       float  weighted average of BB calling
      threebet_freq   float  weighted average of BB 3betting
      ip_weights      np.ndarray[1326]  IP raising range
      oop_call_weights np.ndarray[1326] BB call range
      bb_hands        list of {hand, raise_freq, call_freq, fold_freq, threebet_freq}
    """
    rfi_table = RFI_TABLE.get(position, RFI_BTN)
    facing_table = FACING_TABLE.get(position, FACING_BB_VS_BTN)

    # Dead card set (board + hero cards)
    dead_ints: set[int] = set()
    if dead_cards:
        for cs in dead_cards:
            if len(cs) == 2:
                dead_ints.add(card_int(cs[0], cs[1]))

    # Build IP raise weights
    ip_w = build_ip_range_weights(position)
    oop_w = build_oop_call_range_weights(position)

    # Remove dead card blockers; track which combos are blocked so the per-hand
    # "alive" weight below counts only combos BB can actually hold.
    blocked = np.zeros(NUM_COMBOS, dtype=bool)
    for a in range(51):
        for b in range(a + 1, 52):
            idx = combo_index(a, b)
            if a in dead_ints or b in dead_ints:
                ip_w[idx] = 0.0
                oop_w[idx] = 0.0
                blocked[idx] = True

    # Aggregate fold / call / 3bet frequencies (weighted by how often BB holds each hand)
    fold_w = threebet_w = call_w = 0.0
    bb_hands = []

    for hand in ALL_HANDS:
        rfi_freq = rfi_table.get(hand, {}).get("R", 0) / 100.0
        facing = facing_table.get(hand, {"F": 100, "C": 0, "3B": 0})
        fold_freq = facing.get("F", 0) / 100.0
        call_freq_h = facing.get("C", 0) / 100.0
        tb_freq = facing.get("3B", 0) / 100.0

        # BB sees this hand with uniform probability (each combo equally).
        combo_idxs = hand_to_combo_indices(hand)

        # Weight: number of combos BB can actually hold (dead cards removed).
        # Counts every unblocked combo regardless of whether the hand is in the
        # call range (so fold-only hands are weighted too), but excludes blocked
        # combos — the old `or fold_freq > 0` short-circuit counted them anyway.
        alive = sum(1 for idx in combo_idxs if not blocked[idx])
        if alive == 0:
            continue

        # Aggregate (each combo counts equally for BB's range)
        weight = alive  # relative weight = number of live combos
        fold_w += weight * fold_freq
        call_w += weight * call_freq_h
        threebet_w += weight * tb_freq

        if call_freq_h > 0 or tb_freq > 0 or fold_freq > 0:
            bb_hands.append(
                {
                    "hand": hand,
                    "raise_freq": round(rfi_freq * 100, 1),
                    "call_freq": round(call_freq_h * 100, 1),
                    "fold_freq": round(fold_freq * 100, 1),
                    "threebet_freq": round(tb_freq * 100, 1),
                }
            )

    total = fold_w + call_w + threebet_w
    if total == 0:
        total = 1.0

    return {
        "fold_equity": round(fold_w / total, 4),
        "call_freq": round(call_w / total, 4),
        "threebet_freq": round(threebet_w / total, 4),
        "ip_weights": ip_w,
        "oop_call_weights": oop_w,
        "bb_hands": sorted(bb_hands, key=lambda x: -x["call_freq"]),
    }
