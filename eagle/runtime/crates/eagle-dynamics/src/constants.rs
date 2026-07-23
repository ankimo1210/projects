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
/// PIPA ΔV per pulse, m/s. Provenance: LM_Simulator lm_simulator.tcl:145.
pub const PIPA_INCR: f64 = 0.0585;
/// CDU angle per pulse, degrees. Provenance: lm_simulator.tcl:141-142.
pub const CDU_INCR_DEG: f64 = 360.0 / 32768.0;
/// IMU coarse-align pulse, degrees. Provenance: lm_simulator.tcl:143.
pub const COARSE_INCR_DEG: f64 = 0.043948;
/// Gyro fine-align pulse, degrees. Provenance: lm_simulator.tcl:144.
pub const GYRO_FINE_INCR_DEG: f64 = 0.617981 / 3600.0;
/// DPS maximum throttle thrust, N. Provenance: lm_simulator.tcl:186.
pub const DPS_MAX_N: f64 = 45040.0;
/// DPS minimum throttle thrust, N. Provenance: lm_simulator.tcl:187.
pub const DPS_MIN_N: f64 = 4560.0;
/// Fixed throttle point: commands above 60% snap here. Provenance: assumed.
pub const DPS_FTP_N: f64 = 42500.0;
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
/// DPS thrust per THRUST-counter pulse, N. Provenance: assumed (≈2.7 lbf);
/// Spike B (Task 7) calibrates — update here if measurement disagrees.
pub const THRUST_N_PER_PULSE: f64 = 12.0;
/// Max DINC strobes per 10 ms tick (3200 pps nominal).
pub const DINC_MAX_PER_TICK: u32 = 32;
/// Physics step, seconds (spec: RK4 fixed 10 ms).
pub const DT: f64 = 0.010;
