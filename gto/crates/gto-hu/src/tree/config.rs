/// Response rule when facing a bet.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum RaiseRule {
    /// No raise allowed (fold/call only).
    None,
    /// Raise = jam only (river spec: "raise_jam").
    JamOnly,
    /// Raise to `factor` × the facing total; becomes a jam when the result
    /// reaches the stack. (Flop/turn "raise_3x_or_jam"; used from Phase 4.)
    ToFactorOrJam(f64),
}

/// Action abstraction for one street of one pot type.
#[derive(Debug, Clone)]
pub struct StreetConfig {
    /// Open bet sizes in % of current pot.
    pub bet_pcts: Vec<u32>,
    /// Offer an explicit open jam in addition to bet_pcts.
    pub allow_allin_bet: bool,
    pub raise: RaiseRule,
    pub max_raises: u8,
}

impl StreetConfig {
    /// SRP river per spec: check, bet75, bet150, allin / vs bet: fold,
    /// call, raise-jam / vs raise: fold, call.
    pub fn srp_river() -> Self {
        StreetConfig {
            bet_pcts: vec![75, 150],
            allow_allin_bet: true,
            raise: RaiseRule::JamOnly,
            max_raises: 1,
        }
    }
}
