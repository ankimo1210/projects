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
    CfrPlus {
        avg_delay: u32,
        linear_weighting: bool,
    },
    /// Discounted CFR: positive regrets × t^α/(t^α+1), negative regrets ×
    /// t^β/(t^β+1), strategy contributions × (t/(t+1))^γ.
    Dcfr {
        alpha: f64,
        beta: f64,
        gamma: f64,
    },
}

impl CfrVariant {
    pub fn dcfr_default() -> Self {
        CfrVariant::Dcfr {
            alpha: 1.5,
            beta: 0.0,
            gamma: 2.0,
        }
    }

    pub fn cfr_plus_default() -> Self {
        CfrVariant::CfrPlus {
            avg_delay: 0,
            linear_weighting: true,
        }
    }

    /// Per-iteration discount factor for a stored cumulative regret
    /// (applied lazily on the infoset's first visit in iteration t).
    /// DCFR: t^α/(t^α+1) for positive, t^β/(t^β+1) for negative regrets.
    /// Vanilla/CFR+: no discounting (1.0).
    pub fn regret_discount(&self, old: f64, t: u32) -> f64 {
        let (d_pos, d_neg) = self.regret_discounts(t);
        if old >= 0.0 {
            d_pos
        } else {
            d_neg
        }
    }

    /// The two iteration-t regret discount factors `(d_pos, d_neg)` selected
    /// by `regret_discount` via the sign of the stored regret. For a fixed
    /// `t` only these two values exist, so the caller can compute them once
    /// per (node, iteration) and index by sign inside the update loop instead
    /// of calling `powf` per (combo, action). The math is identical to
    /// `regret_discount` (same `powf`, computed once).
    pub fn regret_discounts(&self, t: u32) -> (f64, f64) {
        match *self {
            CfrVariant::Vanilla | CfrVariant::CfrPlus { .. } => (1.0, 1.0),
            CfrVariant::Dcfr { alpha, beta, .. } => {
                let tf = t as f64;
                let disc = |exp: f64| {
                    let p = tf.powf(exp);
                    p / (p + 1.0)
                };
                (disc(alpha), disc(beta))
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

    /// Cumulative strategy-sum discount for iterations skipped between a
    /// slice's last visit `last` (exclusive) and the current iteration `t`
    /// (exclusive of t — the current iteration's own discount is applied
    /// separately). Used by sampled-mode solvers to catch up the lazy
    /// γ-discount over iterations on which the slice was not visited.
    ///
    /// DCFR γ telescopes: ∏_{u=last+1..t-1} (u/(u+1))^γ = ((last+1)/t)^γ.
    /// For `last == t-1` (no gap — every-iteration visits, enumerate mode)
    /// this is the empty product 1.0 exactly, so visited-every-iteration
    /// slices are numerically untouched. Non-DCFR variants never discount,
    /// so this is always exactly 1.0 (preserves CFR+ bit-identity).
    pub fn strategy_catchup(&self, last: u32, t: u32) -> f64 {
        match *self {
            CfrVariant::Dcfr { gamma, .. } if t > last + 1 => {
                ((last + 1) as f64 / t as f64).powf(gamma)
            }
            _ => 1.0,
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
            CfrVariant::CfrPlus {
                avg_delay,
                linear_weighting,
            } => {
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
