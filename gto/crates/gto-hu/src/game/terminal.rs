use super::betting::BettingState;

/// Payoff convention everywhere in gto-hu:
/// `payoff(p) = chips_won(p) − contrib(p)` in centi-bb.
/// Uncalled bets return to the bettor automatically because the winner's
/// own contribution cancels: pot − contrib(w) = contrib(loser).

/// Fold terminal: `winner` takes the pot.
pub fn fold_payoffs(state: &BettingState, winner: u8) -> [i64; 2] {
    let pot = state.pot();
    let w = winner as usize;
    let mut p = [0i64; 2];
    p[w] = pot - state.contrib[w];
    p[1 - w] = -state.contrib[1 - w];
    debug_assert_eq!(p[0] + p[1], 0, "fold payoffs must be zero-sum");
    p
}

/// Showdown: `Some(winner)` or `None` for a chopped pot.
pub fn showdown_payoffs(state: &BettingState, winner: Option<u8>) -> [i64; 2] {
    debug_assert_eq!(
        state.contrib[0], state.contrib[1],
        "contributions must match at showdown"
    );
    match winner {
        Some(w) => fold_payoffs(state, w),
        None => {
            let half = state.pot() / 2;
            [half - state.contrib[0], half - state.contrib[1]]
        }
    }
}
