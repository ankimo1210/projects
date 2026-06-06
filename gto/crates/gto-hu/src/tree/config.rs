/// Response rule when facing a bet.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum RaiseRule {
    /// No raise allowed (fold/call only).
    None,
    /// Raise = jam only (river spec: "raise_jam").
    JamOnly,
    /// Raise to `factor` × the facing total; becomes a jam when the result
    /// reaches the stack. (Flop/turn "raise_3x_or_jam"; used from Phase 4.)
    /// The factor must be ≥ 2.0 — anything lower produces raises below the
    /// NLHE min-raise increment. Validated by `StreetConfig::validate`.
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

    /// Panics on configs that would build illegal or degenerate trees.
    /// Called by the tree builder before expansion.
    pub fn validate(&self) {
        if let RaiseRule::ToFactorOrJam(f) = self.raise {
            assert!(
                f >= 2.0,
                "ToFactorOrJam factor {f} below 2.0 builds sub-min-raise sizes"
            );
        }
        for &pct in &self.bet_pcts {
            assert!(pct > 0, "bet_pcts must be positive (got 0)");
        }
    }
}
