//! Seeded IMU error models (spec §5). Default is OFF and bit-exact: an
//! all-zero config returns the input untouched without drawing from the
//! RNG, so acceptance runs (errors OFF) are deterministic and RNG-free.
use eagle_dynamics::frames::{Sm, V3};
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;

/// Per-axis IMU error parameters. `Default` (all zeros) means OFF.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct ImuErrorCfg {
    /// Accelerometer bias, m/s² per axis (integrated over dt into ΔV).
    pub accel_bias_mps2: [f64; 3],
    /// Scale-factor error, parts per million per axis.
    pub accel_scale_ppm: [f64; 3],
    /// White-noise standard deviation, m/s² (scaled by √dt into ΔV).
    pub accel_noise_sigma_mps2: f64,
    /// RNG seed (ChaCha8) for reproducible noise sequences.
    pub seed: u64,
}

impl ImuErrorCfg {
    fn is_off(&self) -> bool {
        self.accel_bias_mps2 == [0.0; 3]
            && self.accel_scale_ppm == [0.0; 3]
            && self.accel_noise_sigma_mps2 == 0.0
    }
}

/// Stateful IMU error injector.
pub struct ImuErrors {
    cfg: ImuErrorCfg,
    off: bool,
    rng: ChaCha8Rng,
}

impl ImuErrors {
    pub fn new(cfg: ImuErrorCfg) -> Self {
        let off = cfg.is_off();
        let rng = ChaCha8Rng::seed_from_u64(cfg.seed);
        Self { cfg, off, rng }
    }

    /// Corrupt one tick's stable-member ΔV: bias·dt, scale-factor error,
    /// and √dt-scaled white noise, per axis. OFF short-circuits to identity
    /// without touching the RNG.
    pub fn corrupt(&mut self, dv_sm: V3<Sm>, dt: f64) -> V3<Sm> {
        if self.off {
            return dv_sm;
        }
        let dv = [dv_sm.x, dv_sm.y, dv_sm.z];
        let sigma = self.cfg.accel_noise_sigma_mps2 * dt.sqrt();
        let mut out = [0.0f64; 3];
        for i in 0..3 {
            let scaled = (dv[i] + self.cfg.accel_bias_mps2[i] * dt)
                * (1.0 + self.cfg.accel_scale_ppm[i] * 1e-6);
            let noise = if sigma > 0.0 {
                sigma * self.gaussian()
            } else {
                0.0
            };
            out[i] = scaled + noise;
        }
        V3::new(out[0], out[1], out[2])
    }

    /// Standard-normal sample via Box-Muller (cos branch), from the seeded
    /// ChaCha8 stream.
    fn gaussian(&mut self) -> f64 {
        let u1: f64 = self.rng.gen::<f64>().max(f64::MIN_POSITIVE);
        let u2: f64 = self.rng.gen::<f64>();
        (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn off_config_is_bit_exact_identity() {
        let mut e = ImuErrors::new(ImuErrorCfg::default());
        for k in 0..50 {
            let v = V3::<Sm>::new(0.001 * k as f64, -0.02, 3.5);
            assert_eq!(e.corrupt(v, 0.01), v);
        }
    }

    #[test]
    fn same_seed_same_sequence() {
        let cfg = ImuErrorCfg {
            accel_noise_sigma_mps2: 0.05,
            seed: 42,
            ..Default::default()
        };
        let mut a = ImuErrors::new(cfg.clone());
        let mut b = ImuErrors::new(cfg);
        for _ in 0..100 {
            let va = a.corrupt(V3::new(0.0, 0.0, 0.0), 0.01);
            let vb = b.corrupt(V3::new(0.0, 0.0, 0.0), 0.01);
            assert_eq!(va, vb);
        }
    }

    #[test]
    fn bias_integrates_into_delta_v() {
        let cfg = ImuErrorCfg {
            accel_bias_mps2: [0.01, 0.0, 0.0],
            ..Default::default()
        };
        let mut e = ImuErrors::new(cfg);
        let mut acc = 0.0;
        for _ in 0..1000 {
            acc += e.corrupt(V3::new(0.0, 0.0, 0.0), 0.01).x;
        }
        assert!((acc - 0.1).abs() < 1e-9, "bias sum {acc}");
    }

    #[test]
    fn noise_is_zero_mean_ish() {
        let sigma = 0.05;
        let cfg = ImuErrorCfg {
            accel_noise_sigma_mps2: sigma,
            seed: 7,
            ..Default::default()
        };
        let mut e = ImuErrors::new(cfg);
        let dt = 0.01;
        let n = 10_000;
        let mut sum = 0.0;
        let mut changed = false;
        for _ in 0..n {
            let x = e.corrupt(V3::new(0.0, 0.0, 0.0), dt).x;
            if x != 0.0 {
                changed = true;
            }
            sum += x;
        }
        assert!(changed, "sigma > 0 must perturb outputs");
        let mean = sum / n as f64;
        let bound = 5.0 * (sigma * dt.sqrt()) / (n as f64).sqrt();
        assert!(mean.abs() < bound, "mean {mean} exceeds {bound}");
    }
}
