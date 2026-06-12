"""M2 chart data: consistency validator + chart-derived range presets."""

import pytest
from gto.library.chart_ranges import (
    CHART_OPENERS,
    bb_3bet_weights,
    chart_ranges,
    opener_call_vs_3bet_weights,
)
from gto.library.range_notation import parse_range_notation
from gto.trainer.chart_validator import bb_3bet_pct, validate_all
from gto.trainer.preflop_data import (
    FACING_RANGES,
    RFI_BY_POS,
    VS_3BET_RANGES,
)


def test_shipped_charts_have_no_violations():
    assert validate_all() == []


def test_all_eight_m2_charts_registered():
    # 3 new BB defends (UTG/HJ/SB) + the 2 existing = 5 defend charts
    assert {"BB_vs_UTG", "BB_vs_HJ", "BB_vs_CO", "BB_vs_BTN", "BB_vs_SB"} <= set(
        FACING_RANGES
    )
    # 5 opener-vs-3bet responses
    assert {f"{o}_vs_BB_3bet" for o in CHART_OPENERS} == set(VS_3BET_RANGES)


def test_anchor_hands():
    # BB always 3bets AA, always folds 72o to any open.
    for scenario in ("BB_vs_UTG", "BB_vs_HJ", "BB_vs_SB"):
        assert FACING_RANGES[scenario]["AA"]["3B"] == 100
        assert FACING_RANGES[scenario]["72o"]["F"] == 100
    # Openers never fold AA to a 3bet; never continue 72o.
    for name, chart in VS_3BET_RANGES.items():
        assert chart["AA"]["F"] == 0, name
        assert chart["72o"]["4B"] + chart["72o"]["C"] == 0, name


def test_positional_monotonicity():
    # BB 3bets more vs later (wider) opens: UTG < CO < BTN.
    assert bb_3bet_pct("BB_vs_UTG") < bb_3bet_pct("BB_vs_CO") < bb_3bet_pct("BB_vs_BTN")


def test_vs3bet_continue_requires_open():
    # The conditional 3bet-pot range never contains a hand the opener folds pre.
    for opener in CHART_OPENERS:
        rfi = RFI_BY_POS[opener]
        for hand, w in opener_call_vs_3bet_weights(opener).items():
            if w > 0:
                assert rfi[hand].get("R", 0) > 0, (opener, hand)


@pytest.mark.parametrize("opener", CHART_OPENERS)
@pytest.mark.parametrize("pot_type", ["srp", "3bet"])
def test_chart_notations_parse_to_live_ranges(opener, pot_type):
    r = chart_ranges(opener, pot_type)
    for side in ("ip", "oop"):
        w = parse_range_notation(r[side])
        assert w.sum() > 0
        assert w.max() <= 1.0
    # SB opener is OOP postflop in 6max; everyone else is IP.
    assert r["opener_is_ip"] == (opener != "SB")


def test_3bet_pot_bb_range_is_the_3bet_portion():
    w = bb_3bet_weights("BTN")
    assert w["AA"] == 1.0
    assert w["QQ"] == pytest.approx(0.7)   # QQ 3bets 70 vs BTN
    assert w["72o"] == 0.0


def test_chart_ranges_rejects_unknown():
    with pytest.raises(ValueError):
        chart_ranges("BB", "srp")
    with pytest.raises(ValueError):
        chart_ranges("BTN", "4bet")
