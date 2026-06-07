"""Tests for the PokerStars hand history parser (gto.review)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from gto.review import parse_hand, parse_hands
from gto.review.models import ParsedHand

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture
def fold_hand() -> ParsedHand:
    return parse_hand(load("ps_6max_preflop_fold.txt"))


@pytest.fixture
def showdown_hand() -> ParsedHand:
    return parse_hand(load("ps_zoom_multistreet_showdown.txt"))


@pytest.fixture
def allin_hand() -> ParsedHand:
    return parse_hand(load("ps_3handed_allin_uncalled.txt"))


# ---------------------------------------------------------------------------
# Hand 1: simple 6-max hand folded preflop
# ---------------------------------------------------------------------------


def test_header_and_table(fold_hand: ParsedHand) -> None:
    assert fold_hand.hand_id == "243598731121"
    assert fold_hand.stakes.small_blind == pytest.approx(0.50)
    assert fold_hand.stakes.big_blind == pytest.approx(1.00)
    assert fold_hand.stakes.currency == "USD"
    assert fold_hand.played_at == datetime(2024, 1, 15, 20, 31, 7)
    assert fold_hand.timezone == "ET"
    assert fold_hand.table_name == "Aenna III"
    assert fold_hand.max_players == 6
    assert fold_hand.button_seat == 3
    assert fold_hand.zoom is False


def test_player_extraction(fold_hand: ParsedHand) -> None:
    assert len(fold_hand.players) == 6
    assert [p.seat for p in fold_hand.players] == [1, 2, 3, 4, 5, 6]
    assert fold_hand.players[0].name == "Hero"
    assert fold_hand.players[1].name == "bob_the_fish"
    assert fold_hand.players[1].stack == pytest.approx(85.50)
    assert all(not p.sitting_out for p in fold_hand.players)


def test_hero_cards(fold_hand: ParsedHand) -> None:
    assert fold_hand.hero_name == "Hero"
    assert fold_hand.hero_cards == ("7h", "2s")


def test_blind_posts(fold_hand: ParsedHand) -> None:
    assert [(p.player, p.blind_type, p.amount) for p in fold_hand.posts] == [
        ("dave42", "small", 0.50),
        ("emma_v", "big", 1.00),
    ]


def test_preflop_fold_actions(fold_hand: ParsedHand) -> None:
    pre = fold_hand.actions["preflop"]
    assert [(a.actor, a.action) for a in pre] == [
        ("frank_tank", "fold"),
        ("Hero", "fold"),
        ("bob_the_fish", "fold"),
        ("carol99", "raise"),
        ("dave42", "fold"),
        ("emma_v", "fold"),
    ]
    open_raise = pre[3]
    assert open_raise.amount == pytest.approx(1.50)
    assert open_raise.raise_to == pytest.approx(2.50)
    assert open_raise.all_in is False
    assert fold_hand.actions["flop"] == []
    assert fold_hand.actions["turn"] == []
    assert fold_hand.actions["river"] == []
    assert fold_hand.board == []
    assert fold_hand.showdown == []


def test_preflop_fold_pot_and_winner(fold_hand: ParsedHand) -> None:
    assert [(u.player, u.amount) for u in fold_hand.uncalled_bets] == [("carol99", 1.50)]
    assert [(w.player, w.amount, w.pot) for w in fold_hand.winners] == [("carol99", 2.50, "pot")]
    assert fold_hand.total_pot == pytest.approx(2.50)
    assert fold_hand.rake == pytest.approx(0.0)


def test_preflop_fold_positions_and_deviation(fold_hand: ParsedHand) -> None:
    assert fold_hand.positions == {
        "dave42": "SB",
        "emma_v": "BB",
        "frank_tank": "UTG",
        "Hero": "HJ",
        "bob_the_fish": "CO",
        "carol99": "BTN",
    }
    dev = fold_hand.preflop_deviation
    assert dev is not None
    assert dev.flag == "ok"
    assert dev.hand == "72o"
    assert dev.spot_type == "RFI"
    assert dev.position == "HJ"
    assert dev.hero_action == "F"
    assert dev.gto_action == "F"
    assert dev.gto_frequencies == {"R": 0, "F": 100}
    assert dev.ev_loss == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Hand 2: Zoom multi-street hand with showdown
# ---------------------------------------------------------------------------


def test_showdown_hand_header(showdown_hand: ParsedHand) -> None:
    assert showdown_hand.zoom is True
    assert showdown_hand.hand_id == "244112233445"
    assert showdown_hand.stakes.small_blind == pytest.approx(0.25)
    assert showdown_hand.stakes.big_blind == pytest.approx(0.50)
    assert showdown_hand.button_seat == 1


def test_showdown_hand_streets(showdown_hand: ParsedHand) -> None:
    assert showdown_hand.hero_cards == ("Ah", "Kd")
    assert showdown_hand.board == ["Kc", "7d", "2c", "5h", "9s"]

    pre = showdown_hand.actions["preflop"]
    assert len(pre) == 6
    btn_open = pre[3]
    assert (btn_open.actor, btn_open.action) == ("villain_btn", "raise")
    assert btn_open.amount == pytest.approx(0.75)
    assert btn_open.raise_to == pytest.approx(1.25)

    flop = showdown_hand.actions["flop"]
    assert [(a.actor, a.action) for a in flop] == [
        ("Hero", "check"),
        ("villain_btn", "bet"),
        ("Hero", "call"),
    ]
    assert flop[1].amount == pytest.approx(1.50)

    turn = showdown_hand.actions["turn"]
    assert len(turn) == 3
    assert turn[1].amount == pytest.approx(3.75)

    river = showdown_hand.actions["river"]
    assert [(a.actor, a.action) for a in river] == [
        ("Hero", "check"),
        ("villain_btn", "check"),
    ]


def test_showdown_results(showdown_hand: ParsedHand) -> None:
    sd = {e.player: e for e in showdown_hand.showdown}
    assert set(sd) == {"Hero", "villain_btn"}
    assert sd["Hero"].cards == ("Ah", "Kd")
    assert sd["Hero"].mucked is False
    assert sd["Hero"].description == "a pair of Kings"
    assert sd["villain_btn"].mucked is True
    # mucked cards recovered from the summary section
    assert sd["villain_btn"].cards == ("Qd", "Jd")

    assert [(w.player, w.amount) for w in showdown_hand.winners] == [("Hero", 12.65)]
    assert showdown_hand.total_pot == pytest.approx(13.25)
    assert showdown_hand.rake == pytest.approx(0.60)


def test_showdown_deviation_tight(showdown_hand: ParsedHand) -> None:
    dev = showdown_hand.preflop_deviation
    assert dev is not None
    assert dev.flag == "tight"
    assert dev.hand == "AKo"
    assert dev.spot_type == "FACING"
    assert dev.position == "BB_vs_BTN"
    assert dev.hero_action == "C"
    assert dev.gto_action == "3B"
    assert dev.gto_frequencies["3B"] == 100
    assert dev.ev_loss > 0


# ---------------------------------------------------------------------------
# Hand 3: all-in with uncalled bet returned, antes, sitting-out player
# ---------------------------------------------------------------------------


def test_allin_hand_players_and_antes(allin_hand: ParsedHand) -> None:
    assert len(allin_hand.players) == 4
    by_name = {p.name: p for p in allin_hand.players}
    assert by_name["tired_tom"].sitting_out is True
    antes = [p for p in allin_hand.posts if p.blind_type == "ante"]
    assert [(p.player, p.amount) for p in antes] == [
        ("shark_ali", 0.50),
        ("rocky_5", 0.50),
        ("Hero", 0.50),
    ]
    # sitting-out player is excluded from position assignment
    assert allin_hand.positions == {"shark_ali": "SB", "rocky_5": "BB", "Hero": "BTN"}


def test_allin_actions_and_uncalled_return(allin_hand: ParsedHand) -> None:
    pre = allin_hand.actions["preflop"]
    assert [(a.actor, a.action) for a in pre] == [
        ("Hero", "raise"),
        ("shark_ali", "call"),
        ("rocky_5", "fold"),
    ]
    shove = pre[0]
    assert shove.all_in is True
    assert shove.raise_to == pytest.approx(249.50)
    call = pre[1]
    assert call.all_in is True
    assert call.amount == pytest.approx(78.50)

    assert [(u.player, u.amount) for u in allin_hand.uncalled_bets] == [("Hero", 170.0)]
    assert allin_hand.board == ["9c", "6h", "3d", "Qs", "2h"]

    sd = {e.player: e for e in allin_hand.showdown}
    assert sd["Hero"].cards == ("As", "Ad")
    assert sd["shark_ali"].cards == ("Kh", "Ks")

    assert [(w.player, w.amount) for w in allin_hand.winners] == [("Hero", 160.0)]
    assert allin_hand.total_pot == pytest.approx(162.50)
    assert allin_hand.rake == pytest.approx(2.50)


def test_allin_deviation_ok(allin_hand: ParsedHand) -> None:
    dev = allin_hand.preflop_deviation
    assert dev is not None
    assert dev.flag == "ok"
    assert dev.hand == "AA"
    assert dev.spot_type == "RFI"
    assert dev.position == "BTN"
    assert dev.hero_action == "R"
    assert dev.gto_action == "R"


# ---------------------------------------------------------------------------
# Multiple hands / malformed input
# ---------------------------------------------------------------------------


def test_parse_multiple_hands() -> None:
    text = "\n\n".join(
        load(n)
        for n in (
            "ps_6max_preflop_fold.txt",
            "ps_zoom_multistreet_showdown.txt",
            "ps_3handed_allin_uncalled.txt",
        )
    )
    result = parse_hands(text)
    assert len(result.hands) == 3
    assert result.errors == []
    assert [h.hand_id for h in result.hands] == [
        "243598731121",
        "244112233445",
        "245000111222",
    ]


def test_garbage_input_returns_errors() -> None:
    result = parse_hands("totally not a hand\nfoo bar baz\n")
    assert result.hands == []
    assert len(result.errors) == 1
    assert result.errors[0].message


def test_mixed_good_and_garbage() -> None:
    text = (
        load("ps_6max_preflop_fold.txt")
        + "\n\nPokerStars Hand #999: garbage that should not parse\njunk line\n"
    )
    result = parse_hands(text)
    assert len(result.hands) == 1
    assert result.hands[0].hand_id == "243598731121"
    assert len(result.errors) == 1
    assert "999" in result.errors[0].snippet


def test_empty_input() -> None:
    result = parse_hands("")
    assert result.hands == []
    assert result.errors == []


def test_deviation_missing_data_for_uncovered_scenario() -> None:
    # BB facing a UTG open: no facing data exists for BB_vs_UTG.
    text = """\
PokerStars Hand #246000000001:  Hold'em No Limit ($0.50/$1.00 USD) - 2024/04/01 11:00:00 ET
Table 'Mizar' 6-max Seat #3 is the button
Seat 1: hj_p ($100.00 in chips)
Seat 2: co_p ($100.00 in chips)
Seat 3: btn_p ($100.00 in chips)
Seat 4: sb_p ($100.00 in chips)
Seat 5: Hero ($100.00 in chips)
Seat 6: utg_open ($100.00 in chips)
sb_p: posts small blind $0.50
Hero: posts big blind $1
*** HOLE CARDS ***
Dealt to Hero [Qh Qs]
utg_open: raises $2 to $3
hj_p: folds
co_p: folds
btn_p: folds
sb_p: folds
Hero: calls $2
*** FLOP *** [2c 7d Jh]
Hero: checks
utg_open: bets $2
Hero: folds
Uncalled bet ($2) returned to utg_open
utg_open collected $6.20 from pot
*** SUMMARY ***
Total pot $6.50 | Rake $0.30
Board [2c 7d Jh]
"""
    hand = parse_hand(text)
    assert hand.positions["utg_open"] == "UTG"
    dev = hand.preflop_deviation
    assert dev is not None
    assert dev.flag == "missing_data"
    assert dev.reason


# ---------------------------------------------------------------------------
# Dead small blind (regression: positions used to shift one seat)
# ---------------------------------------------------------------------------

_DEAD_SB_HAND = """\
PokerStars Hand #247000000001:  Hold'em No Limit ($0.50/$1.00 USD) - 2024/05/02 19:05:11 ET
Table 'Deneb V' 6-max Seat #6 is the button
Seat 1: bb_player ($100.00 in chips)
Seat 2: Hero ($100.00 in chips)
Seat 3: mp_p ($100.00 in chips)
Seat 4: hj_p ($100.00 in chips)
Seat 5: co_p ($100.00 in chips)
Seat 6: btn_p ($100.00 in chips)
bb_player: posts big blind $1
*** HOLE CARDS ***
Dealt to Hero [Ah Kc]
Hero: raises $1.50 to $2.50
mp_p: folds
hj_p: folds
co_p: folds
btn_p: folds
bb_player: folds
Uncalled bet ($1.50) returned to Hero
Hero collected $2 from pot
*** SUMMARY ***
Total pot $2 | Rake $0
"""


def test_dead_small_blind_anchors_positions_on_bb() -> None:
    # No "posts small blind" line: the first seat after the button is the BB,
    # not the SB, and no seat gets the SB label.
    hand = parse_hand(_DEAD_SB_HAND)
    assert hand.positions == {
        "bb_player": "BB",
        "Hero": "UTG",
        "mp_p": "UTG+1",
        "hj_p": "HJ",
        "co_p": "CO",
        "btn_p": "BTN",
    }


def test_dead_small_blind_deviation_uses_true_position() -> None:
    # Hero (true UTG) opening AKo used to be judged as BB -> missing_data.
    dev = parse_hand(_DEAD_SB_HAND).preflop_deviation
    assert dev is not None
    assert dev.flag == "ok"
    assert dev.hand == "AKo"
    assert dev.spot_type == "RFI"
    assert dev.position == "UTG"
    assert dev.hero_action == "R"
    assert dev.gto_action == "R"


def test_returning_player_small_and_big_post_is_not_sb() -> None:
    # A returning player's "small & big blinds" post must not anchor the
    # rotation; the big-blind poster does.
    text = """\
PokerStars Hand #247000000002:  Hold'em No Limit ($0.50/$1.00 USD) - 2024/05/02 19:08:45 ET
Table 'Deneb V' 6-max Seat #5 is the button
Seat 1: bb_player ($100.00 in chips)
Seat 2: Hero ($100.00 in chips)
Seat 3: returner ($100.00 in chips)
Seat 4: co_p ($100.00 in chips)
Seat 5: btn_p ($100.00 in chips)
bb_player: posts big blind $1
returner: posts small & big blinds $1.50
*** HOLE CARDS ***
Dealt to Hero [7h 2s]
Hero: folds
returner: checks
co_p: folds
btn_p: folds
bb_player: checks
*** FLOP *** [2c 7d Jh]
bb_player: checks
returner: checks
*** TURN *** [2c 7d Jh] [5s]
bb_player: checks
returner: checks
*** RIVER *** [2c 7d Jh 5s] [9d]
bb_player: bets $1
returner: folds
Uncalled bet ($1) returned to bb_player
bb_player collected $2.38 from pot
*** SUMMARY ***
Total pot $2.50 | Rake $0.12
Board [2c 7d Jh 5s 9d]
"""
    hand = parse_hand(text)
    assert [(p.player, p.blind_type) for p in hand.posts] == [
        ("bb_player", "big"),
        ("returner", "small_and_big"),
    ]
    assert hand.positions == {
        "bb_player": "BB",
        "Hero": "UTG",
        "returner": "HJ",
        "co_p": "CO",
        "btn_p": "BTN",
    }


# ---------------------------------------------------------------------------
# Non-USD currencies (regression: EUR hands failed with "unrecognized header")
# ---------------------------------------------------------------------------

_EUR_HAND = """\
PokerStars Hand #248000000001:  Hold'em No Limit (€0.50/€1.00 EUR) - 2024/05/03 14:22:09 CET
Table 'Castor IV' 6-max Seat #3 is the button
Seat 1: alice (€100.00 in chips)
Seat 2: bruno (€85.50 in chips)
Seat 3: Hero (€120.00 in chips)
Seat 4: dieter (€100.00 in chips)
Seat 5: elena (€64.20 in chips)
dieter: posts small blind €0.50
elena: posts big blind €1
*** HOLE CARDS ***
Dealt to Hero [As Ks]
alice: folds
bruno: folds
Hero: raises €1.50 to €2.50
dieter: folds
elena: calls €1.50
*** FLOP *** [Kh 8c 2d]
elena: checks
Hero: bets €3
elena: folds
Uncalled bet (€3) returned to Hero
Hero collected €5.25 from pot
*** SUMMARY ***
Total pot €5.50 | Rake €0.25
Board [Kh 8c 2d]
"""


def test_eur_hand_parses() -> None:
    hand = parse_hand(_EUR_HAND)
    assert hand.stakes.currency == "EUR"
    assert hand.stakes.small_blind == pytest.approx(0.50)
    assert hand.stakes.big_blind == pytest.approx(1.00)
    assert {p.name: p.stack for p in hand.players}["elena"] == pytest.approx(64.20)
    assert [(p.player, p.amount) for p in hand.posts] == [("dieter", 0.50), ("elena", 1.00)]
    open_raise = hand.actions["preflop"][2]
    assert open_raise.amount == pytest.approx(1.50)
    assert open_raise.raise_to == pytest.approx(2.50)
    assert [(u.player, u.amount) for u in hand.uncalled_bets] == [("Hero", 3.0)]
    assert [(w.player, w.amount) for w in hand.winners] == [("Hero", 5.25)]
    assert hand.total_pot == pytest.approx(5.50)
    assert hand.rake == pytest.approx(0.25)
    dev = hand.preflop_deviation
    assert dev is not None
    assert dev.flag == "ok"
    assert dev.hand == "AKs"


def test_currency_inferred_from_symbol_without_code() -> None:
    text = _EUR_HAND.replace("(€0.50/€1.00 EUR)", "(€0.50/€1.00)")
    assert parse_hand(text).stakes.currency == "EUR"
