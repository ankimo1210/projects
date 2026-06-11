"""M1a: custom ranges / bet sizes / rake on the gto_py HU bindings."""

import pytest

try:
    import gto_py

    HAS = hasattr(gto_py, "solve_hu_river")
except ImportError:
    HAS = False

pytestmark = pytest.mark.skipif(not HAS, reason="gto_py not built in this venv")

BOARD5 = ["Ah", "Kd", "7s", "2c", "9h"]
NUM_COMBOS = 1326


def _combo_index(a: int, b: int) -> int:
    lo, hi = (a, b) if a < b else (b, a)
    return lo * (103 - lo) // 2 + hi - lo - 1


def _card(s: str) -> int:
    return "23456789TJQKA".index(s[0]) * 4 + "cdhs".index(s[1])


def test_baseline_signature_still_works():
    r = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 300)
    assert {"strategy", "exploitability", "br_sb", "br_bb", "combos"} <= set(r)
    # new outputs present
    assert {"nashconv", "br_gain_sb", "br_gain_bb", "equity_sb", "equity_bb", "game_value_bb"} <= set(r)
    assert r["equity_sb"] + r["equity_bb"] == pytest.approx(1.0)
    # unraked: nashconv == br_sb + br_bb exactly
    assert r["nashconv"] == r["br_sb"] + r["br_bb"]
    assert all("ev" in c for c in r["combos"])


def test_custom_oop_range_filters_combo_export():
    # OOP holds only QQ (6 combos, none blocked by this board).
    w = [0.0] * NUM_COMBOS
    qq = []
    q_cards = [_card("Q" + s) for s in "cdhs"]
    for i, a in enumerate(q_cards):
        for b in q_cards[i + 1:]:
            qq.append(_combo_index(a, b))
    for i in qq:
        w[i] = 1.0
    r = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 300, None, w)
    # Combo export is the ROOT ACTOR's (OOP) range -> exactly the QQ combos.
    got = {(c["card_a"], c["card_b"]) for c in r["combos"]}
    assert len(got) == 6
    assert all(a[0] == "Q" and b[0] == "Q" for a, b in got)


def test_invalid_ranges_rejected():
    with pytest.raises(ValueError):
        gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 100, [1.0] * 10, None)
    blocked = [0.0] * NUM_COMBOS
    blocked[_combo_index(_card("Ah"), _card("Kd"))] = 1.0  # both on board
    with pytest.raises(ValueError):
        gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 100, blocked, None)


def test_custom_bet_sizes_change_action_set():
    base = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 200)
    custom = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 200, None, None, [50], 0)
    assert base["actions"] != custom["actions"]
    # bet_pcts=[50] -> a single 50%-pot bet = 10bb of the 20bb pot; the action
    # labels carry the resulting bb amount, and this size isn't in the default set.
    assert any("10.0bb" in a for a in custom["actions"])
    assert not any("10.0bb" in a for a in base["actions"])


def test_rake_reduces_total_value():
    raked = gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 500, None, None, None, None, None, 0.05, 3.0)
    total = raked["game_value_sb"] + raked["game_value_bb"]
    assert total < 0.0
    # raked nashconv uses per-player gains, still ~0 at convergence
    assert raked["nashconv"] == pytest.approx(
        raked["br_gain_sb"] + raked["br_gain_bb"]
    )


def test_bad_rake_rejected():
    with pytest.raises(ValueError):
        gto_py.solve_hu_river(BOARD5, 20.0, 90.0, 100, None, None, None, None, None, 0.9)
