// Telemetry frame mirroring eagle_schema::TelemetryMsg (snake_case), schema v2.
export interface TelemetryFrame {
  schema_version: number;
  t_s: number;
  frozen: boolean;
  alt_m: number;
  vz_ms: number;
  v_horiz_ms: number;
  tilt_deg: number;
  mass_kg: number;
  fuel_dps_kg: number;
  fuel_rcs_kg: number;
  thrust_n: number;
  throttle_cmd_pulses: number;
  jets: number;
  mm: string;
  agc_alt_m: number | null;
  agc_hdot_ms: number | null;
  nav_err_alt_m: number | null;
  nav_err_hdot_ms: number | null;
  drift_ms: number;
  downlink_wps: number;
  ingest_drops: number;
  touchdown: string | null;
  /** Scenario explicitly opts into the non-authentic playable safety layer. */
  demo_mode: boolean;
  assist_active: boolean;
  /** Signed target vertical velocity; negative means down. */
  assist_target_vz_ms: number | null;
  touchdown_v_vert_ms: number | null;
  touchdown_v_horiz_ms: number | null;
  touchdown_tilt_deg: number | null;
  /** Sim-driven P64→P66 handover has fired (latched). Always false in hover mode. */
  handover: boolean;
}

export interface PhaseChange {
  t_s: number;
  mm: string;
}
