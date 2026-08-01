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
//! # The AGC interface, verified (step 0) — not yet implemented
//!
//! Recorded here so it is not re-derived. The AGC selects a radar
//! quantity on **channel 13**: bits 1-3 are the "A,B,C matrix" select and
//! bit 4 is RADAR ACTIVITY
//! (`INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:102`, `:117-120`). The
//! radar answers with pulses into the **`RNRAD` counter, address 0o46**
//! (`ERASABLE_ASSIGNMENTS.agc:141`).
//!
//! The lead-in routines write these exact octal values to channel 13
//! (`P20-P25.agc:2738-2755`), i.e. activity (bit 4) plus a 3-bit select:
//!
//! | quantity | ch13 | select |
//! |---|---|---|
//! | `LRALT`   (LR altitude/range) | `0o17` | 7 |
//! | `LRVELZ`  | `0o16` | 6 |
//! | `LRVELY`  | `0o15` | 5 |
//! | `LRVELX`  | `0o14` | 4 |
//! | `RRRDOT`  | `0o12` | 2 |
//! | `RRRANGE` | `0o11` | 1 |
//!
//! `LRALT` and the RR quantities take ONE sample per reading
//! (`TC INITREAD -1`); the three LR velocity beams take five
//! (`LRVEL`, `:2759-2762`).
//!
//! The read sequence itself is `P20-P25.agc:2780-2801`: sample the
//! data-good bits (`DGBITS OCT 230` = bit 4 RR + bit 5 LR range + bit 8
//! LR velocity), `WAND` off all radar bits, `WOR` in the new select, and
//! wait for RADARUPT; `RADAREAD` (`:2812-2828`) then reads `RNRAD`.
//!
//! # The integration constraint — RADARUPT works, the DATA does not
//!
//! **Good news:** unlike the ROD channel, no vendor patch is needed for
//! the interrupt. yaAGC simulates RADARUPT natively
//! (`agc_engine.c:2223-2234`, added 2024-01-29): on radar-cycle
//! completion it clears ch13 bit 4, calls `RequestRadarData()`, and sets
//! `InterruptRequests[9]`.
//!
//! **The catch:** `RequestRadarData` is an EMPTY STUB —
//! `yaAGC/NullAPI.c:188-197`, "provided as a stub for integrators of
//! yaAGC into more complete simulations. It is expected to populate the
//! counter RNRAD with radar data", with the only line commented out. So
//! the interrupt fires on schedule and the AGC reads whatever `RNRAD`
//! happens to hold.
//!
//! `vendor/` is READ-ONLY, so the value has to arrive from outside.
//! `RNRAD` is at erasable 0o46 and AGC counters are driven by input
//! pulses over the same socket path the sim already uses for PIPA
//! (0o37-0o41) and THRUST (0o55) — the same no-patch pattern that solved
//! the ROD channel. **The timing is the real constraint:** `RNRAD` must
//! already hold the answer when the radar gate completes, so the sim has
//! to notice ch13 bit 4 going up and drive the counter within one radar
//! gate, rather than answering the interrupt afterwards.
//!
//! So the sim's side is: watch channel 13 for bit 4 with a select in
//! 1..=7, compute the corresponding beam from this module's geometry,
//! quantize it, drive `RNRAD` before the gate closes — then assert the
//! ch33 data-good bit for that quantity, remembering it is ACTIVE LOW.
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

/// Metres per LR altitude count, high scale.
///
/// `CONTROLLED_CONSTANTS.agc:168`:
/// `HSCAL  2DEC  -.3288792   # SCALES 1.079 FT/BIT TO 2(22)M.`
///
/// The comment names the quantum in feet and the constant is that same
/// quantum in metres: 1.079 ft x 0.3048 = 0.32887920 m, matching all
/// eight digits. `HSCAL` is negative because the AGC's slant range closes
/// as the vehicle descends; the magnitude is the quantum.
///
/// Low scale is selected by `ALTSCBIT` (`FLAGWORD_ASSIGNMENTS.agc:1147`,
/// `BIT9` of FLGWRD12), which is the flag counterpart of channel 33's
/// bit 9 "LR RANGE LOW SCALE", and rescaled through `SKALSKAL`
/// (`ERASABLE_ASSIGNMENTS.agc:813`, "LR ALT SCALE FACTOR RATIO: .2 NOM").
/// Only the high scale is pinned here; the low-scale path is not yet
/// verified and must not be guessed.
pub const LR_ALT_M_PER_COUNT: f64 = 0.328_879_2;

/// Quantize a slant range to LR altitude counts, high scale.
///
/// Truncation, not rounding: a counter accumulates whole pulses, and the
/// residual belongs to the caller so successive readings do not lose it —
/// the same carry-forward the PIPA model uses.
pub fn alt_counts(range_m: f64) -> i32 {
    (range_m / LR_ALT_M_PER_COUNT).trunc() as i32
}

/// Which quantity the AGC has selected on channel 13.
///
/// Bit 4 is RADAR ACTIVITY and bits 1-3 are the A,B,C select; the rope
/// writes activity+select together (`P20-P25.agc:2738-2755`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RadarSelect {
    LrAlt,
    LrVelX,
    LrVelY,
    LrVelZ,
    /// A rendezvous-radar quantity: the LR must not answer it.
    Rendezvous,
}

/// Channel 13's radar field: bit 4 activity, bits 1-3 select.
const CH13_ACTIVITY: u16 = 0o10;
const CH13_SELECT: u16 = 0o7;

/// Decode a channel-13 value into the selected quantity, or `None` when
/// no read is in progress.
///
/// `None` for a cleared activity bit is not an error: the rope clears all
/// radar bits with `CS ALLREAD / WAND CHAN13` before setting the new
/// select (`P20-P25.agc:2785-2792`), and yaAGC itself clears bit 4 when
/// the gate completes (`agc_engine.c:2232`).
pub fn decode_ch13(ch13: u16) -> Option<RadarSelect> {
    if ch13 & CH13_ACTIVITY == 0 {
        return None;
    }
    match ch13 & CH13_SELECT {
        7 => Some(RadarSelect::LrAlt),
        4 => Some(RadarSelect::LrVelX),
        5 => Some(RadarSelect::LrVelY),
        6 => Some(RadarSelect::LrVelZ),
        1 | 2 => Some(RadarSelect::Rendezvous),
        _ => None,
    }
}

/// Channel 33's data-good bits, **active low**.
///
/// `DGBITS OCT 230` (`P20-P25.agc:2803`) = bit 4 RR + bit 5 LR range +
/// bit 8 LR velocity. The rope reads them with `RAND CHAN33` and treats
/// ZERO as good, so "data is good" means the bit is CLEAR — see this
/// module's header for the `SERVICER.agc:749` proof.
pub const CH33_RR_DATA_GOOD: u16 = 0o10;
pub const CH33_LR_RANGE_DATA_GOOD: u16 = 0o20;
pub const CH33_LR_POS1: u16 = 0o40;
pub const CH33_LR_POS2: u16 = 0o100;
pub const CH33_LR_VEL_DATA_GOOD: u16 = 0o200;

/// Build the channel-33 word the LR should be presenting.
///
/// Every bit here is asserted by CLEARING it, so this starts from
/// all-set and clears what is true. Getting this backwards makes the
/// radar either invisible or permanently alarmed (`LRPOSALM`, 0522).
pub fn ch33_bits(range_good: bool, vel_good: bool, in_position_2: bool) -> u16 {
    let mut w = CH33_RR_DATA_GOOD
        | CH33_LR_RANGE_DATA_GOOD
        | CH33_LR_POS1
        | CH33_LR_POS2
        | CH33_LR_VEL_DATA_GOOD;
    if range_good {
        w &= !CH33_LR_RANGE_DATA_GOOD;
    }
    if vel_good {
        w &= !CH33_LR_VEL_DATA_GOOD;
    }
    if in_position_2 {
        w &= !CH33_LR_POS2;
    }
    w
}

/// Seeded landing-radar error model. `Default` (all zeros) means OFF.
///
/// Follows `ImuErrorCfg`'s contract exactly, and for the same reason: an
/// all-zero config returns the input untouched **without drawing from the
/// RNG**, so an acceptance run with errors off is deterministic and
/// RNG-free. A model that drew and discarded would make the acceptance
/// depend on the seed.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct LrErrorCfg {
    /// Range bias, metres. Constant offset on every altitude reading.
    pub range_bias_m: f64,
    /// Range scale-factor error, parts per million.
    pub range_scale_ppm: f64,
    /// Range white-noise standard deviation, metres.
    pub range_noise_sigma_m: f64,
    /// Probability in [0,1] that a reading drops out entirely — the
    /// radar's real failure mode over broken terrain, and the one the
    /// AGC's data-good discrete exists to signal.
    pub dropout_probability: f64,
    /// RNG seed (ChaCha8), for reproducible sequences.
    pub seed: u64,
}

impl LrErrorCfg {
    fn is_off(&self) -> bool {
        self.range_bias_m == 0.0
            && self.range_scale_ppm == 0.0
            && self.range_noise_sigma_m == 0.0
            && self.dropout_probability == 0.0
    }
}

/// Stateful LR error injector.
pub struct LrErrors {
    cfg: LrErrorCfg,
    off: bool,
    rng: rand_chacha::ChaCha8Rng,
}

impl LrErrors {
    pub fn new(cfg: LrErrorCfg) -> Self {
        use rand::SeedableRng;
        let off = cfg.is_off();
        let rng = rand_chacha::ChaCha8Rng::seed_from_u64(cfg.seed);
        Self { cfg, off, rng }
    }

    /// Corrupt one altitude reading. `None` is a dropout, which the caller
    /// must turn into "data NOT good" rather than into a zero range —
    /// a zero would read as "on the surface".
    pub fn corrupt_range(&mut self, range_m: f64) -> Option<f64> {
        use rand::Rng;
        if self.off {
            return Some(range_m);
        }
        if self.cfg.dropout_probability > 0.0
            && self.rng.gen::<f64>() < self.cfg.dropout_probability
        {
            return None;
        }
        let noise = if self.cfg.range_noise_sigma_m > 0.0 {
            // Box-Muller, so the sigma means what it says.
            let (u1, u2): (f64, f64) = (self.rng.gen(), self.rng.gen());
            let u1 = u1.max(1e-12);
            self.cfg.range_noise_sigma_m
                * (-2.0 * u1.ln()).sqrt()
                * (std::f64::consts::TAU * u2).cos()
        } else {
            0.0
        };
        Some(range_m * (1.0 + self.cfg.range_scale_ppm * 1e-6) + self.cfg.range_bias_m + noise)
    }
}

/// LR antenna orientation, per position: (alpha about X, beta about Y),
/// degrees.
///
/// `SERVICER.agc:1685-1720` (`SETPOS`/`SETPOS2`) loads `LRALPHA`/`LRBETA`
/// into `CDUSPOT` as rotations about X and Y (Z is zeroed), builds the
/// antenna-to-navigation-base transform, and derives the beams:
/// `VYBEAMNB = UNITY(antenna)`, `VXBEAMNB = UNITX(antenna)`,
/// `VZBEAMNB = X x Y`, and the altitude beam from `HBEAMANT`.
///
/// Values from the flown reference pad load
/// (`vendor/virtualagc/LUM69R2/PADLOADS.agc:542-559`), whose comments
/// give both the octal word and the intended angle:
///
/// | word | octal | angle |
/// |---|---|---|
/// | `LRALPHA`  (pos 1, X) | `01042` | 6° |
/// | `LRBETA1`  (pos 1, Y) | `04210` | 24° |
/// | `LRALPHA2` (pos 2, X) | `01042` | 6° |
/// | `LRBETA2`  (pos 2, Y) | `00000` | 0° |
///
/// **These are not in this project's pad load.** `scenarios/p66-padload.toml`
/// omits the `LRALPHA..LRWVFF` block deliberately, because every flight so
/// far has run `lrbypass = true`. Enabling the radar means pad-loading
/// them first — the velocity beams cannot be built without them.
pub const LR_ANTENNA_POS1_DEG: (f64, f64) = (6.0, 24.0);
pub const LR_ANTENNA_POS2_DEG: (f64, f64) = (6.0, 0.0);

/// Decode a pad-loaded LR antenna angle: the word is a fraction of a
/// half-revolution, so `degrees = word / 2^14 * 180`.
///
/// Verified against the reference pad load's own comments — `01042`
/// decodes to 5.999° against a documented 6°, and `04210` to 23.99°
/// against 24°.
pub fn antenna_angle_deg(word: u16) -> f64 {
    f64::from(word) / 16384.0 * 180.0
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
    fn the_altitude_quantum_is_the_ropes_own_1_079_ft() {
        // HSCAL's comment gives the quantum in feet and its value gives
        // the same quantum in metres; they must agree, or the constant
        // has been transcribed rather than derived.
        let from_feet = 1.079 * 0.3048;
        assert!(
            (LR_ALT_M_PER_COUNT - from_feet).abs() < 1e-9,
            "{LR_ALT_M_PER_COUNT} vs {from_feet}"
        );
    }

    #[test]
    fn altitude_counts_round_trip_at_descent_altitudes() {
        for h in [15_000.0, 3_000.0, 250.0, 40.0, 3.0] {
            let n = alt_counts(h);
            let back = f64::from(n) * LR_ALT_M_PER_COUNT;
            assert!(
                (h - back) < LR_ALT_M_PER_COUNT && h - back >= 0.0,
                "h={h} -> {n} counts -> {back}"
            );
        }
    }

    #[test]
    fn altitude_counts_truncate_rather_than_round() {
        // A counter carries whole pulses; the residual is the caller's,
        // so half a quantum must not become a whole one.
        assert_eq!(alt_counts(LR_ALT_M_PER_COUNT * 1.9), 1);
        assert_eq!(alt_counts(LR_ALT_M_PER_COUNT * 0.9), 0);
    }

    #[test]
    fn ch13_decodes_the_ropes_own_select_codes() {
        // The exact octals the lead-in routines write (P20-P25.agc:2739-2755).
        assert_eq!(decode_ch13(0o17), Some(RadarSelect::LrAlt));
        assert_eq!(decode_ch13(0o16), Some(RadarSelect::LrVelZ));
        assert_eq!(decode_ch13(0o15), Some(RadarSelect::LrVelY));
        assert_eq!(decode_ch13(0o14), Some(RadarSelect::LrVelX));
        assert_eq!(decode_ch13(0o12), Some(RadarSelect::Rendezvous));
        assert_eq!(decode_ch13(0o11), Some(RadarSelect::Rendezvous));
    }

    #[test]
    fn ch13_without_the_activity_bit_is_not_a_read() {
        // The rope clears all radar bits before setting a new select, and
        // yaAGC clears bit 4 when the gate completes. Neither is an error.
        for sel in 0..8u16 {
            assert_eq!(decode_ch13(sel), None, "select {sel} without activity");
        }
        // Unrelated channel-13 traffic must not look like a radar read.
        assert_eq!(decode_ch13(0o400), None); // RHC counter enable, bit 8
    }

    #[test]
    fn data_good_is_asserted_by_clearing_the_bit() {
        // The trap this module exists to document. "Good" is a ZERO bit.
        let good = ch33_bits(true, true, true);
        assert_eq!(good & CH33_LR_RANGE_DATA_GOOD, 0, "range good => bit clear");
        assert_eq!(good & CH33_LR_VEL_DATA_GOOD, 0, "vel good => bit clear");
        assert_eq!(good & CH33_LR_POS2, 0, "in position 2 => bit clear");

        let bad = ch33_bits(false, false, false);
        assert_ne!(bad & CH33_LR_RANGE_DATA_GOOD, 0);
        assert_ne!(bad & CH33_LR_VEL_DATA_GOOD, 0);
        assert_ne!(bad & CH33_LR_POS2, 0);
    }

    #[test]
    fn the_rope_sees_our_bits_the_way_servicer_tests_them() {
        // SERVICER.agc:749  CAF BIT7 / RAND CHAN33 / BZF UPDATCHK
        // i.e. "in position 2" iff (ch33 & BIT7) == 0.
        let in_pos2 = ch33_bits(true, true, true);
        assert_eq!(in_pos2 & 0o100, 0, "BZF would branch: LR is in POS2");
        let not_pos2 = ch33_bits(true, true, false);
        assert_ne!(not_pos2 & 0o100, 0, "BZF would not branch: LRPOSALM");
        // And DGBITS masks exactly the three data-good bits.
        assert_eq!(
            CH33_RR_DATA_GOOD | CH33_LR_RANGE_DATA_GOOD | CH33_LR_VEL_DATA_GOOD,
            0o230,
            "DGBITS (P20-P25.agc:2803)"
        );
    }

    #[test]
    fn errors_off_is_identity_and_never_touches_the_rng() {
        // The acceptance runs with errors off and must not depend on the
        // seed. Two injectors with DIFFERENT seeds must agree exactly.
        let mut a = LrErrors::new(LrErrorCfg {
            seed: 1,
            ..Default::default()
        });
        let mut b = LrErrors::new(LrErrorCfg {
            seed: 999,
            ..Default::default()
        });
        for h in [15_000.0, 250.0, 3.0] {
            assert_eq!(a.corrupt_range(h), Some(h));
            assert_eq!(a.corrupt_range(h), b.corrupt_range(h));
        }
    }

    #[test]
    fn a_dropout_is_none_not_a_zero_range() {
        // A zero would read as "on the surface" and fly the vehicle into
        // the ground; the caller must turn None into data-NOT-good.
        let mut e = LrErrors::new(LrErrorCfg {
            dropout_probability: 1.0,
            seed: 7,
            ..Default::default()
        });
        assert_eq!(e.corrupt_range(1000.0), None);
    }

    #[test]
    fn bias_and_scale_apply_as_documented() {
        let mut e = LrErrors::new(LrErrorCfg {
            range_bias_m: 5.0,
            range_scale_ppm: 1000.0, // 0.1 %
            seed: 3,
            ..Default::default()
        });
        let got = e.corrupt_range(1000.0).unwrap();
        assert!((got - (1000.0 * 1.001 + 5.0)).abs() < 1e-9, "{got}");
    }

    #[test]
    fn the_same_seed_reproduces_the_same_sequence() {
        let cfg = LrErrorCfg {
            range_noise_sigma_m: 2.0,
            seed: 42,
            ..Default::default()
        };
        let mut a = LrErrors::new(cfg.clone());
        let mut b = LrErrors::new(cfg);
        for _ in 0..20 {
            assert_eq!(a.corrupt_range(500.0), b.corrupt_range(500.0));
        }
    }

    #[test]
    fn the_antenna_angles_decode_to_the_pad_loads_documented_degrees() {
        // Same "derived, not transcribed" check as the altitude quantum:
        // the reference pad load gives both the octal and the angle, and
        // they must agree, or the scaling is wrong.
        assert!(
            (antenna_angle_deg(0o01042) - 6.0).abs() < 0.01,
            "{}",
            antenna_angle_deg(0o01042)
        );
        assert!(
            (antenna_angle_deg(0o04210) - 24.0).abs() < 0.01,
            "{}",
            antenna_angle_deg(0o04210)
        );
        assert_eq!(antenna_angle_deg(0o00000), 0.0);
        // And the constants match what those words decode to.
        assert!((LR_ANTENNA_POS1_DEG.0 - antenna_angle_deg(0o01042)).abs() < 0.01);
        assert!((LR_ANTENNA_POS1_DEG.1 - antenna_angle_deg(0o04210)).abs() < 0.01);
        assert_eq!(LR_ANTENNA_POS2_DEG.1, 0.0);
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
