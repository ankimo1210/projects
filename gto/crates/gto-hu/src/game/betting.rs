use super::action::Action;
use super::street::Street;

/// 1 big blind in internal chip units (centi-bb).
pub const BB: i64 = 100;
/// Player 0: SB / Button — acts first preflop, last postflop (IP).
pub const PLAYER_SB: u8 = 0;
/// Player 1: BB — acts last preflop, first postflop (OOP).
pub const PLAYER_BB: u8 = 1;

/// Pure betting state. `apply` returns a new state; legality is enforced
/// with assertions (the tree builder only generates legal actions).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BettingState {
    pub street: Street,
    pub to_act: u8,
    /// Remaining stacks.
    pub stacks: [i64; 2],
    /// Committed on the current street (totals, not increments).
    pub street_committed: [i64; 2],
    /// Total committed this hand (blinds + all streets). pot() derives from it.
    pub contrib: [i64; 2],
    pub raises_this_street: u8,
    /// Number of actions taken this street (for street-close detection).
    pub actions_this_street: u8,
    /// Set when the street's betting is finished (call, or both checked).
    closed: bool,
}

impl BettingState {
    /// Symmetric street subgame root: pot carried in, OOP (BB) to act.
    /// Generalizes `river_root` to any postflop street.
    pub fn street_root(street: Street, pot: i64, stack: i64) -> Self {
        assert!(
            pot > 0 && pot % 2 == 0,
            "carried pot must be positive and even"
        );
        assert!(stack > 0, "stack must be positive");
        BettingState {
            street,
            to_act: PLAYER_BB,
            stacks: [stack; 2],
            street_committed: [0; 2],
            contrib: [pot / 2; 2],
            raises_this_street: 0,
            actions_this_street: 0,
            closed: false,
        }
    }

    /// River subgame root: symmetric pot carried in, OOP (BB) to act.
    pub fn river_root(pot: i64, stack: i64) -> Self {
        Self::street_root(Street::River, pot, stack)
    }

    pub fn pot(&self) -> i64 {
        self.contrib[0] + self.contrib[1]
    }

    pub fn facing_bet(&self) -> bool {
        let me = self.to_act as usize;
        self.street_committed[1 - me] > self.street_committed[me]
    }

    /// Chips needed to call (capped by own stack).
    /// Returns 0 when not facing a bet — callers should gate on `facing_bet()`.
    pub fn call_amount(&self) -> i64 {
        let me = self.to_act as usize;
        (self.street_committed[1 - me] - self.street_committed[me]).min(self.stacks[me])
    }

    pub fn street_closed(&self) -> bool {
        self.closed
    }

    pub fn is_all_in(&self, p: u8) -> bool {
        self.stacks[p as usize] == 0
    }

    /// Move a closed (non-fold) street to the next one: betting counters
    /// reset, OOP to act, chips carried over.
    pub fn advance_street(&self) -> BettingState {
        assert!(self.closed, "cannot advance an open street");
        assert_eq!(
            self.contrib[0], self.contrib[1],
            "advance_street requires matched contributions (no fold)"
        );
        let next = self.street.next().expect("no street after river");
        BettingState {
            street: next,
            to_act: PLAYER_BB,
            stacks: self.stacks,
            street_committed: [0; 2],
            contrib: self.contrib,
            raises_this_street: 0,
            actions_this_street: 0,
            closed: false,
        }
    }

    /// Apply an action, returning the successor state.
    /// Fold does not change chips — terminal payoff handles the pot.
    pub fn apply(&self, action: Action) -> BettingState {
        assert!(!self.closed, "street already closed");
        let me = self.to_act as usize;
        let opp = 1 - me;
        let mut s = *self;
        s.actions_this_street += 1;
        match action {
            Action::Fold => {
                assert!(self.facing_bet(), "fold only legal when facing a bet");
                s.closed = true;
            }
            Action::Check => {
                assert!(!self.facing_bet(), "check illegal when facing a bet");
                // Both players acted without a bet → street closes.
                if s.actions_this_street >= 2 {
                    s.closed = true;
                }
            }
            Action::Call => {
                assert!(self.facing_bet(), "call only legal when facing a bet");
                let amt = self.call_amount();
                s.stacks[me] -= amt;
                s.street_committed[me] += amt;
                s.contrib[me] += amt;
                s.closed = true;
            }
            Action::Bet { to } | Action::Raise { to } | Action::AllIn { to } => {
                let add = to - self.street_committed[me];
                assert!(add > 0, "size must exceed current commitment");
                assert!(add <= self.stacks[me], "cannot bet more than stack");
                assert!(
                    to > self.street_committed[opp] || add == self.stacks[me],
                    "must exceed facing bet unless all-in"
                );
                if matches!(action, Action::AllIn { .. }) {
                    assert_eq!(
                        add, self.stacks[me],
                        "AllIn must commit the entire remaining stack"
                    );
                }
                if self.facing_bet() {
                    s.raises_this_street += 1;
                }
                s.stacks[me] -= add;
                s.street_committed[me] = to;
                s.contrib[me] += add;
            }
        }
        s.to_act = opp as u8;
        s
    }
}
