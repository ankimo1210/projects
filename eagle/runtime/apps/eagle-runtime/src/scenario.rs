//! Scenario loader (spec §6): the closed-loop run's site, gate state, AGC
//! choreography parameters, ROD schedule, optional sensor errors, and
//! acceptance thresholds. Every struct is `deny_unknown_fields` so a typo
//! in the TOML is a hard error, not a silent default.
use anyhow::{Context, Result};
use eagle_dynamics::frames::{mci_to_mcmf, retag, Body, Mci, Mcmf, Rot, V3};
use eagle_dynamics::state::LmState;
use eagle_sensors::errors::ImuErrorCfg;
use serde::Deserialize;
use std::path::Path;

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Scenario {
    pub schema: u32,
    pub name: String,
    pub site: Site,
    pub gate: Gate,
    pub agc: Agc,
    pub rod: Rod,
    #[serde(default)]
    pub errors: Errors,
    pub acceptance: Acceptance,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Site {
    pub lat_deg: f64,
    pub lon_deg: f64,
    pub radius_m: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Gate {
    pub alt_m: f64,
    pub vz_ms: f64,
    pub mass_dry_kg: f64,
    pub fuel_dps_kg: f64,
    pub fuel_rcs_kg: f64,
    pub inertia_kgm2: [f64; 3],
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Agc {
    pub padload: String,
    pub lm_weight_lbs: f64,
    pub tland_offset_cs: i64,
    pub flip_atthold_after_engine_on_s: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rod {
    /// `[alt_m, target_sink_rate_ms]` breakpoints (descending altitude).
    pub steps: Vec<[f64; 2]>,
}

/// Optional sensor error injection. An empty `[errors]` table means all OFF.
#[derive(Debug, Clone, Default, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Errors {
    pub imu: Option<ImuErrorSpec>,
}

/// Serde mirror of `eagle_sensors::errors::ImuErrorCfg` (which is
/// deliberately serde-free).
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ImuErrorSpec {
    #[serde(default)]
    pub accel_bias_mps2: [f64; 3],
    #[serde(default)]
    pub accel_scale_ppm: [f64; 3],
    #[serde(default)]
    pub accel_noise_sigma_mps2: f64,
    #[serde(default)]
    pub seed: u64,
}

impl From<&ImuErrorSpec> for ImuErrorCfg {
    fn from(s: &ImuErrorSpec) -> Self {
        ImuErrorCfg {
            accel_bias_mps2: s.accel_bias_mps2,
            accel_scale_ppm: s.accel_scale_ppm,
            accel_noise_sigma_mps2: s.accel_noise_sigma_mps2,
            seed: s.seed,
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Acceptance {
    pub v_vert_max: f64,
    pub v_horiz_max: f64,
    pub tilt_max_deg: f64,
    pub timeout_s: f64,
}

impl Scenario {
    pub fn load(path: &Path) -> Result<Scenario> {
        let text = std::fs::read_to_string(path)
            .with_context(|| format!("reading scenario {}", path.display()))?;
        toml::from_str(&text).with_context(|| format!("parsing scenario {}", path.display()))
    }

    /// Landing-site radial unit vector in the moon-fixed frame (z = pole).
    pub fn site_unit_mcmf(&self) -> V3<Mcmf> {
        let phi = self.site.lat_deg.to_radians();
        let lam = self.site.lon_deg.to_radians();
        V3::new(phi.cos() * lam.cos(), phi.cos() * lam.sin(), phi.sin())
    }

    /// Initial LM state at `epoch_s`: on the site radial at gate altitude,
    /// body +X pointing up (radially out), no spin. Mass is dry + both
    /// propellants. The gate is a HOVER — stationary relative to the
    /// rotating surface — so the inertial velocity is `vz·up` plus the
    /// co-rotation term ω ẑ × r (the same ω·r the AGC pad-load state
    /// carries; see `padload::generate_state`).
    pub fn initial_state(&self, epoch_s: f64) -> LmState {
        let mcmf_to_mci = mci_to_mcmf(epoch_s).inverse();
        let up_mci = mcmf_to_mci.apply(self.site_unit_mcmf()).unit();
        let pos = up_mci.scale(self.site.radius_m + self.gate.alt_m);
        let vel = up_mci.scale(self.gate.vz_ms) + eagle_dynamics::state::surface_velocity(pos);
        let att = body_x_to(up_mci);
        LmState {
            t: epoch_s,
            pos,
            vel,
            att,
            omega: V3::zero(),
            mass_kg: self.gate.mass_dry_kg + self.gate.fuel_dps_kg + self.gate.fuel_rcs_kg,
            fuel_dps_kg: self.gate.fuel_dps_kg,
            fuel_rcs_kg: self.gate.fuel_rcs_kg,
        }
    }
}

/// A Body→MCI attitude whose body +X maps to the MCI unit vector `u`.
fn body_x_to(u: V3<Mci>) -> Rot<Body, Mci> {
    let x = V3::<Mci>::new(1.0, 0.0, 0.0);
    let c = x.dot(u);
    let r: Rot<Mci, Mci> = if c > 1.0 - 1e-12 {
        Rot::identity()
    } else if c < -1.0 + 1e-12 {
        // antiparallel: 180° about any axis ⊥ x
        Rot::from_axis_angle(V3::new(0.0, 1.0, 0.0), std::f64::consts::PI)
    } else {
        Rot::from_axis_angle(x.cross(u), c.acos())
    };
    retag(r)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn repo() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
    }

    #[test]
    fn loads_committed_p66_gate() {
        let s = Scenario::load(&repo().join("scenarios/p66-gate.toml")).unwrap();
        assert_eq!(s.schema, 1);
        assert_eq!(s.name, "p66-gate");
        assert_eq!(s.rod.steps.len(), 3);
        assert!(s.errors.imu.is_none()); // empty [errors] = OFF
        assert_eq!(s.acceptance.v_vert_max, 3.0);
    }

    #[test]
    fn unknown_field_is_rejected() {
        let bad = r#"
            schema = 1
            name = "x"
            [site]
            lat_deg = 0.0
            lon_deg = 0.0
            radius_m = 1737400.0
            typo_field = 3
            [gate]
            alt_m = 500.0
            vz_ms = 0.0
            mass_dry_kg = 7009.0
            fuel_dps_kg = 2000.0
            fuel_rcs_kg = 150.0
            inertia_kgm2 = [1.0, 2.0, 3.0]
            [agc]
            padload = "x"
            lm_weight_lbs = 1.0
            tland_offset_cs = 1
            flip_atthold_after_engine_on_s = 2.0
            [rod]
            steps = []
            [errors]
            [acceptance]
            v_vert_max = 3.0
            v_horiz_max = 1.5
            tilt_max_deg = 12.0
            timeout_s = 300.0
        "#;
        assert!(toml::from_str::<Scenario>(bad).is_err());
    }

    #[test]
    fn imu_bias_scenario_populates_error_cfg() {
        let s = Scenario::load(&repo().join("scenarios/p66-gate-imu-bias.toml")).unwrap();
        let imu = s.errors.imu.expect("[errors.imu] present");
        assert_eq!(imu.accel_bias_mps2, [0.0005, 0.0002, 0.0]);
        assert_eq!(imu.seed, 42);
        // Converts 1:1 into the sensors ImuErrorCfg.
        let cfg: eagle_sensors::errors::ImuErrorCfg = (&imu).into();
        assert_eq!(cfg.accel_bias_mps2, [0.0005, 0.0002, 0.0]);
    }

    #[test]
    fn initial_state_geometry() {
        let s = Scenario::load(&repo().join("scenarios/p66-gate.toml")).unwrap();
        let st = s.initial_state(1234.0);
        let r = s.site.radius_m + s.gate.alt_m;
        assert!((st.pos.norm() - r).abs() / r < 1e-6);
        // body +X parallel to the radial
        let bx = st.att.apply(V3::<Body>::new(1.0, 0.0, 0.0));
        let up = st.pos.unit();
        assert!((bx.dot(up) - 1.0).abs() < 1e-9, "body x not radial: {bx:?}");
        // Hover gate = stationary relative to the surface (vz_ms = 0 here):
        // inertial velocity must be exactly the co-rotation term.
        let v_rel = st.vel - eagle_dynamics::state::surface_velocity(st.pos);
        assert!(v_rel.norm() < 1e-9, "gate not co-rotating: {v_rel:?}");
    }
}
