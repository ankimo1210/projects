//! Physical and simulator-calibration constants (spec §3 plan-header table).
//! Every constant carries its provenance: historical (measured astrodynamic
//! quantity), derived (computed from another sourced quantity), assumed
//! (engineering estimate pending calibration), or a direct LM_Simulator
//! citation (file:line in the reference Tcl implementation).

/// Lunar gravitational parameter, m^3/s^2. Provenance: historical.
pub const MU_MOON: f64 = 4.9028e12;
/// Landing-site radius, m. Provenance: assumed (mean lunar radius).
pub const R_SITE: f64 = 1_737_400.0;
/// Lunar sidereal rotation rate, rad/s. Provenance: historical.
pub const OMEGA_MOON: f64 = 2.6617e-6;
/// PIPA ΔV per pulse, m/s. Provenance: **the rope's own decode constant**,
/// cross-checked against a live descent.
///
/// This is not a free physical choice — it is the number Luminary099 uses
/// to turn the PIPA counters back into velocity, so the sim must emit
/// pulses in exactly these units or the AGC's navigation silently
/// integrates the wrong ΔV.
///
/// Derivation (`vendor/virtualagc/Luminary099/`):
/// * `SERVICER.agc:570-580` (PIPASR's REPIP1/REPIP3) reads the PIPAX/Y/Z counters and
///   stores each raw count into the HIGH word of `DELVX/Y/Z`, so `DELV`
///   as a DP fraction is `count · 2⁻¹⁴` — the same "(PIPA PULSES) X
///   2(+14)" scaling the compensation package states at
///   `IMU_COMPENSATION_PACKAGE.agc:55-65`.
/// * `CONTROLLED_CONSTANTS.agc:178-180` then converts it:
///   `KPIP = .0512` ("SCALES DELV TO UNITS OF 2(5) M/CS"),
///   `KPIP1 = .0128` (2(7) M/CS), `KPIP2 = .0064` (2(8) M/CS).
///   All three give the same physical value —
///   `count · 2⁻¹⁴ · 0.0128 · 2⁷ = count · 1.0e-4 m/cs` —
///   i.e. **1 pulse = 1 cm/s**.
///
/// Measured confirmation (2026-07-26 M1 flight 1,
/// `docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`): with the old
/// 0.0585 value the AGC's own V06N63 R2 altitude rate tracked a model in
/// which it integrated only k = 0.159 of the delivered ΔV over a 198 s
/// powered descent (rms 0.46 m/s over ~1900 samples, against rms 92.9 m/s
/// for k = 1). 1 cm/s ÷ 5.85 cm/s = 0.171.
///
/// The superseded provenance was LM_Simulator's `lm_simulator.tcl:145`
/// (`set PIPA_INCR 0.0585`, metres — its `AGC_IMU.tcl:293-297` displays
/// the same integrated velocity raw and again times `MeterToFeet`). That
/// contributed Tcl demo drives a DSKY, never a closed navigation loop, and
/// on this point it disagrees with the rope it is talking to. The rope
/// wins.
pub const PIPA_INCR: f64 = 0.01;
/// CDU angle per pulse, degrees. Provenance: lm_simulator.tcl:141-142.
pub const CDU_INCR_DEG: f64 = 360.0 / 32768.0;
/// IMU coarse-align pulse, degrees. Provenance: lm_simulator.tcl:143.
pub const COARSE_INCR_DEG: f64 = 0.043948;
/// Gyro fine-align pulse, degrees. Provenance: lm_simulator.tcl:144.
pub const GYRO_FINE_INCR_DEG: f64 = 0.617981 / 3600.0;
/// DPS full-throttle (saturation) thrust, N. Provenance: **the flown
/// rope's own throttle constants, in SI, on one line**.
///
/// `vendor/virtualagc/Luminary099/CONTROLLED_CONSTANTS.agc:132` —
/// `FMAXODD DEC +3841   # FSAT +4.81454413 E+4`. `THROTTLE_CONTROL_
/// ROUTINES.agc:114-118` (NOTE 2) says what that bit count is in as many
/// words: *"the NUMBER OF BITS CORRESPONDING TO FULL THROTTLE
/// (FMAXODD)"*. So full throttle = **48 145.4 N**.
///
/// The counter is deliberately driven PAST it: `FLATOUT` and the
/// throttle-up branch both load `FEXTRA = BIT13 = 4096` bits
/// (`THROTTLE_CONTROL_ROUTINES.agc:107,226`, commented
/// `# FEXT +5.13309020 E+4`), i.e. 51 330.9 N of command against a
/// 48 145.4 N stop — the same drive-past-the-stop idiom Luminary uses at
/// the zero end. `dps_envelope` models the stop, so the extra 255 bits do
/// nothing, which is correct.
///
/// The rope's third force constant is NOT this one:
/// `CONTROLLED_CONSTANTS.agc:133`, `FMAXPOS DEC +3467  # FMAX
/// +4.34546769 E+4`, is what the AGC writes into FCODD as its own
/// bookkeeping estimate after a throttle-up
/// (`THROTTLE_CONTROL_ROUTINES.agc:105-106`) — 90.3 % of FSAT. It is the
/// AGC's belief about the thrust, not the thrust; the PIPAs correct it.
/// Modelling it as the delivered thrust would under-power the vehicle by
/// 9.7 %.
///
/// Supersedes two earlier provenances, both wrong for this rope:
/// LM_Simulator's `lm_simulator.tcl:186` (45 040 N), and — 2026-07-26,
/// review round 1 — 46 706 N derived from `LUM69R2/PADLOADS.agc:501-511`'s
/// "57 %/63 % NOMINAL MAX THRUST" annotation at *that* rope's 2.7 lbs/bit.
/// LUM69R2 and Luminary099 have different `SCALEFAC`s (12.0325 vs
/// 12.5320 N/bit, 4.16 % apart), so mixing LUM69R2's bit scale with
/// Luminary099's criteria mis-scaled the answer. Against FSAT the same
/// criteria land where they should: LOWCRIT 2217 bits = 57.7 % of 3841,
/// HIGHCRIT 2450 bits = 63.8 %.
///
/// Measured live (2026-07-26 M1): at 42 500 N the braking phase reached
/// HIGATE at 4052 m / 435 m/s against a 2924 m / 172 m/s target; at
/// 46 706 N, 3832 m / 218 m/s. See
/// `docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`.
pub const DPS_MAX_N: f64 = 48145.4413;
/// DPS minimum throttle thrust, N. Provenance: lm_simulator.tcl:187.
pub const DPS_MIN_N: f64 = 4560.0;
/// Fixed throttle point: commands above 60 % snap here. Luminary's own
/// throttle law never *rests* between LOWCRIT and HIGHCRIT — it goes
/// either back into the throttleable region or to full throttle
/// (`THROTTLE_CONTROL_ROUTINES.agc:88-107`) — and full throttle is FSAT,
/// so this is `DPS_MAX_N`, not a lower fixed point.
pub const DPS_FTP_N: f64 = DPS_MAX_N;
/// DPS effective exhaust velocity, m/s. Provenance: lm_simulator.tcl:188.
pub const DPS_VE: f64 = 3050.0;
/// DPS first-order throttle lag, s. Provenance: **the rope's own engine
/// response lag** — `vendor/virtualagc/Luminary099/
/// CONTROLLED_CONSTANTS.agc:134`, `THROTLAG DEC +20  # TAU (TH)
/// +1.99999999 E-1`, i.e. 20 centiseconds. This is not decoration: the AGC
/// actively compensates its thrust estimate for it
/// (`THROTTLE_CONTROL_ROUTINES.agc:172`, `AD THROTLAG  # COMPENSATE FOR
/// ENGINE RESPONSE LAG`), so a plant slower than THROTLAG is a plant the
/// compensator is systematically wrong about. Was `assumed = 0.3` — 50 %
/// slower than the AGC assumes, i.e. a standing phase-margin loss in every
/// throttle loop, P66's included.
pub const DPS_TAU: f64 = 0.2;
/// RCS thruster nominal thrust, N. Provenance: lm_simulator.tcl:182.
pub const RCS_THRUST_N: f64 = 445.0;
/// RCS effective exhaust velocity, m/s. Provenance: lm_simulator.tcl:183.
pub const RCS_VE: f64 = 2840.0;
/// RCS torque lever arm, m. Provenance: derived from LM_Simulator.
pub const RCS_LEVER_M: f64 = 1.68;
/// Trim-gimbal drive rate, deg/s. Provenance: assumed (not found in
/// vendored lm_simulator.tcl; consistent with historical LM DPS gimbal
/// trim actuator rate).
pub const TRIM_RATE_DEG_S: f64 = 0.2;
/// Trim-gimbal maximum deflection, degrees. Provenance: assumed (not found
/// in vendored lm_simulator.tcl; consistent with historical LM DPS ±6°
/// pitch/roll trim range).
pub const TRIM_MAX_DEG: f64 = 6.0;
/// DPS thrust per THRUST-counter bit, N. Provenance: **the flown rope
/// publishes it**, as the reciprocal —
/// `vendor/virtualagc/Luminary099/CONTROLLED_CONSTANTS.agc:135`,
/// `SCALEFAC 2DEC* +7.97959872 E+2 B-16*  # BITPERF +7.97959872 E-2`,
/// bits per newton, so 1 / 0.0797959872 = **12.531966 N/bit**.
///
/// This is the conversion the AGC itself uses in both directions, which is
/// why it has to be exact rather than close: `MASSMULT` turns a desired
/// acceleration into counter bits through `SCALEFAC`
/// (`THROTTLE_CONTROL_ROUTINES.agc:206-214`), and P66's force law divides
/// by it again (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1074-1076`). Any
/// error here is a proportional thrust error across the whole modulated
/// band — the AGC asks for N and gets 0.9575·N.
///
/// Cross-checked three further ways against the same block, all agreeing
/// to 0.03 %: FEXTRA 51 330.9 N / 4096 bits = 12.5320
/// (`THROTTLE_CONTROL_ROUTINES.agc:226`), FSAT 48 145.4 / 3841 = 12.5346,
/// FMAX 43 454.7 / 3467 = 12.5338 (`CONTROLLED_CONSTANTS.agc:132-133`).
///
/// Was `assumed = 12.0`, then briefly mis-cited (2026-07-26) to
/// `LUM69R2/PADLOADS.agc:501`'s "2.7 LBS/BIT" = 12.0325 N/bit as if that
/// justified it. It does not: LUM69R2 is a different rope with a different
/// SCALEFAC, and 12.0 was 4.25 % low against the rope we actually fly.
pub const THRUST_N_PER_PULSE: f64 = 12.531966;
/// Max DINC strobes per 10 ms tick.
///
/// The real throttle-drive electronics run 3200 pps (32 per tick), but on
/// this rig every strobe is a socket packet and a counter interrupt, not an
/// electrical pulse. At 32/tick the interrupt load starves the Servicer and
/// Luminary POODOOs 01202 (EXECUTIVE OVERFLOW — NO VAC AREAS) once P66 is
/// commanding throttle every pass — the same mechanism as Apollo 11's own
/// 1202, where the rendezvous radar's CDU counters stole the AGC's time.
/// 800 pps still slews the actuator's full 0-4096 stroke in ~5 s, well
/// inside the ZOOMTIME trim phase and P66's 1-2 s command cadence.
/// Measured: spike-B iters 10-11.
pub const DINC_MAX_PER_TICK: u32 = 8;
/// Physics step, seconds (spec: RK4 fixed 10 ms).
pub const DT: f64 = 0.010;
