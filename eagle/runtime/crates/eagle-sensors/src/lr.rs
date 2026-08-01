//! Landing radar: beam geometry against a spherical moon.
//!
//! M3 of the Wave 2 spec (`docs/superpowers/specs/
//! 2026-07-26-eagle-wave2-real-descent-design.md`). This module is the
//! **geometry only** — where the beams point and what they would measure.
//! The AGC interface (counters, data-good discretes, the R12 read
//! sequence) is separate, because the geometry is testable offline with
//! no AGC and the interface is not.
//!
//! # Why the LM needs this at all
//!
//! Inertial navigation accrues altitude error through a powered descent.
//! This project measures the AGC ending P64 about **190 m low** on a run
//! flown with the radar bypassed, reproducibly across flights 9-11
//! (`docs/superpowers/notes/2026-07-31-m1b-rod-loop.md`). The real LM
//! corrected exactly this with the landing radar; every flight here so
//! far has run `lrbypass = true` and nothing has ever corrected it.
//!
//! # Channel 33 is ACTIVE LOW — verified, and easy to get backwards
//!
//! `INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:206-224` lists bit 5 as
//! "LR RANGE DATA GOOD", bit 6 "LR POS1", bit 7 "LR POS2", bit 8 "LR VEL
//! DATA GOOD" — but `ASSEMBLY_AND_OPERATION_INFORMATION.agc:873-874`
//! spells the position bits as "**NOT** POSIT. 1" / "**NOT** POSIT. 2",
//! and the rope confirms it:
//!
//! ```text
//!   POS2CHK   CAF   BIT7      # VERIFY LR IN POS2
//!             EXTEND
//!             RAND  CHAN33
//!             EXTEND
//!             BZF   UPDATCHK  # IT IS-CHECK FOR LR UPDATE
//! ```
//! (`SERVICER.agc:749-753`.) `BZF` branches on ZERO, so "the LR **is** in
//! position 2" is bit 7 **CLEAR**. Asserting these bits the intuitive way
//! round makes the radar either invisible or permanently alarmed —
//! `LRPOSALM` raises alarm 0522 (`P20-P25.agc:2864-2869`).
use eagle_dynamics::frames::{Body, Frame, Mcmf, V3};

/// One landing-radar beam, as a unit vector in body axes.
#[derive(Debug, Clone, Copy)]
pub struct Beam {
    pub dir: V3<Body>,
}

/// What a beam measured, or why it did not.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BeamReading {
    /// Slant range to the surface along the beam, metres.
    Range(f64),
    /// Surface-relative velocity component along the beam, m/s.
    Velocity(f64),
    /// The beam does not intersect the surface ahead of the vehicle.
    NoReturn,
}

/// Slant range from `pos` along unit direction `dir` to a sphere of
/// radius `r_surface` centred at the origin.
///
/// Closed form, because there is no terrain: substituting
/// `p + t·d` into `|x| = r` gives `t² + 2(p·d)t + (|p|² − r²) = 0`, and
/// the nearer non-negative root is the return. A beam pointing away from
/// the surface has no non-negative root and yields `NoReturn` — which is
/// a real flight condition during the pitchover, not an error.
pub fn slant_range<F: Frame>(pos: V3<F>, dir: V3<F>, r_surface: f64) -> BeamReading {
    let d = dir.unit();
    let b = pos.dot(d);
    let c = pos.dot(pos) - r_surface * r_surface;
    let disc = b * b - c;
    if disc < 0.0 {
        return BeamReading::NoReturn;
    }
    let root = disc.sqrt();
    // Near root first; if it is behind us, try the far one.
    let t = {
        let t0 = -b - root;
        if t0 >= 0.0 {
            t0
        } else {
            -b + root
        }
    };
    if t < 0.0 {
        BeamReading::NoReturn
    } else {
        BeamReading::Range(t)
    }
}

/// Surface-relative velocity projected onto a beam, positive CLOSING.
///
/// The range shrinks by the component of velocity along the beam, so the
/// closing rate is `v · d̂` — not its negation. A vehicle descending at
/// 30 m/s with a beam pointing down has `v·d̂ = (−30)(−1) = +30`, and its
/// altitude is indeed falling at 30 m/s.
pub fn beam_velocity<F: Frame>(vel_surface: V3<F>, dir: V3<F>) -> f64 {
    vel_surface.dot(dir.unit())
}

/// Whether the geometry admits a usable return at all: the beam must
/// point at the surface and the slant range must be inside the radar's
/// operating band.
///
/// Range limits are the LR's published ones, and are deliberately NOT
/// invented here — they gate `Range` into a data-good discrete, and that
/// gating belongs with the AGC interface where the discrete lives.
pub fn in_band(range_m: f64, min_m: f64, max_m: f64) -> bool {
    range_m >= min_m && range_m <= max_m
}

/// Convenience: altitude above the sphere, for cross-checking a beam
/// against the vehicle state in tests.
pub fn altitude<F: Frame>(pos: V3<F>, r_surface: f64) -> f64 {
    pos.norm() - r_surface
}

/// The moon-fixed radius the beams intersect. Kept as a parameter rather
/// than a constant so a test can use a unit sphere.
pub type Surface = Mcmf;

#[cfg(test)]
mod tests {
    use super::*;
    use eagle_dynamics::frames::V3;

    const R: f64 = 1_737_400.0;

    #[test]
    fn a_beam_straight_down_reads_the_altitude() {
        // Straight down from 1000 m: the slant range IS the altitude.
        let pos = V3::<Body>::new(R + 1000.0, 0.0, 0.0);
        let down = V3::<Body>::new(-1.0, 0.0, 0.0);
        match slant_range(pos, down, R) {
            BeamReading::Range(r) => assert!((r - 1000.0).abs() < 1e-6, "{r}"),
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn a_tilted_beam_reads_longer_than_the_altitude() {
        // The whole point of a slant range: at 30 deg off vertical from
        // 1000 m the return is 1000/cos(30) = 1154.7 m, to first order.
        let h = 1000.0;
        let pos = V3::<Body>::new(R + h, 0.0, 0.0);
        let a = 30f64.to_radians();
        let dir = V3::<Body>::new(-a.cos(), a.sin(), 0.0);
        match slant_range(pos, dir, R) {
            BeamReading::Range(r) => {
                let flat = h / a.cos();
                // The sphere curves AWAY from the vehicle, so a tilted
                // beam travels FARTHER than the flat-moon value, not
                // less. At 1 km and 30 deg the excess is ~1.3 m.
                assert!(r > flat, "curvature must lengthen: {r} vs {flat}");
                assert!((r - flat).abs() < 5.0, "{r} vs {flat}");
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn a_beam_pointing_up_has_no_return() {
        let pos = V3::<Body>::new(R + 1000.0, 0.0, 0.0);
        let up = V3::<Body>::new(1.0, 0.0, 0.0);
        assert_eq!(slant_range(pos, up, R), BeamReading::NoReturn);
        // Horizontal from 1 km up also misses a sphere this size at any
        // sane range... but it does NOT: a horizontal beam grazes and
        // re-enters. That is real geometry, so assert what is true.
        let horiz = V3::<Body>::new(0.0, 1.0, 0.0);
        assert!(matches!(slant_range(pos, horiz, R), BeamReading::NoReturn));
    }

    #[test]
    fn closing_velocity_is_positive_while_descending() {
        // A vehicle descending at 30 m/s, beam straight down.
        let vel = V3::<Body>::new(-30.0, 0.0, 0.0);
        let down = V3::<Body>::new(-1.0, 0.0, 0.0);
        assert!(
            (beam_velocity(vel, down) - 30.0).abs() < 1e-9,
            "{}",
            beam_velocity(vel, down)
        );
        // Climbing opens the range, so the sign flips.
        let up_vel = V3::<Body>::new(30.0, 0.0, 0.0);
        assert!((beam_velocity(up_vel, down) + 30.0).abs() < 1e-9);
    }

    #[test]
    fn the_band_gate_is_inclusive_at_both_ends() {
        assert!(in_band(10.0, 10.0, 1000.0));
        assert!(in_band(1000.0, 10.0, 1000.0));
        assert!(!in_band(9.9, 10.0, 1000.0));
        assert!(!in_band(1000.1, 10.0, 1000.0));
    }

    #[test]
    fn altitude_matches_a_vertical_beam_at_descent_altitudes() {
        // Cross-check the two independent paths at altitudes this project
        // actually flies, including the P66 band where the radar matters.
        for h in [15_000.0, 3_000.0, 250.0, 40.0] {
            let pos = V3::<Body>::new(R + h, 0.0, 0.0);
            let down = V3::<Body>::new(-1.0, 0.0, 0.0);
            let BeamReading::Range(r) = slant_range(pos, down, R) else {
                panic!("no return at {h} m");
            };
            assert!((r - altitude(pos, R)).abs() < 1e-6, "h={h}");
        }
    }
}
