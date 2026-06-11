//! Rake model: chips removed from a won pot at terminal payout.
//! Amounts are centi-bb (`BB = 100`); rake is floored to the centi-bb grid
//! so payoffs stay integral. Applied in SOLVER space at terminal evaluation —
//! `terminal.rs` payoffs stay pure zero-sum (its asserts are untouched).

use super::street::Street;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RakeModel {
    /// Fraction of the pot taken (e.g. 0.05).
    pub pct: f64,
    /// Cap in centi-bb.
    pub cap_cbb: i64,
    /// No-flop-no-drop: pots won preflop are not raked.
    pub no_flop_no_drop: bool,
}

impl RakeModel {
    pub const NONE: RakeModel = RakeModel {
        pct: 0.0,
        cap_cbb: 0,
        no_flop_no_drop: true,
    };

    /// Online-site preset: 5% pot, 3bb cap, no flop no drop.
    pub fn site() -> Self {
        RakeModel { pct: 0.05, cap_cbb: 300, no_flop_no_drop: true }
    }

    /// Live preset: 10% pot, 5bb cap, dropped on every pot.
    pub fn live() -> Self {
        RakeModel { pct: 0.10, cap_cbb: 500, no_flop_no_drop: false }
    }

    pub fn is_none(&self) -> bool {
        self.pct == 0.0
    }

    /// Rake (centi-bb) taken from a pot won with the hand ending on `street`.
    pub fn rake_cbb(&self, pot: i64, street: Street) -> i64 {
        if self.pct == 0.0 {
            return 0;
        }
        if self.no_flop_no_drop && street == Street::Preflop {
            return 0;
        }
        ((pot as f64 * self.pct) as i64).min(self.cap_cbb)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn none_takes_nothing() {
        assert_eq!(RakeModel::NONE.rake_cbb(2000, Street::River), 0);
        assert!(RakeModel::NONE.is_none());
    }

    #[test]
    fn site_takes_5pct_capped_at_3bb() {
        let r = RakeModel::site();
        // 20bb pot -> 1bb rake (under the cap)
        assert_eq!(r.rake_cbb(2000, Street::River), 100);
        // 100bb pot -> 5bb uncapped, capped to 3bb
        assert_eq!(r.rake_cbb(10_000, Street::River), 300);
    }

    #[test]
    fn site_nfnd_skips_preflop_pots() {
        assert_eq!(RakeModel::site().rake_cbb(2000, Street::Preflop), 0);
        // live drops every pot
        assert_eq!(RakeModel::live().rake_cbb(2000, Street::Preflop), 200);
    }

    #[test]
    fn rake_floors_to_centibb() {
        // 5% of 1010 cbb = 50.5 -> floors to 50
        assert_eq!(RakeModel::site().rake_cbb(1010, Street::River), 50);
    }
}
