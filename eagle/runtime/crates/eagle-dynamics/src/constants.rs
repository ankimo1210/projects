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
/// DPS nominal maximum thrust, N = 10 500 lbf. Provenance: **derived from
/// the rope's own pad-load**, cross-checked against a live descent.
///
/// `vendor/virtualagc/LUM69R2/PADLOADS.agc:501-511` documents the two
/// throttle-region criteria with both their bit scale and what fraction of
/// maximum thrust they represent:
///
/// * `LOWCRIT  1OCT 04251` = 2217 bits, "(2.7 LBS/BIT) (57% NOMINAL MAX
///   THRUST)" → 2217 × 2.7 / 0.57 = 10 502 lbf
/// * `HIGHCRIT 1OCT 04622` = 2450 bits, "63% NOMINAL MAX THRUST"
///   → 2450 × 2.7 / 0.63 = 10 500 lbf
///
/// Two independent pad words agreeing to 0.02 % on **10 500 lbf =
/// 46 706 N**. (Both words are carried in `scenarios/p66-padload.toml`, so
/// the AGC we fly is loaded with exactly these criteria.)
///
/// Supersedes LM_Simulator's `lm_simulator.tcl:186` (45 040 N), which is
/// 3.6 % lower and was this repo's original provenance. Measured live
/// (2026-07-26 M1 flight 2): at 42 500 N the braking phase ran out of
/// capability and reached HIGATE at 4052 m / 435 m/s against the
/// pad-loaded RBRFG/VBRFG target of 2924 m / 172 m/s — the AGC flew its
/// guidance correctly into an engine that could not deliver the profile.
/// See `docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`.
pub const DPS_MAX_N: f64 = 46706.0;
/// DPS minimum throttle thrust, N. Provenance: lm_simulator.tcl:187.
pub const DPS_MIN_N: f64 = 4560.0;
/// Fixed throttle point: commands above 60 % snap here — and per
/// `LUM69R2/PADLOADS.agc:501-511` ("THROTTLE SET TO EITHER MAXIMUM OR TRUE
/// VALUE" outside the 57-63 % band) the AGC's "maximum" IS nominal max
/// thrust, so this is `DPS_MAX_N`, not a lower fixed point. Provenance:
/// derived, same two pad words.
pub const DPS_FTP_N: f64 = DPS_MAX_N;
/// DPS effective exhaust velocity, m/s. Provenance: lm_simulator.tcl:188.
pub const DPS_VE: f64 = 3050.0;
/// DPS first-order throttle lag, s. Provenance: assumed.
pub const DPS_TAU: f64 = 0.3;
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
/// DPS thrust per THRUST-counter pulse, N. Provenance: derived —
/// `vendor/virtualagc/LUM69R2/PADLOADS.agc:501` states the throttle-counter
/// scale outright, "(2.7 LBS/BIT)", = 12.010 N/bit. Kept at 12.0 (0.08 %
/// low) because that is the value every live spike was calibrated against;
/// the citation replaces the previous "assumed" tag, it does not move the
/// number.
pub const THRUST_N_PER_PULSE: f64 = 12.0;
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
