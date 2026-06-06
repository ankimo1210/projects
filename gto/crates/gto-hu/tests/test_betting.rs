use gto_hu::game::{Action, BettingState, BB, PLAYER_BB, PLAYER_SB};

#[test]
fn river_root_state_is_exact() {
    let s = BettingState::river_root(20 * BB, 90 * BB);
    assert_eq!(s.to_act, PLAYER_BB, "OOP (BB) acts first postflop");
    assert_eq!(s.pot(), 20 * BB);
    assert_eq!(s.contrib, [10 * BB, 10 * BB]);
    assert_eq!(s.stacks, [90 * BB, 90 * BB]);
    assert!(!s.facing_bet());
}

#[test]
fn bet_call_conserves_chips() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let total0 = s0.pot() + s0.stacks[0] + s0.stacks[1];
    let s1 = s0.apply(Action::Bet { to: 15 * BB }); // BB bets 15bb (75% pot)
    let s2 = s1.apply(Action::Call);
    let total2 = s2.pot() + s2.stacks[0] + s2.stacks[1];
    assert_eq!(total0, total2, "chips must be conserved");
    assert_eq!(s2.pot(), 50 * BB);
    assert_eq!(s2.street_committed, [15 * BB, 15 * BB]);
    assert_eq!(s2.stacks, [75 * BB, 75 * BB]);
}

#[test]
fn call_is_capped_by_stack() {
    // Short stack: pot 20, stacks 10. BB jams 10bb total, SB calls all-in.
    let s0 = BettingState::river_root(20 * BB, 10 * BB);
    let s1 = s0.apply(Action::AllIn { to: 10 * BB });
    assert_eq!(s1.stacks[PLAYER_BB as usize], 0);
    let s2 = s1.apply(Action::Call);
    assert_eq!(s2.stacks[PLAYER_SB as usize], 0);
    assert_eq!(s2.pot(), 40 * BB);
}

#[test]
fn facing_bet_detection_and_call_amount() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let s1 = s0.apply(Action::Bet { to: 30 * BB }); // 150% pot
    assert!(s1.facing_bet());
    assert_eq!(s1.call_amount(), 30 * BB);
    assert_eq!(s1.to_act, PLAYER_SB);
}

#[test]
fn check_check_tracks_street_close() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let s1 = s0.apply(Action::Check);
    assert!(!s1.street_closed());
    let s2 = s1.apply(Action::Check);
    assert!(s2.street_closed());
}

#[test]
fn call_closes_street() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let s2 = s0.apply(Action::Bet { to: 15 * BB }).apply(Action::Call);
    assert!(s2.street_closed());
}
