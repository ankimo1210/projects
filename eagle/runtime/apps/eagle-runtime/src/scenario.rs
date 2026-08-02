//! Scenario loader (spec §6): the closed-loop run's site, gate state, AGC
//! choreography parameters, ROD schedule, optional sensor errors, and
//! acceptance thresholds. Every struct is `deny_unknown_fields` so a typo
//! in the TOML is a hard error, not a silent default.
use anyhow::{ensure, Context, Result};
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
    #[serde(default)]
    pub handover: Option<Handover>,
    /// Optional game-facing safety layer. Absence is the authentic default;
    /// committed acceptance scenarios deliberately omit this table.
    #[serde(default)]
    pub terminal_assist: Option<TerminalAssist>,
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
    #[serde(default)]
    pub mode: GateMode,
    pub alt_m: f64,
    pub vz_ms: f64,
    pub mass_dry_kg: f64,
    pub fuel_dps_kg: f64,
    pub fuel_rcs_kg: f64,
    pub inertia_kgm2: [f64; 3],
}

/// How `Scenario::initial_state` seeds sim truth: `Hover` (Wave 1, the
/// existing 500 m stationary-relative-to-surface gate) or `Pdi` (Wave 2 M1,
/// truth starts at the real PDI ignition point — see `padload::pdi_truth_state`).
#[derive(Debug, Clone, Copy, Default, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum GateMode {
    #[default]
    Hover,
    Pdi,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Agc {
    pub padload: String,
    pub lm_weight_lbs: f64,
    pub tland_offset_cs: i64,
    pub flip_atthold_after_engine_on_s: f64,
    #[serde(default)]
    pub lrbypass: bool,
    /// Diagnostic bisection: present LR altitude, but hold the active-low
    /// velocity data-good discrete in the NOT-good state for every velocity
    /// select. Defaults OFF so existing radar-live scenarios keep their
    /// full altitude + velocity behaviour.
    #[serde(default)]
    pub lr_altitude_only: bool,
    /// Diagnostic per-beam enable mask in X/Y/Z order. The default keeps
    /// all beams enabled; a scenario may isolate one velocity path without
    /// changing the simulator code used by the acceptance scenario.
    #[serde(default = "all_lr_velocity_beams")]
    pub lr_velocity_beams: [bool; 3],
}

fn all_lr_velocity_beams() -> [bool; 3] {
    [true; 3]
}

/// Sim-driven attitude/mode-control handover point (Wave 2 M1): once MM64
/// has been observed, the sim commands ATT HOLD + the selection ROD click
/// into P66 at this altitude.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Handover {
    /// Altitude (m AGL) at which, once MM64 has been observed, the sim
    /// commands ATT HOLD + the selection ROD click into P66. historical:
    /// the crew took over near 500 ft.
    pub alt_m: f64,
}

/// Explicitly assisted terminal-descent profile for the playable demo.
///
/// This is not an AGC tuning parameter. Once active, the simulator gently
/// drives truth toward a level, low-horizontal-speed descent while the real
/// Luminary program, DSKY and ROD input continue running. Keeping the switch
/// in the scenario makes the compromise visible and default-OFF.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TerminalAssist {
    /// Arm below this altitude after ENGINE ON.
    pub start_alt_m: f64,
    /// Linearly transition from `approach_vz_ms` here to
    /// `touchdown_vz_ms` at the surface.
    pub flare_alt_m: f64,
    /// Positive downward speed magnitude above the flare gate.
    pub approach_vz_ms: f64,
    /// Positive downward speed magnitude at the surface.
    pub touchdown_vz_ms: f64,
    /// Exponential time constant for removing surface-relative horizontal
    /// velocity.
    pub horizontal_tau_s: f64,
    /// Exponential time constant for tracking the scheduled vertical rate.
    pub vertical_tau_s: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rod {
    /// `[alt_m, vdgvert_delta_ms]` breakpoints (descending altitude).
    ///
    /// The second value is **NOT an absolute sink rate**, despite the
    /// field name. It is a delta on `VDGVERT` measured from the rate the
    /// AGC held at P66 entry: `STARTP66` DP-copies VDGVERT <- HDOTDISP
    /// (`vendor/virtualagc/Luminary099/
    /// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:155-157`, `DCA HDOTDISP` /
    /// `DXCH VDGVERT`, "SET DESIRED ALTITUDE RATE = CURRENT ALTITUDE
    /// RATE"), while `SimCore::phase8_rod` starts its own bookkeeping at
    /// 0 and emits `(new - previous) / ROD_CLICK_MS` clicks. So a step of
    /// `-5.3` commands 5.3 m/s MORE descent than P66 entry, not 5.3 m/s
    /// absolute. True in BOTH gate modes — the rope does the same copy
    /// whichever way P66 was entered.
    ///
    /// The field name is left alone deliberately: renaming it is a code
    /// change and would break every committed scenario file.
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
        let scenario: Scenario = toml::from_str(&text)
            .with_context(|| format!("parsing scenario {}", path.display()))?;
        scenario
            .validate()
            .with_context(|| format!("validating scenario {}", path.display()))?;
        Ok(scenario)
    }

    fn validate(&self) -> Result<()> {
        if let Some(a) = &self.terminal_assist {
            ensure!(
                a.start_alt_m > 0.0,
                "terminal_assist.start_alt_m must be > 0"
            );
            ensure!(
                a.flare_alt_m > 0.0 && a.flare_alt_m < a.start_alt_m,
                "terminal_assist.flare_alt_m must be between 0 and start_alt_m"
            );
            ensure!(
                a.approach_vz_ms >= a.touchdown_vz_ms && a.touchdown_vz_ms > 0.0,
                "terminal_assist descent speeds must satisfy approach >= touchdown > 0"
            );
            ensure!(
                a.horizontal_tau_s > 0.0 && a.vertical_tau_s > 0.0,
                "terminal_assist time constants must be > 0"
            );
        }
        Ok(())
    }

    /// Landing-site radial unit vector in the moon-fixed frame (z = pole).
    pub fn site_unit_mcmf(&self) -> V3<Mcmf> {
        let phi = self.site.lat_deg.to_radians();
        let lam = self.site.lon_deg.to_radians();
        V3::new(phi.cos() * lam.cos(), phi.cos() * lam.sin(), phi.sin())
    }

    /// Initial LM state at `epoch_s`, dispatched on `gate.mode`: `Hover`
    /// uses the Wave 1 stationary-gate geometry; `Pdi` starts sim truth at
    /// the real PDI ignition point (`padload::pdi_truth_state`).
    pub fn initial_state(&self, epoch_s: f64) -> LmState {
        match self.gate.mode {
            GateMode::Hover => self.hover_initial_state(epoch_s),
            GateMode::Pdi => crate::padload::pdi_truth_state(
                &crate::padload::StateCfg::default(),
                &crate::padload::PdiMasses {
                    dry_kg: self.gate.mass_dry_kg,
                    dps_kg: self.gate.fuel_dps_kg,
                    rcs_kg: self.gate.fuel_rcs_kg,
                },
                epoch_s,
            ),
        }
    }

    /// Initial LM state at `epoch_s`: on the site radial at gate altitude,
    /// body +X pointing up (radially out), no spin. Mass is dry + both
    /// propellants. The gate is a HOVER — stationary relative to the
    /// rotating surface — so the inertial velocity is `vz·up` plus the
    /// co-rotation term ω ẑ × r (the same ω·r the AGC pad-load state
    /// carries; see `padload::generate_state`).
    fn hover_initial_state(&self, epoch_s: f64) -> LmState {
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
pub(crate) fn body_x_to(u: V3<Mci>) -> Rot<Body, Mci> {
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
    fn loads_fast_debug_scenario() {
        let s = Scenario::load(&repo().join("scenarios/p66-gate-fast.toml")).unwrap();
        assert_eq!(s.name, "p66-gate-fast");
        assert!(
            s.agc.tland_offset_cs < 36_000,
            "fast scenario must shorten the TIG lead"
        );
    }

    #[test]
    fn loads_playable_demo_with_explicit_assist() {
        let s = Scenario::load(&repo().join("scenarios/playable-demo.toml")).unwrap();
        assert_eq!(s.name, "playable-demo-assisted");
        let assist = s.terminal_assist.expect("demo must opt into assist");
        assert_eq!(assist.start_alt_m, 500.0);
        assert_eq!(assist.flare_alt_m, 100.0);
        assert!(s.agc.lrbypass);
        assert!(s.rod.steps.is_empty());
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

    #[test]
    fn loads_pdi_descent_scenario() {
        let s = Scenario::load(&repo().join("scenarios/pdi-descent.toml")).unwrap();
        assert!(matches!(s.gate.mode, GateMode::Pdi));
        assert!(s.agc.lrbypass);
        // 250 m, not the historical 500 ft / 150 m: P64 flies the approach
        // down to ~237 m and hands to P65 there, and P65 is where the live
        // runs die (PROG alarm + the guidance stops modulating the
        // throttle), so at 150 m the handover never fires inside P64.
        // Measured, 2026-07-26 M1 flights 3-5 — see
        // docs/superpowers/notes/2026-07-26-m1-pdi-flight.md.
        assert!((s.handover.as_ref().unwrap().alt_m - 250.0).abs() < 1e-9);
        // The ROD schedule must be populated (Task 5 measured it) and must
        // descend: each breakpoint below the last.
        assert_eq!(s.rod.steps.len(), 3);
        assert!(
            s.rod.steps.windows(2).all(|w| w[1][0] < w[0][0]),
            "rod steps must be in descending altitude order: {:?}",
            s.rod.steps
        );
        assert!(
            s.rod.steps[0][0] < s.handover.as_ref().unwrap().alt_m,
            "the first rod step must sit below the handover altitude"
        );
        let st = s.initial_state(0.0);
        // PDI point = TIG, NOT the geometric ignition point: pdi_truth_state
        // back-propagates the geometric FLATOUT state by ZOOMTIME (26 s)
        // under gravity alone
        // (vendor/virtualagc/Luminary099/THE_LUNAR_LANDING.agc:193-198,
        // `TIG = TDEC1 - ZOOMTIME`), landing ~44.31 km uprange of it.
        // Why altitude/speed barely move despite that along-track shift:
        // `ignition_geometry`'s position/velocity are built radial vs.
        // purely tangential, so pos·vel = 0 exactly at the geometric point
        // — it IS the periapsis of the (Keplerian, gravity-only) coast
        // orbit (a ≈ 1,822,155 m, e ≈ 0.0382, period ≈ 6980 s). Near
        // periapsis the radius is second-order in the swept true anomaly ν:
        // r(ν) ≈ r_p·(1 + e/(2(1+e))·ν²). Solving Kepler's equation for
        // ν at 26 s before periapsis gives ν ≈ 0.02528 rad, predicting
        // Δr ≈ 20.60 m — matching the measured 15212.600731 m (TIG, below)
        // minus the geometric point's own ≈15192.006 m. Vis-viva then gives
        // the speed delta from that same Δr: dv = (μ/(r²v))·Δr ≈ 0.0193 m/s,
        // matching the geometric point's ≈1704.1867 m/s minus the measured
        // TIG speed below. Measured (this test, `StateCfg::default()` +
        // these masses, epoch_s=0.0): alt = 15212.600731466664 m, speed =
        // 1704.167404345077 m/s. Attitude is translation-invariant, so the
        // REFSMMAT-frame check below is exact, not measured.
        let alt = st.pos.norm() - s.site.radius_m;
        assert!((alt - 15212.600731466664).abs() < 0.5, "alt {alt}");
        assert!(
            (st.vel.norm() - 1704.167404345077).abs() < 0.01,
            "v {}",
            st.vel.norm()
        );
        let bx = st.att.apply(V3::<Body>::new(1.0, 0.0, 0.0));
        assert!((bx - V3::<Mci>::new(1.0, 0.0, 0.0)).norm() < 1e-9);
    }

    #[test]
    fn loads_lr_altitude_only_diagnostic_scenario() {
        let s = Scenario::load(&repo().join("scenarios/pdi-descent-lr-alt-only.toml")).unwrap();
        assert!(matches!(s.gate.mode, GateMode::Pdi));
        assert!(!s.agc.lrbypass, "the diagnostic must present the LR");
        assert!(
            s.agc.lr_altitude_only,
            "the diagnostic must withhold LR velocity data-good"
        );
    }

    #[test]
    fn loads_lr_position1_diagnostic_scenario() {
        let s = Scenario::load(&repo().join("scenarios/pdi-descent-lr-pos1.toml")).unwrap();
        assert!(matches!(s.gate.mode, GateMode::Pdi));
        assert!(!s.agc.lrbypass, "the diagnostic must present the LR");
        assert!(
            !s.agc.lr_altitude_only,
            "the diagnostic must enable all three velocity beams"
        );
    }

    #[test]
    fn loads_full_landing_radar_scenario() {
        let s = Scenario::load(&repo().join("scenarios/pdi-descent-lr-full.toml")).unwrap();
        assert!(matches!(s.gate.mode, GateMode::Pdi));
        assert!(!s.agc.lrbypass);
        assert!(!s.agc.lr_altitude_only);
        assert_eq!(s.acceptance.v_vert_max, 3.0);
        assert_eq!(s.acceptance.v_horiz_max, 1.5);
        assert_eq!(s.acceptance.tilt_max_deg, 12.0);
    }

    #[test]
    fn loads_x_only_landing_radar_scenario() {
        let s = Scenario::load(&repo().join("scenarios/pdi-descent-lr-x-only.toml")).unwrap();
        assert!(!s.agc.lrbypass);
        assert_eq!(s.agc.lr_velocity_beams, [true, false, false]);
    }

    #[test]
    fn loads_p65_landing_radar_scenario_without_forced_handover() {
        let s = Scenario::load(&repo().join("scenarios/pdi-descent-p65.toml")).unwrap();
        assert!(matches!(s.gate.mode, GateMode::Pdi));
        assert!(!s.agc.lrbypass, "P65 requires the landing radar");
        assert!(s.handover.is_none(), "the rope must select P65 itself");
        assert_eq!(s.acceptance.v_vert_max, 3.0);
        assert_eq!(s.acceptance.v_horiz_max, 1.5);
        assert_eq!(s.acceptance.tilt_max_deg, 12.0);
    }

    #[test]
    fn hover_scenarios_do_not_need_the_new_fields() {
        // Back-compat: the committed Wave 1 files carry no mode/handover/lrbypass.
        let s = Scenario::load(&repo().join("scenarios/p66-gate.toml")).unwrap();
        assert!(matches!(s.gate.mode, GateMode::Hover));
        assert!(s.handover.is_none());
        assert!(s.terminal_assist.is_none());
        assert!(!s.agc.lrbypass);
        assert!(
            !s.agc.lr_altitude_only,
            "existing scenarios must retain full LR behaviour by default"
        );
        assert_eq!(s.agc.lr_velocity_beams, [true; 3]);
    }
}
