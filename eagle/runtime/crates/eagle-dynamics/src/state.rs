//! Rigid-body state and lunar gravity (spec §4).
//!
//! The LM state carries position/velocity in MCI, attitude as a Body→Mci
//! rotation, body-frame angular velocity, and mass/fuel bookkeeping. All
//! vectors are typed frames — no anonymous `[f64; 3]` crosses a boundary.
use crate::frames::{Body, Mci, Rot, V3};

/// Full 14-degree-of-freedom LM state at one instant.
#[derive(Debug, Clone, PartialEq)]
pub struct LmState {
    /// Seconds since sim start.
    pub t: f64,
    /// Position, MCI, m.
    pub pos: V3<Mci>,
    /// Velocity, MCI, m/s.
    pub vel: V3<Mci>,
    /// Attitude: rotates Body-frame vectors into MCI.
    pub att: Rot<Body, Mci>,
    /// Angular velocity, Body frame, rad/s.
    pub omega: V3<Body>,
    /// Total vehicle mass, kg.
    pub mass_kg: f64,
    /// Remaining DPS propellant, kg.
    pub fuel_dps_kg: f64,
    /// Remaining RCS propellant, kg.
    pub fuel_rcs_kg: f64,
}

/// Time-derivatives supplied by a force model to the integrator: linear
/// acceleration (MCI), angular acceleration (Body), and mass-flow rates
/// (all ≤ 0; `mdot_total` = dps + rcs).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Derivs {
    pub acc: V3<Mci>,
    pub alpha: V3<Body>,
    pub mdot_total: f64,
    pub mdot_dps: f64,
    pub mdot_rcs: f64,
}

/// Point-mass lunar gravity at `pos` (MCI), m/s²: −μ/r² along the radial.
pub fn gravity(pos: V3<Mci>) -> V3<Mci> {
    let r2 = pos.dot(pos);
    pos.unit().scale(-crate::constants::MU_MOON / r2)
}

/// Inertial (MCI) velocity of the co-rotating lunar surface point at
/// `pos`: ω ẑ × pos (MCI z = lunar pole, docs/coordinate-frames.md). A
/// vehicle hovering — stationary relative to the ground — carries exactly
/// this velocity.
pub fn surface_velocity(pos: V3<Mci>) -> V3<Mci> {
    let w = crate::constants::OMEGA_MOON;
    V3::new(-w * pos.y, w * pos.x, 0.0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::constants::{MU_MOON, R_SITE};

    #[test]
    fn gravity_points_inward_with_inverse_square_magnitude() {
        let r = R_SITE + 500.0;
        let g = gravity(V3::<Mci>::new(r, 0.0, 0.0));
        // points toward the centre (−x here)
        assert!(g.x < 0.0 && g.y == 0.0 && g.z == 0.0);
        assert!((g.norm() - MU_MOON / (r * r)).abs() < 1e-9);
    }

    #[test]
    fn surface_velocity_is_eastward_and_horizontal() {
        use crate::constants::OMEGA_MOON;
        let r = R_SITE;
        let v = surface_velocity(V3::<Mci>::new(r, 0.0, 0.0));
        assert!(v.x == 0.0 && v.z == 0.0);
        assert!(
            (v.y - OMEGA_MOON * r).abs() < 1e-12,
            "eastward ω·r at the equator"
        );
        // Perpendicular to the radial everywhere.
        let p = V3::<Mci>::new(0.3 * r, -0.5 * r, 0.8 * r);
        assert!(surface_velocity(p).dot(p).abs() < 1e-6);
    }
}
