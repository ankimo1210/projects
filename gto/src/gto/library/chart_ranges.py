"""Chart-derived range presets for the 6max position-pair matrix (M2).

6max postflop is solved as 2-player subgames between position pairs with
ranges FIXED by the preflop charts (mode-matrix spec F1). This module turns
the hand-class charts in `gto.trainer.preflop_data` into range-notation
strings consumable by `parse_range_notation` / the gto-hu bindings.

Range provenance per pot type:
- SRP  (opener raises, BB calls):  opener = RFI R%, BB = defend C%.
- 3bet (BB 3bets, opener calls):   BB = defend 3B%, opener = RFI R% x vs-3bet
  C% (the conditional range that opened AND then called the 3bet).

Postflop position: the opener is IP against the BB — except the SB, who acts
first postflop in 6max (SB opener = OOP, BB = IP). This differs from the HU
convention where SB/BTN is always IP.
"""

from __future__ import annotations

from gto.trainer.preflop_data import FACING_RANGES, RFI_BY_POS, VS_3BET_RANGES

CHART_OPENERS = ("UTG", "HJ", "CO", "BTN", "SB")


def _notation(weights: dict[str, float]) -> str:
    """Hand-class weights (0..1) -> "AA,QQ:0.6,..." notation, zeros dropped."""
    parts = []
    for hand, w in weights.items():
        if w <= 0.0:
            continue
        parts.append(hand if w >= 1.0 else f"{hand}:{round(w, 4)}")
    if not parts:
        raise ValueError("chart-derived range is empty")
    return ",".join(parts)


def opener_rfi_weights(opener: str) -> dict[str, float]:
    return {h: f.get("R", 0) / 100.0 for h, f in RFI_BY_POS[opener].items()}


def bb_defend_call_weights(opener: str) -> dict[str, float]:
    chart = FACING_RANGES[f"BB_vs_{opener}"]
    return {h: f.get("C", 0) / 100.0 for h, f in chart.items()}


def bb_3bet_weights(opener: str) -> dict[str, float]:
    chart = FACING_RANGES[f"BB_vs_{opener}"]
    return {h: f.get("3B", 0) / 100.0 for h, f in chart.items()}


def opener_call_vs_3bet_weights(opener: str) -> dict[str, float]:
    """Conditional: opened AND called the 3bet (open freq x call freq)."""
    rfi = RFI_BY_POS[opener]
    vs3 = VS_3BET_RANGES[f"{opener}_vs_BB_3bet"]
    return {
        h: (rfi[h].get("R", 0) / 100.0) * (vs3[h].get("C", 0) / 100.0)
        for h in rfi
    }


def chart_ranges(opener: str, pot_type: str) -> dict:
    """Range notations for an opener-vs-BB subgame.

    Returns {"ip": notation, "oop": notation, "opener_is_ip": bool}.
    """
    if opener not in CHART_OPENERS:
        raise ValueError(f"no charts for opener {opener!r} (need one of {CHART_OPENERS})")
    if pot_type == "srp":
        opener_w = opener_rfi_weights(opener)
        bb_w = bb_defend_call_weights(opener)
    elif pot_type == "3bet":
        opener_w = opener_call_vs_3bet_weights(opener)
        bb_w = bb_3bet_weights(opener)
    else:
        raise ValueError(f"charts cover srp and 3bet pots, not {pot_type!r}")

    opener_is_ip = opener != "SB"  # SB acts first postflop in 6max
    opener_n, bb_n = _notation(opener_w), _notation(bb_w)
    if opener_is_ip:
        return {"ip": opener_n, "oop": bb_n, "opener_is_ip": True}
    return {"ip": bb_n, "oop": opener_n, "opener_is_ip": False}
