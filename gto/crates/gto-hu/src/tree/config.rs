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
    /// First raise = `factor` × facing total (or jam when it reaches the
    /// stack); every re-raise is jam-only. Matches the spec §6 SRP flop
    /// row "vs bet: raise 3x-or-jam / vs raise: fold, call, jam" at deep
    /// SPR, where plain `ToFactorOrJam` would still produce a 3x re-raise.
    ToFactorThenJam(f64),
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
    /// SRP turn per spec §6: check, b50, b100 / vs bet: fold, call,
    /// raise 3x-or-jam / vs raise: fold, call, jam (the second 3x raise
    /// reaches the stack at normal SPRs and becomes a jam).
    pub fn srp_turn() -> Self {
        StreetConfig {
            bet_pcts: vec![50, 100],
            allow_allin_bet: false,
            raise: RaiseRule::ToFactorOrJam(3.0),
            max_raises: 2,
        }
    }

    /// SRP flop per spec §6: check, b33, b75 / vs bet: fold, call,
    /// raise 3x-or-jam / vs raise: fold, call, jam.
    pub fn srp_flop() -> Self {
        StreetConfig {
            bet_pcts: vec![33, 75],
            allow_allin_bet: false,
            raise: RaiseRule::ToFactorThenJam(3.0),
            max_raises: 2,
        }
    }

    /// 3BP flop per spec §6: check, b25, b50 / vs bet: fold, call,
    /// raise-jam.
    pub fn threebet_flop() -> Self {
        StreetConfig {
            bet_pcts: vec![25, 50],
            allow_allin_bet: false,
            raise: RaiseRule::JamOnly,
            max_raises: 1,
        }
    }

    /// 3BP turn per spec §6: check, b50, b100, allin / vs bet: fold,
    /// call, jam.
    pub fn threebet_turn() -> Self {
        StreetConfig {
            bet_pcts: vec![50, 100],
            allow_allin_bet: true,
            raise: RaiseRule::JamOnly,
            max_raises: 1,
        }
    }

    /// 3BP river per spec §6: check, b75, allin / vs bet: fold, call.
    pub fn threebet_river() -> Self {
        StreetConfig {
            bet_pcts: vec![75],
            allow_allin_bet: true,
            raise: RaiseRule::None,
            max_raises: 0,
        }
    }

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
        if let RaiseRule::ToFactorOrJam(f) | RaiseRule::ToFactorThenJam(f) = self.raise {
            assert!(
                f >= 2.0,
                "raise factor {f} below 2.0 builds sub-min-raise sizes"
            );
        }
        for &pct in &self.bet_pcts {
            assert!(pct > 0, "bet_pcts must be positive (got 0)");
        }
    }
}
