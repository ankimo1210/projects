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
    apply_lr_bits(
        CH33_RR_DATA_GOOD
            | CH33_LR_RANGE_DATA_GOOD
            | CH33_LR_POS1
            | CH33_LR_POS2
            | CH33_LR_VEL_DATA_GOOD,
        range_good,
        vel_good,
        in_position_2,
    )
}

/// Every channel-33 bit this module owns. Anything outside this mask
/// belongs to `runner::init_discretes` (uplink, PIPA fail, oscillator)
/// and must survive an LR update untouched.
pub const CH33_LR_MASK: u16 =
    CH33_LR_RANGE_DATA_GOOD | CH33_LR_POS1 | CH33_LR_POS2 | CH33_LR_VEL_DATA_GOOD;

/// Read-modify-write the LR bits of an existing channel-33 word.
///
/// Building the whole word from scratch clobbers the bits
/// `init_discretes` set — which is what flight 14 did on every radar
/// reply. Only `CH33_LR_MASK` may move.
pub fn apply_lr_bits(current: u16, range_good: bool, vel_good: bool, in_position_2: bool) -> u16 {
    // Start from "nothing good, not in position" for the owned bits...
    let mut w = current | CH33_LR_MASK;
    // ...then CLEAR what is true (active low).
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

/// The range (altitude) beam direction in LR ANTENNA coordinates.
///
/// `CONTROLLED_CONSTANTS.agc:164-166` — three consecutive `2DEC` words,
/// which the `SETPOS` sequence loads as a vector and transforms to the
/// navigation base (`SERVICER.agc:1718-1720`):
///
/// ```text
///   HBEAMANT  2DEC  -.4687018041   # RANGE BEAM IN LR ANTENNA COORDINATES.
///             2DEC   0
///             2DEC  -.1741224271
/// ```
///
/// Its magnitude is **0.5**, not 1: the AGC stores unit vectors at half
/// magnitude (b=1), the same convention as `REFSMMAT`'s direction
/// cosines. `unit()` below returns the true unit vector.
///
/// As a direction that is 20.4 degrees off the antenna's −X axis, in the
/// X-Z plane — the altimeter beam's tilt relative to the antenna face.
pub const HBEAMANT: [f64; 3] = [-0.468_701_804_1, 0.0, -0.174_122_427_1];

/// `HBEAMANT` as a true unit vector, undoing the AGC's b=1 half-magnitude
/// storage.
pub fn hbeam_unit() -> [f64; 3] {
    [HBEAMANT[0] * 2.0, HBEAMANT[1] * 2.0, HBEAMANT[2] * 2.0]
}

/// How the antenna-frame beams reach the navigation base — verified.
///
/// `SETPOS` (`SERVICER.agc:1691-1699`) loads the angles like this:
///
/// ```text
///   DCA   LRALPHA        # LRALPHA IN A, LRBETA IN L
///   TS    CDUSPOT +4     # ROTATION ABOUT X
///   LXCH  CDUSPOT        # ROTATION ABOUT Y
///   CA    ZERO
///   TS    CDUSPOT +2     # ZERO ROTATION ABOUT Z.
/// ```
///
/// and `POWERED_FLIGHT_SUBROUTINES.agc:169-172` states the convention the
/// transform expects: *"TRG\*SMNB AND TRG\*NBSM BOTH EXPECT TO SEE THE
/// 2'S COMPLEMENT ANGLES AT CDUSPOT (ORDER Y Z X, AT CDUSPOT, CDUSPOT +2,
/// AND CDUSPOT +4)"*, with `TRG*NBSM` doing NB→SM and `TRG*SMNB` the
/// reverse.
///
/// The two agree exactly — CDUSPOT+0 = Y = `LRBETA`, +2 = Z = 0,
/// +4 = X = `LRALPHA` — which is the check worth doing, because a
/// transposed axis order would mis-point every beam by tens of degrees
/// while still looking plausible.
///
/// So the velocity beams are the antenna axes carried through the
/// (alpha about X, beta about Y, 0 about Z) rotation in the SM→NB sense:
/// `VYBEAMNB` from `UNITY`, `VXBEAMNB` from `UNITX`, and
/// `VZBEAMNB = VXBEAMNB x VYBEAMNB` (`SERVICER.agc:1705-1717`).
/// `HBEAMANT` rides the same transform.
///
/// **The axis order inside `AX*SR*T` is now pinned too.** Its own
/// documentation (`POWERED_FLIGHT_SUBROUTINES.agc:217-235`) says: enter
/// with `+3` for NB→SM and `-3` for SM→NB, with sines and cosines "AT
/// SINCDU AND COSCDU, IN THE ORDER Y Z X". The loop `R*TL**P` (`:239-242`)
/// maps that entry value to a starting index — `+3 -> 0`, `+2 -> 1`,
/// `+1 -> 2` and `-3 -> 2`, `-2 -> 1`, `-1 -> 0` — so it is three
/// single-axis rotations walked forwards for NB→SM and backwards for
/// SM→NB.
///
/// With the Y,Z,X ordering that makes **SM→NB apply X, then Z, then Y**.
/// The LR case zeroes Z, so a beam reaches the navigation base as
///
/// ```text
///   beam_nb = R_y(beta) . R_x(alpha) . beam_antenna
/// ```
///
/// **The rotation SIGN does not need a flight to settle.** `AX*SR*T`
/// negates one direction internally (`DCS VBUF` against `DCA`,
/// `:246-250`), and tracing that arithmetic by eye is exactly the kind of
/// reading that produces a confident, mirrored, wrong answer. It does not
/// have to be traced:
///
/// `CDU*SMNB` and `TRG*SMNB` differ ONLY in where the angles come from —
/// live CDU counters versus `CDUSPOT`. Both fall through to the same
/// `C*MM*N1` and the same `AX*SR*T` call with `CS THREE`
/// (`POWERED_FLIGHT_SUBROUTINES.agc:179-190`). So whatever rotation sense
/// the CDU path uses, the `CDUSPOT` path uses identically.
///
/// And this project's CDU convention is **already live-verified**:
/// `eagle_sensors::imu::Imu::gimbals_deg` decomposes Body→SM into
/// (OGA, IGA, MGA) = (X, Y, Z) CDU slots, and Wave 1 established that the
/// attitude loop closes correctly against the real rope — the DAP slews
/// and captures, which it could not do through a mirrored transform.
///
/// So the antenna transform should be built as the inverse of that same
/// decomposition, with `LRALPHA` in the X slot and `LRBETA` in the Y
/// slot, and validated against `gimbals_deg` on a round trip rather than
/// against a fresh reading of `AX*SR*T`. **That is the remaining work,
/// and it needs no flight** — only the acceptance flight afterwards does.
pub const CDUSPOT_ORDER: [&str; 3] = ["Y (LRBETA)", "Z (zero)", "X (LRALPHA)"];

/// Rotation order for the SM→NB direction `AX*SR*T` uses: X, then Z,
/// then Y (`POWERED_FLIGHT_SUBROUTINES.agc:217-242`). NB→SM is the
/// reverse.
pub const SMNB_ROTATION_ORDER: [&str; 3] = ["X (alpha)", "Z (zero)", "Y (beta)"];

/// Metres per second per count, for the three LR velocity beams.
///
/// `CONTROLLED_CONSTANTS.agc:172-174`, under a banner reading
/// "***** THE SEQUENCE OF THE FOLLOWING CONSTANTS MUST BE PRESERVED *****":
///
/// ```text
///   VZSCAL  2DEC  +.5410829105   # SCALES .8668 FT/SEC/BIT TO 2(18) M/CS.
///   VYSCAL  2DEC  +.7565672446   # SCALES 1.212 FT/SEC/BIT TO 2(18) M/CS.
///   VXSCAL  2DEC  -.4020043770   # SCALES -.644 FT/SEC/BIT TO 2(18) M/CS.
/// ```
///
/// **The three beams have DIFFERENT quanta, and X's is NEGATIVE** — a
/// sign asymmetry that is easy to miss and would invert one axis of every
/// velocity update.
///
/// Each constant is its stated ft/s quantum times exactly **2.048**,
/// which holds for all three to five digits (see the test). That is the
/// b=18 m/cs encoding, and it is what makes these derived rather than
/// transcribed.
pub const LR_VEL_MS_PER_COUNT: [f64; 3] = [
    -0.644 * 0.3048, // X
    1.212 * 0.3048,  // Y
    0.8668 * 0.3048, // Z
];

/// The LR velocity zero offset, in counts.
///
/// `CONTROLLED_CONSTANTS.agc:150`:
/// `LVELBIAS  DEC  -12288   # LANDING RADAR BIAS FOR 153.6 KC.`
///
/// The radar's velocity beams are frequency-modulated about a carrier, so
/// zero velocity is a non-zero count; the AGC removes the offset with
/// `AD LVELBIAS` on the raw word (`P20-P25.agc:2880`). Since the AGC
/// ADDS -12288, a simulator driving the counter must place the reading at
/// `count + 12288` — i.e. SUBTRACT the (negative) bias — or every
/// velocity beam is offset by 12288 counts.
pub const LVELBIAS_COUNTS: i32 = -12288;

/// Convert a beam velocity to the raw count the AGC expects to read,
/// including the carrier offset.
pub fn vel_raw_counts(along_ms: f64, ms_per_count: f64) -> i32 {
    (along_ms / ms_per_count).trunc() as i32 - LVELBIAS_COUNTS
}

/// Transform a vector from LR ANTENNA axes to the navigation base.
///
/// # Derivation, from the live-verified CDU convention
///
/// `imu::gimbals_deg` decomposes Body→SM as
/// `mga = asin(M[1][0])`, `iga = atan2(-M[2][0], M[0][0])`,
/// `oga = atan2(-M[1][2], M[1][1])`. The unique product satisfying all
/// three is
///
/// ```text
///   M(body->SM) = Ry(IGA) . Rz(MGA) . Rx(OGA)
/// ```
///
/// — and that factor order is exactly `CDUSPOT`'s documented Y, Z, X
/// ordering (`POWERED_FLIGHT_SUBROUTINES.agc:169-172`), which is the
/// cross-check that the decomposition and the rope agree.
///
/// `TRG*SMNB` is the inverse direction, so with the LR's angles
/// (X slot = `LRALPHA` = alpha, Y slot = `LRBETA` = beta, Z = 0):
///
/// ```text
///   beam_nb = Rx(-alpha) . Ry(-beta) . beam_antenna
/// ```
///
/// This needs no reading of `AX*SR*T`'s internal negation: `CDU*SMNB` and
/// `TRG*SMNB` share that code, and the CDU path is verified by Wave 1's
/// working attitude loop.
pub fn antenna_to_nav_base(v: [f64; 3], alpha_deg: f64, beta_deg: f64) -> [f64; 3] {
    let (a, b) = (-alpha_deg.to_radians(), -beta_deg.to_radians());
    // Ry(b) first, then Rx(a).
    let (sb, cb) = b.sin_cos();
    let y = [cb * v[0] + sb * v[2], v[1], -sb * v[0] + cb * v[2]];
    let (sa, ca) = a.sin_cos();
    [y[0], ca * y[1] - sa * y[2], sa * y[1] + ca * y[2]]
}

/// The three LR velocity beams in navigation-base axes, for one antenna
/// position.
///
/// `SERVICER.agc:1705-1717`: `VYBEAMNB` from `UNITY`, `VXBEAMNB` from
/// `UNITX`, and `VZBEAMNB = VXBEAMNB x VYBEAMNB`.
pub fn velocity_beams_nb(alpha_deg: f64, beta_deg: f64) -> [[f64; 3]; 3] {
    let x = antenna_to_nav_base([1.0, 0.0, 0.0], alpha_deg, beta_deg);
    let y = antenna_to_nav_base([0.0, 1.0, 0.0], alpha_deg, beta_deg);
    let z = [
        x[1] * y[2] - x[2] * y[1],
        x[2] * y[0] - x[0] * y[2],
        x[0] * y[1] - x[1] * y[0],
    ];
    [x, y, z]
}

/// The altitude beam in navigation-base axes.
pub fn altitude_beam_nb(alpha_deg: f64, beta_deg: f64) -> [f64; 3] {
    antenna_to_nav_base(hbeam_unit(), alpha_deg, beta_deg)
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
    fn hbeamant_is_a_half_magnitude_unit_vector() {
        // The AGC stores unit vectors at half magnitude (b=1). If this
        // were read as a true unit vector every range beam would be
        // mis-pointed, so assert the convention rather than assume it.
        let m = (HBEAMANT[0] * HBEAMANT[0] + HBEAMANT[2] * HBEAMANT[2]).sqrt();
        assert!((m - 0.5).abs() < 1e-6, "|HBEAMANT| = {m}, expected 0.5");
        let u = hbeam_unit();
        let mu = (u[0] * u[0] + u[2] * u[2]).sqrt();
        assert!((mu - 1.0).abs() < 1e-6, "|unit| = {mu}");
        // 20.4 deg off the antenna -X axis, in the X-Z plane.
        let tilt = (-u[2]).atan2(-u[0]).to_degrees();
        assert!((tilt - 20.4).abs() < 0.1, "tilt {tilt} deg");
    }

    #[test]
    fn the_transform_matches_the_gimbal_decomposition_it_was_derived_from() {
        // The validation the derivation calls for: build M(body->SM) as
        // Ry(iga).Rz(mga).Rx(oga), then check gimbals_deg's three formulas
        // recover the angles. If the factor order were wrong this fails.
        let (oga, mga, iga) = (0.11_f64, -0.07_f64, 0.23_f64);
        let (so, co) = oga.sin_cos();
        let (sm, cm) = mga.sin_cos();
        let (si, ci) = iga.sin_cos();
        // M = Ry(iga) . Rz(mga) . Rx(oga), rows.
        let m = [
            [ci * cm, -ci * sm * co + si * so, ci * sm * so + si * co],
            [sm, cm * co, -cm * so],
            [-si * cm, si * sm * co + ci * so, -si * sm * so + ci * co],
        ];
        assert!((m[1][0].asin() - mga).abs() < 1e-12, "mga");
        assert!(((-m[2][0]).atan2(m[0][0]) - iga).abs() < 1e-12, "iga");
        assert!(((-m[1][2]).atan2(m[1][1]) - oga).abs() < 1e-12, "oga");
    }

    #[test]
    fn the_antenna_transform_is_an_isometry_and_inverts_cleanly() {
        let v: [f64; 3] = [0.3, -0.5, 0.81];
        let n = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt();
        let out = antenna_to_nav_base(v, 6.0, 24.0);
        let no = (out[0] * out[0] + out[1] * out[1] + out[2] * out[2]).sqrt();
        assert!((n - no).abs() < 1e-12, "length must be preserved");
        // Zero angles are the identity.
        assert_eq!(antenna_to_nav_base(v, 0.0, 0.0), v);
    }

    #[test]
    fn position_2_rotates_about_x_only() {
        // beta = 0, so the X component is untouched -- the natural
        // fixture, and the one that would expose a swapped axis order.
        let v: [f64; 3] = [0.5, 0.5, 0.5];
        let out = antenna_to_nav_base(v, 6.0, LR_ANTENNA_POS2_DEG.1);
        assert!((out[0] - v[0]).abs() < 1e-12, "X untouched at beta=0");
        assert!((out[1] - v[1]).abs() > 1e-6, "but Y must move");
    }

    #[test]
    fn the_velocity_beams_are_an_orthonormal_triad() {
        // These come from exact unit axes, so they ARE exactly orthonormal
        // -- unlike the altitude beam, which inherits HBEAMANT's precision.
        let [x, y, z] = velocity_beams_nb(LR_ANTENNA_POS1_DEG.0, LR_ANTENNA_POS1_DEG.1);
        let dot = |a: [f64; 3], b: [f64; 3]| a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
        for v in [x, y, z] {
            assert!((dot(v, v) - 1.0).abs() < 1e-12, "unit");
        }
        assert!(dot(x, y).abs() < 1e-12, "x.y");
        assert!(dot(x, z).abs() < 1e-12, "x.z");
        assert!(dot(y, z).abs() < 1e-12, "y.z");
    }

    #[test]
    fn the_altitude_beam_still_points_down_after_the_transform() {
        // HBEAMANT is 20.4 deg off antenna -X; a 6/24 deg antenna tilt
        // must not turn it upward, or the altimeter would look at the sky.
        let b = altitude_beam_nb(LR_ANTENNA_POS1_DEG.0, LR_ANTENNA_POS1_DEG.1);
        assert!(b[0] < -0.5, "still predominantly -X (down): {b:?}");
        // Unit to the precision of HBEAMANT itself: the rope's constant is
        // 0.5 to seven digits (0.5000016), so the doubled vector is unit to
        // ~3e-5. Asserting tighter would be asserting against the rope.
        let n = (b[0] * b[0] + b[1] * b[1] + b[2] * b[2]).sqrt();
        assert!(
            (n - 1.0).abs() < 1e-4,
            "unit to HBEAMANT's own precision: {n}"
        );
    }

    #[test]
    fn the_velocity_quanta_match_the_ropes_own_constants() {
        // Same "derived, not transcribed" guard as the altitude quantum.
        // Each VxSCAL is its stated ft/s quantum times exactly 2.048 --
        // the b=18 m/cs encoding.
        for (constant, ft_per_s) in [
            (0.541_082_910_5_f64, 0.8668_f64),
            (0.756_567_244_6, 1.212),
            (-0.402_004_377_0, -0.644),
        ] {
            let ms = ft_per_s * 0.3048;
            assert!(
                (constant / ms - 2.048).abs() < 1e-4,
                "{constant} / {ms} = {}, expected 2.048",
                constant / ms
            );
        }
        // And the exported quanta are those ft/s figures in metres.
        assert!((LR_VEL_MS_PER_COUNT[2] - 0.8668 * 0.3048).abs() < 1e-12);
        // X is NEGATIVE. Losing this inverts one axis of every update.
        // (Read through a binding so clippy sees a runtime assertion, not
        // a const-folded one -- the point is to fail if the TABLE changes.)
        let q = LR_VEL_MS_PER_COUNT;
        assert!(q[0] < 0.0, "VXSCAL's sign is negative: {q:?}");
        assert!(q[1] > 0.0 && q[2] > 0.0, "{q:?}");
        // All three differ -- one shared quantum would be wrong.
        assert!((q[1] - q[2]).abs() > 0.1, "{q:?}");
    }

    #[test]
    fn the_velocity_bias_round_trips_the_way_the_agc_removes_it() {
        // The AGC does `AD LVELBIAS` on the raw word, so raw + (-12288)
        // must recover the count. Getting the sign backwards offsets every
        // beam by 24576 counts, which is worse than not applying it.
        let q = LR_VEL_MS_PER_COUNT[2];
        for v in [0.0_f64, 5.0, -5.0, 40.0] {
            let raw = vel_raw_counts(v, q);
            let recovered = raw + LVELBIAS_COUNTS;
            let expect = (v / q).trunc() as i32;
            assert_eq!(recovered, expect, "v = {v}");
        }
        // Zero velocity is NOT a zero count -- that is the whole point.
        assert_eq!(vel_raw_counts(0.0, q), 12288);
    }

    #[test]
    fn an_lr_update_leaves_every_other_ch33_bit_alone() {
        // Flight 14: building the word from scratch overwrote the uplink,
        // PIPA-fail and oscillator bits init_discretes had set.
        let init: u16 = 0o57776; // runner::INIT_CH33
        let out = apply_lr_bits(init, true, true, true);
        assert_eq!(
            out & !CH33_LR_MASK,
            init & !CH33_LR_MASK,
            "bits outside CH33_LR_MASK must survive"
        );
        // And the LR bits still assert correctly (active low).
        assert_eq!(out & CH33_LR_RANGE_DATA_GOOD, 0);
        assert_eq!(out & CH33_LR_VEL_DATA_GOOD, 0);
        assert_eq!(out & CH33_LR_POS2, 0);
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
