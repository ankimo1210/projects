"""Quiz engine: generate random spots and score answers."""

from __future__ import annotations

import random

from .preflop_data import (
    ALL_HANDS,
    FACING_RANGES,
    RFI_BY_POS,
    QuizSpot,
    get_facing_spot,
    get_rfi_spot,
)

RFI_POSITIONS = list(RFI_BY_POS.keys())
FACE_SCENARIOS = list(FACING_RANGES.keys())


def _interesting(freqs: dict) -> bool:
    """Skip trivially obvious spots (pure fold or near-pure)."""
    best_freq = max(freqs.values())
    return best_freq < 98  # some strategic complexity


def random_spot() -> QuizSpot:
    for _ in range(100):
        if random.random() < 0.6:
            pos = random.choice(RFI_POSITIONS)
            hand = random.choice(ALL_HANDS)
            spot = get_rfi_spot(pos, hand)
        else:
            sc = random.choice(FACE_SCENARIOS)
            hand = random.choice(ALL_HANDS)
            spot = get_facing_spot(sc, hand)

        if _interesting(spot.freqs):
            return spot

    # fallback
    return get_rfi_spot("BTN", "AKs")


def score_answer(spot: QuizSpot, chosen: str) -> dict:
    gto = spot.gto_action()
    ev_loss = spot.ev_loss(chosen)
    correct = (chosen == gto) or (spot.freqs.get(chosen, 0) >= 40)

    # Build sorted action list for display
    actions = sorted(spot.freqs.items(), key=lambda x: -x[1])

    return {
        "correct": correct,
        "chosen": chosen,
        "gto_action": gto,
        "gto_freq": spot.freqs.get(gto, 0),
        "all_actions": [{"action": a, "freq": f} for a, f in actions if f > 0],
        "ev_loss": ev_loss,
        "hand": spot.hand,
        "description": spot.description,
    }
