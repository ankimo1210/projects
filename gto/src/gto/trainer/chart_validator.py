"""Chart consistency validator (M2 — mode-matrix spec section 3 / M2 v1).

The 6max position-pair matrix is only as good as its chart data, and chart
bugs are silent (a typo'd hand class just shifts frequencies). This module
checks the structural invariants that hand-authored charts must satisfy:

1. Every chart row's action frequencies sum to 100.
2. An opener's vs-3bet chart may only continue (4B or C) hands the opener
   actually opens — you cannot face a 3bet with a hand you never raised.
3. Pairing: every BB defend chart with a nonzero 3bet line has a matching
   opener-vs-3bet chart, and vice versa.
4. Sanity bands (combo-weighted): the opener's continue frequency vs the
   3bet sits in [30%, 75%] — outside that the pair of charts cannot be a
   plausible equilibrium (auto-fold or never-fold vs 3bets).

`validate_all()` returns a list of human-readable violations; tests assert
it is empty for the shipped charts.
"""

from __future__ import annotations

from gto.trainer.preflop_data import (
    FACING_RANGES,
    RFI_BY_POS,
    VS_3BET_RANGES,
)

_SUM_TOL = 1e-9


def _combo_weight(hand: str) -> int:
    """Number of card combos in a hand class: pair 6, suited 4, offsuit 12."""
    if len(hand) == 2:
        return 6
    return 4 if hand[2] == "s" else 12


def _check_freq_sums(name: str, chart: dict[str, dict]) -> list[str]:
    out = []
    for hand, freqs in chart.items():
        total = sum(freqs.values())
        if abs(total - 100) > _SUM_TOL:
            out.append(f"{name}: {hand} frequencies sum to {total}, not 100")
        if any(v < 0 for v in freqs.values()):
            out.append(f"{name}: {hand} has a negative frequency {freqs}")
    return out


def _open_freq(opener: str, hand: str) -> float:
    return RFI_BY_POS[opener][hand].get("R", 0)


def _check_vs3bet_support(opener: str, chart: dict[str, dict]) -> list[str]:
    """Continue hands must be inside the opener's RFI support."""
    out = []
    for hand, freqs in chart.items():
        continues = freqs.get("4B", 0) + freqs.get("C", 0)
        if continues > 0 and _open_freq(opener, hand) == 0:
            out.append(
                f"{opener}_vs_BB_3bet: continues {hand} "
                f"({continues}%) but {opener} never opens it"
            )
    return out


def _continue_pct_vs_3bet(opener: str, chart: dict[str, dict]) -> float:
    """Combo-weighted continue % over the opener's (open-frequency-weighted)
    opening range."""
    num = 0.0
    den = 0.0
    for hand, freqs in chart.items():
        w = _combo_weight(hand) * _open_freq(opener, hand) / 100.0
        if w == 0:
            continue
        num += w * (freqs.get("4B", 0) + freqs.get("C", 0))
        den += w * 100.0
    return num / den if den else 0.0


def bb_3bet_pct(scenario: str) -> float:
    """Combo-weighted BB 3bet frequency for a defend chart (over all hands)."""
    chart = FACING_RANGES[scenario]
    num = sum(_combo_weight(h) * f.get("3B", 0) for h, f in chart.items())
    den = sum(_combo_weight(h) * 100.0 for h in chart)
    return num / den


def validate_all() -> list[str]:
    violations: list[str] = []

    for name, chart in RFI_BY_POS.items():
        violations += _check_freq_sums(f"RFI_{name}", chart)
    for name, chart in FACING_RANGES.items():
        violations += _check_freq_sums(name, chart)
    for name, chart in VS_3BET_RANGES.items():
        violations += _check_freq_sums(name, chart)

    # Pairing + support + sanity band, per opener that BB defends against.
    for scenario, chart in FACING_RANGES.items():
        opener = scenario.partition("_vs_")[2]
        if opener not in RFI_BY_POS:
            violations.append(f"{scenario}: unknown opener {opener}")
            continue
        has_3bet = any(f.get("3B", 0) > 0 for f in chart.values())
        partner = f"{opener}_vs_BB_3bet"
        if has_3bet and partner not in VS_3BET_RANGES:
            violations.append(
                f"{scenario} has a 3bet line but no {partner} response chart"
            )

    for name, chart in VS_3BET_RANGES.items():
        opener = name.partition("_vs_")[0]
        if opener not in RFI_BY_POS:
            violations.append(f"{name}: unknown opener {opener}")
            continue
        if f"BB_vs_{opener}" not in FACING_RANGES:
            violations.append(f"{name} has no paired BB_vs_{opener} defend chart")
        violations += _check_vs3bet_support(opener, chart)
        pct = _continue_pct_vs_3bet(opener, chart)
        if not 0.30 <= pct <= 0.75:
            violations.append(
                f"{name}: continue frequency vs 3bet is {pct:.1%}, "
                f"outside the [30%, 75%] sanity band"
            )

    return violations
