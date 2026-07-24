//! DPS/RCS force and torque model (spec §4).
//!
//! Min-impulse note: the AGC times sub-tick jet pulses internally (T6RUPT,
//! ~14 ms minimum). Our fixed 10 ms tick applies the latest jet word for a
//! whole tick, so jet timing is quantized to ~10 ms worst case — accepted
//! for Wave 1.
use crate::constants::{
    DPS_FTP_N, DPS_MAX_N, DPS_MIN_N, DPS_TAU, DPS_VE, RCS_THRUST_N, RCS_VE, RCS_LEVER_M,
};
use crate::frames::{Body, V3};
use crate::state::{Derivs, LmState};

/// DPS gimbal mount below the CG on the −X (thrust) axis, m. Provenance:
/// assumed.
pub const ENGINE_MOUNT_M: f64 = -1.7;

/// Const-friendly plain triple; only `forces` turns it into a typed
/// `V3<Body>`. Keeps `JET_TABLE`/inertia usable in `const` position.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct V3Raw(pub f64, pub f64, pub f64);

impl V3Raw {
    fn body(self) -> V3<Body> {
        V3::new(self.0, self.1, self.2)
    }
}

/// Commanded autopilot actuator state for one tick.
#[derive(Debug, Clone, PartialEq)]
pub struct Actuators {
    pub engine_on: bool,
    pub throttle_cmd_n: f64,
    pub thrust_n: f64,
    pub trim_pitch_rad: f64,
    pub trim_roll_rad: f64,
    /// Bit i set ⇒ `JET_TABLE[i]` firing (bits 0-7 ← ch005 bits 1-8,
    /// bits 8-15 ← ch006 bits 1-8).
    pub jets: u16,
}

/// One RCS thruster: name, mount position and thrust direction (BODY).
#[derive(Debug, Clone, Copy)]
pub struct Jet {
    pub name: &'static str,
    pub pos: V3Raw,
    pub dir: V3Raw,
}

// Quad mount positions in the Y-Z plane at 45° azimuths, radius RCS_LEVER_M
// (`lm_simulator.tcl`; azimuths chosen so the couple/yaw torque signs below
// reproduce LM_Simulator's axis mapping, AGC_Simulation_Monitor_Control.tcl
// :231-305). L = RCS_LEVER_M, s = L/√2.
//   Q1 = (0, +s, +s)  Q2 = (0, −s, +s)  Q3 = (0, −s, −s)  Q4 = (0, +s, −s)
// U jets push −X (nozzle up), D jets push +X. Tangential jets lie in the
// Y-Z plane; the "+yaw" quartet {Q1F,Q2L,Q3A,Q4R} is the CCW tangent
// (0,−z,y)/L at each quad (all give +X torque), the "−yaw" quartet
// {Q1L,Q2A,Q3R,Q4F} the CW tangent.
const S: f64 = std::f64::consts::FRAC_1_SQRT_2; // 1/√2, so |(±s,±s)| = 1·L
const L: f64 = RCS_LEVER_M;

/// Bit-indexed thruster table: index = jet bit (ch005 bits 1-8 → 0-7,
/// ch006 bits 1-8 → 8-15). Order pinned by the Task 1 channel-map doc.
pub const JET_TABLE: [Jet; 16] = [
    // ch005 (PYJETS) bits 1-8: Q4U,Q4D,Q3U,Q3D,Q2U,Q2D,Q1U,Q1D
    Jet { name: "Q4U", pos: V3Raw(0.0, L * S, -L * S), dir: V3Raw(-1.0, 0.0, 0.0) },
    Jet { name: "Q4D", pos: V3Raw(0.0, L * S, -L * S), dir: V3Raw(1.0, 0.0, 0.0) },
    Jet { name: "Q3U", pos: V3Raw(0.0, -L * S, -L * S), dir: V3Raw(-1.0, 0.0, 0.0) },
    Jet { name: "Q3D", pos: V3Raw(0.0, -L * S, -L * S), dir: V3Raw(1.0, 0.0, 0.0) },
    Jet { name: "Q2U", pos: V3Raw(0.0, -L * S, L * S), dir: V3Raw(-1.0, 0.0, 0.0) },
    Jet { name: "Q2D", pos: V3Raw(0.0, -L * S, L * S), dir: V3Raw(1.0, 0.0, 0.0) },
    Jet { name: "Q1U", pos: V3Raw(0.0, L * S, L * S), dir: V3Raw(-1.0, 0.0, 0.0) },
    Jet { name: "Q1D", pos: V3Raw(0.0, L * S, L * S), dir: V3Raw(1.0, 0.0, 0.0) },
    // ch006 (ROLLJETS) bits 1-8: Q3A,Q4F,Q1F,Q2A,Q2L,Q3R,Q4R,Q1L
    Jet { name: "Q3A", pos: V3Raw(0.0, -L * S, -L * S), dir: V3Raw(0.0, S, -S) },
    Jet { name: "Q4F", pos: V3Raw(0.0, L * S, -L * S), dir: V3Raw(0.0, -S, -S) },
    Jet { name: "Q1F", pos: V3Raw(0.0, L * S, L * S), dir: V3Raw(0.0, -S, S) },
    Jet { name: "Q2A", pos: V3Raw(0.0, -L * S, L * S), dir: V3Raw(0.0, S, S) },
    Jet { name: "Q2L", pos: V3Raw(0.0, -L * S, L * S), dir: V3Raw(0.0, -S, -S) },
    Jet { name: "Q3R", pos: V3Raw(0.0, -L * S, -L * S), dir: V3Raw(0.0, -S, S) },
    Jet { name: "Q4R", pos: V3Raw(0.0, L * S, -L * S), dir: V3Raw(0.0, S, S) },
    Jet { name: "Q1L", pos: V3Raw(0.0, L * S, L * S), dir: V3Raw(0.0, S, -S) },
];

/// DPS throttle envelope: no thrust below MIN; linear through the
/// throttleable band up to 0.6·MAX; above that it snaps to the fixed
/// throttle point (FTP).
pub fn dps_envelope(cmd_n: f64) -> f64 {
    if cmd_n < DPS_MIN_N {
        0.0
    } else if cmd_n <= 0.6 * DPS_MAX_N {
        cmd_n
    } else {
        DPS_FTP_N
    }
}

/// First-order throttle lag toward the envelope of the command. Thrust
/// falls to zero when the engine is off (the caller also gates on fuel).
pub fn actuator_step(a: &mut Actuators, dt: f64) {
    if !a.engine_on {
        a.thrust_n = 0.0;
        return;
    }
    let target = dps_envelope(a.throttle_cmd_n);
    a.thrust_n += (target - a.thrust_n) * (1.0 - (-dt / DPS_TAU).exp());
}

/// Thrust direction (BODY): nominal +X tilted by the trim gimbal — pitch
/// about +Y, roll about +Z (small-angle exact via two rotations).
fn thrust_dir(pitch: f64, roll: f64) -> V3<Body> {
    // Ry(pitch)·x̂ = (cos p, 0, −sin p); then Rz(roll).
    let (sp, cp) = pitch.sin_cos();
    let (sr, cr) = roll.sin_cos();
    V3::new(cp * cr, cp * sr, -sp)
}

/// Net force/torque on the vehicle from the DPS and every firing RCS jet,
/// plus lunar gravity, as state derivatives. `inertia0` is the diagonal
/// body inertia (kg·m²) at `mass0_kg`; the inertia used scales linearly
/// with the current mass (Wave 1 model, provenance assumed).
pub fn forces(s: &LmState, a: &Actuators, inertia0: V3Raw, mass0_kg: f64) -> Derivs {
    let mut force = V3::<Body>::zero();
    let mut torque = V3::<Body>::zero();

    // DPS: thrust along the trimmed +X, applied at the gimbal mount.
    if a.engine_on && a.thrust_n > 0.0 {
        let f = thrust_dir(a.trim_pitch_rad, a.trim_roll_rad).scale(a.thrust_n);
        let mount = V3::<Body>::new(ENGINE_MOUNT_M, 0.0, 0.0);
        force = force + f;
        torque = torque + mount.cross(f);
    }

    // RCS: each firing jet's force at its mount.
    let mut jets_firing = 0u32;
    for (i, jet) in JET_TABLE.iter().enumerate() {
        if a.jets & (1 << i) != 0 {
            jets_firing += 1;
            let f = jet.dir.body().scale(RCS_THRUST_N);
            force = force + f;
            torque = torque + jet.pos.body().cross(f);
        }
    }

    // Linear acceleration: body force → MCI, over mass, plus gravity.
    let acc = s.att.apply(force).scale(1.0 / s.mass_kg) + crate::state::gravity(s.pos);

    // Angular acceleration: Euler's equation with a diagonal inertia that
    // scales with mass. alpha = (τ − ω×(I∘ω)) / I, componentwise.
    let scale = s.mass_kg / mass0_kg;
    let inertia = V3::<Body>::new(inertia0.0 * scale, inertia0.1 * scale, inertia0.2 * scale);
    let iw = V3::<Body>::new(
        inertia.x * s.omega.x,
        inertia.y * s.omega.y,
        inertia.z * s.omega.z,
    );
    let gyro = s.omega.cross(iw);
    let alpha = V3::<Body>::new(
        (torque.x - gyro.x) / inertia.x,
        (torque.y - gyro.y) / inertia.y,
        (torque.z - gyro.z) / inertia.z,
    );

    let mdot_dps = if a.engine_on { -a.thrust_n / DPS_VE } else { 0.0 };
    let mdot_rcs = -(jets_firing as f64) * RCS_THRUST_N / RCS_VE;

    Derivs {
        acc,
        alpha,
        mdot_total: mdot_dps + mdot_rcs,
        mdot_dps,
        mdot_rcs,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testutil::hover_state;

    #[test]
    fn envelope_clamps_and_ftp_snaps() {
        assert_eq!(dps_envelope(0.0), 0.0);
        assert_eq!(dps_envelope(3000.0), 0.0); // below MIN → no thrust band
        assert_eq!(dps_envelope(10_000.0), 10_000.0); // throttleable band
        assert_eq!(dps_envelope(0.6 * DPS_MAX_N), 0.6 * DPS_MAX_N);
        assert_eq!(dps_envelope(0.61 * DPS_MAX_N), DPS_FTP_N); // FTP snap
    }

    #[test]
    fn throttle_lag_first_order() {
        let mut a = Actuators {
            engine_on: true,
            throttle_cmd_n: 20_000.0,
            thrust_n: 0.0,
            trim_pitch_rad: 0.0,
            trim_roll_rad: 0.0,
            jets: 0,
        };
        actuator_step(&mut a, DPS_TAU); // one time constant
        assert!((a.thrust_n / 20_000.0 - 0.632).abs() < 0.01);
    }

    #[test]
    fn dps_thrust_along_body_x_and_trim_torques() {
        let s = hover_state();
        let a = Actuators {
            engine_on: true,
            throttle_cmd_n: 20_000.0,
            thrust_n: 20_000.0,
            trim_pitch_rad: 0.01,
            trim_roll_rad: 0.0,
            jets: 0,
        };
        let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
        // thrust ~ +X body = +x MCI (identity attitude), minus gravity pull
        assert!(d.acc.x > 0.0);
        // pitch trim tilts thrust → torque about the trim axis, sign per geometry
        assert!(d.alpha.y.abs() > 0.0 && d.alpha.z.abs() < 1e-12);
    }

    #[test]
    fn rcs_axis_mapping_matches_lm_simulator() {
        let s = hover_state();
        let base = Actuators {
            engine_on: false,
            throttle_cmd_n: 0.0,
            thrust_n: 0.0,
            trim_pitch_rad: 0.0,
            trim_roll_rad: 0.0,
            jets: 0,
        };
        let jet = |name: &str| JET_TABLE.iter().position(|j| j.name == name).unwrap();
        // Q2D + Q4U together: pure "V-axis" rotation, no net force couple errors.
        // Transverse inertia is symmetric here (13000,13000) so alpha directly
        // reflects the equal-magnitude torque about the 45° axis — the plan's
        // (13500,13000) makes |αy|=|αz| impossible for equal torque (α=τ/I),
        // and this test is about jet geometry, not inertia coupling.
        let mut a = base.clone();
        a.jets = (1 << jet("Q2D")) | (1 << jet("Q4U"));
        let d = forces(&s, &a, V3Raw(12_000.0, 13_000.0, 13_000.0), 9159.0);
        let (ay, az) = (d.alpha.y, d.alpha.z);
        // couple: same-magnitude rotation about the 45° axis, zero X torque
        assert!(d.alpha.x.abs() < 1e-9);
        assert!((ay.abs() - az.abs()).abs() < 1e-9 && ay.hypot(az) > 0.0);
        // yaw quartet: pure X torque
        let mut a = base.clone();
        a.jets = ["Q1F", "Q2L", "Q3A", "Q4R"]
            .iter()
            .fold(0, |m, n| m | 1 << jet(n));
        let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
        assert!(d.alpha.x.abs() > 0.0 && d.alpha.y.abs() < 1e-9 && d.alpha.z.abs() < 1e-9);
    }

    #[test]
    fn fuel_burn_rates() {
        let s = hover_state();
        let mut a = Actuators {
            engine_on: true,
            throttle_cmd_n: 30_000.0,
            thrust_n: 30_000.0,
            trim_pitch_rad: 0.0,
            trim_roll_rad: 0.0,
            jets: 1,
        };
        let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
        assert!((d.mdot_dps - (-30_000.0 / DPS_VE)).abs() < 1e-9);
        assert!((d.mdot_rcs - (-RCS_THRUST_N / RCS_VE)).abs() < 1e-9);
        a.jets = 0b11; // two jets
        let d = forces(&s, &a, V3Raw(12_000.0, 13_500.0, 13_000.0), 9159.0);
        assert!((d.mdot_rcs - (-2.0 * RCS_THRUST_N / RCS_VE)).abs() < 1e-9);
    }
}
