//! PIPA accelerometer quantizer (spec §5).
//!
//! Per-axis carry-forward accumulator, truncated toward zero to whole
//! pulses each tick — the LM_Simulator algorithm (`AGC_IMU.tcl:635-653`):
//! velocity integrates the ΔV, and the emitted pulse count is the integer
//! part of `(velocity − PIPA_INCR·count)/PIPA_INCR`, so no ΔV is ever lost.
use eagle_dynamics::constants::PIPA_INCR;
use eagle_dynamics::frames::{Sm, V3};

/// Three-axis PIPA quantizer over the stable-member ΔV.
#[derive(Debug, Default, Clone)]
pub struct Pipa {
    residual: [f64; 3],
}

impl Pipa {
    /// Accumulate this tick's SM-frame ΔV and emit signed pulse counts
    /// (PINC positive / MINC negative), carrying the sub-pulse remainder.
    pub fn step(&mut self, dv_sm: V3<Sm>) -> [i32; 3] {
        let dv = [dv_sm.x, dv_sm.y, dv_sm.z];
        let mut out = [0i32; 3];
        for i in 0..3 {
            self.residual[i] += dv[i];
            let pulses = (self.residual[i] / PIPA_INCR).trunc() as i32;
            self.residual[i] -= pulses as f64 * PIPA_INCR;
            out[i] = pulses;
        }
        out
    }

    pub fn residual_x(&self) -> f64 {
        self.residual[0]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pipa_zero_accumulation_error() {
        let mut p = Pipa::default();
        let mut emitted = [0i64; 3];
        let mut total = 0.0f64;
        for i in 0..10_000 {
            let dv = 0.001 + 0.0001 * (i % 7) as f64; // awkward fractions of PIPA_INCR
            total += dv;
            let out = p.step(V3::new(dv, -dv / 3.0, 0.0));
            for (e, o) in emitted.iter_mut().zip(out) {
                *e += o as i64;
            }
        }
        let err = (emitted[0] as f64 * PIPA_INCR - total).abs();
        assert!(err < PIPA_INCR, "carry lost: {err}");
        assert!(p.residual_x().abs() < PIPA_INCR);
        assert_eq!(emitted[2], 0);
    }
}
