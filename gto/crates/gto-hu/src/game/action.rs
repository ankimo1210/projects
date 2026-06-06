/// Betting actions. All sizes are **committed totals for the current
/// street** (spec requirement), never increments.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Action {
    Fold,
    Check,
    Call,
    /// Open bet to a total of `to` centi-bb on this street.
    Bet { to: i64 },
    /// Raise to a total of `to` centi-bb on this street.
    Raise { to: i64 },
    /// Commit the entire remaining stack (total = `to`).
    AllIn { to: i64 },
}

impl Action {
    /// Human-readable label with bb amounts (e.g. "bet 15.0bb").
    pub fn label(&self) -> String {
        let bb = |v: i64| format!("{:.1}bb", v as f64 / 100.0);
        match self {
            Action::Fold => "fold".into(),
            Action::Check => "check".into(),
            Action::Call => "call".into(),
            Action::Bet { to } => format!("bet {}", bb(*to)),
            Action::Raise { to } => format!("raise {}", bb(*to)),
            Action::AllIn { to } => format!("allin {}", bb(*to)),
        }
    }
}
