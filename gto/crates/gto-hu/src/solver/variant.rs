/// CFR family member. References: Zinkevich et al. 2007 (vanilla CFR),
/// Tammelin 2014 (CFR+), Brown & Sandholm 2019 (DCFR).
///
/// # Discount semantics
///
/// Discount-then-add per iteration: stored sums are discounted by the factor
/// for iteration t on the infoset's **first visit** in t, then deltas
/// accumulate undiscounted for the remainder of the iteration.  This is the
/// standard lazy-discount DCFR implementation; it differs from
/// add-then-discount formulations by one delta term, which is asymptotically
/// irrelevant.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CfrVariant {
    Vanilla,
    /// Regrets clipped at zero after each update. Average-strategy
    /// accumulation starts after `avg_delay` iterations; with
    /// `linear_weighting` iteration t contributes weight (t − avg_delay).
    CfrPlus { avg_delay: u32, linear_weighting: bool },
    /// Discounted CFR: positive regrets × t^α/(t^α+1), negative regrets ×
    /// t^β/(t^β+1), strategy contributions × (t/(t+1))^γ.
    Dcfr { alpha: f64, beta: f64, gamma: f64 },
}

impl CfrVariant {
    pub fn dcfr_default() -> Self {
        CfrVariant::Dcfr { alpha: 1.5, beta: 0.0, gamma: 2.0 }
    }

    pub fn cfr_plus_default() -> Self {
        CfrVariant::CfrPlus { avg_delay: 0, linear_weighting: true }
    }

    /// Per-iteration discount factor for a stored cumulative regret
    /// (applied lazily on the infoset's first visit in iteration t).
    /// DCFR: t^α/(t^α+1) for positive, t^β/(t^β+1) for negative regrets.
    /// Vanilla/CFR+: no discounting (1.0).
    pub fn regret_discount(&self, old: f64, t: u32) -> f64 {
        match *self {
            CfrVariant::Vanilla | CfrVariant::CfrPlus { .. } => 1.0,
            CfrVariant::Dcfr { alpha, beta, .. } => {
                let tf = t as f64;
                let exp = if old >= 0.0 { alpha } else { beta };
                let p = tf.powf(exp);
                p / (p + 1.0)
            }
        }
    }

    /// Accumulate this visit's regret delta (CFR+ clips at zero).
    pub fn accumulate_regret(&self, old: f64, delta: f64) -> f64 {
        match *self {
            CfrVariant::CfrPlus { .. } => (old + delta).max(0.0),
            _ => old + delta,
        }
    }

    /// Multiplier applied to the stored strategy sum at iteration t
    /// (DCFR's γ-discount; 1.0 for other variants).
    pub fn strategy_discount(&self, t: u32) -> f64 {
        match *self {
            CfrVariant::Dcfr { gamma, .. } => {
                let tf = t as f64;
                (tf / (tf + 1.0)).powf(gamma)
            }
            _ => 1.0,
        }
    }

    /// Weight of iteration t's strategy contribution.
    pub fn strategy_weight(&self, t: u32) -> f64 {
        match *self {
            CfrVariant::Vanilla | CfrVariant::Dcfr { .. } => 1.0,
            CfrVariant::CfrPlus { avg_delay, linear_weighting } => {
                if t <= avg_delay {
                    0.0
                } else if linear_weighting {
                    (t - avg_delay) as f64
                } else {
                    1.0
                }
            }
        }
    }
}
