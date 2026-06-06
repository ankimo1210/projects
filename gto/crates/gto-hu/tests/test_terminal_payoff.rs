use gto_hu::game::{terminal, Action, BettingState, BB, PLAYER_BB, PLAYER_SB};

#[test]
fn fold_returns_uncalled_bet() {
    // Pot 20bb, BB bets 15bb, SB folds. BB must win exactly 10bb
    // (SB's half of the carried pot), NOT half of the 35bb pot.
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 15 * BB });
    let p = terminal::fold_payoffs(&s, PLAYER_BB);
    assert_eq!(p[PLAYER_BB as usize], 10 * BB);
    assert_eq!(p[PLAYER_SB as usize], -10 * BB);
}

#[test]
fn fold_payoffs_are_zero_sum() {
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 30 * BB });
    let p = terminal::fold_payoffs(&s, PLAYER_BB);
    assert_eq!(p[0] + p[1], 0);
}

#[test]
fn showdown_winner_takes_opponent_contribution() {
    // Bet 15bb called: each contributed 25bb total. Winner nets +25bb.
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 15 * BB })
        .apply(Action::Call);
    let p = terminal::showdown_payoffs(&s, Some(PLAYER_SB));
    assert_eq!(p[PLAYER_SB as usize], 25 * BB);
    assert_eq!(p[PLAYER_BB as usize], -25 * BB);
}

#[test]
fn showdown_tie_splits_to_zero() {
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 15 * BB })
        .apply(Action::Call);
    let p = terminal::showdown_payoffs(&s, None);
    assert_eq!(p, [0, 0]);
}
