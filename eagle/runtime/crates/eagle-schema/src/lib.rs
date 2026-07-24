use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq, Eq)]
pub struct DskyStateMsg {
    pub schema_version: u32,
    pub prog: String,
    pub verb: String,
    pub noun: String,
    pub r1: String,
    pub r2: String,
    pub r3: String,
    pub lamps: BTreeMap<String, bool>,
    pub verb_noun_flash: bool,
    pub restart: bool,
    pub standby: bool,
    pub key_rel: bool,
    pub opr_err: bool,
    pub temp: bool,
}

/// One engineer-telemetry frame from the sim thread (spec §6). Truth state
/// plus the AGC's own nav readout and their difference. Serialized to the
/// existing tagged-JSON broadcast.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TelemetryMsg {
    pub schema_version: u32,
    pub t_s: f64,
    pub frozen: bool,
    pub alt_m: f64,
    pub vz_ms: f64,
    pub v_horiz_ms: f64,
    pub tilt_deg: f64,
    pub mass_kg: f64,
    pub fuel_dps_kg: f64,
    pub fuel_rcs_kg: f64,
    pub thrust_n: f64,
    pub throttle_cmd_pulses: i64,
    pub jets: u16,
    pub mm: String,
    pub agc_alt_m: Option<f64>,
    pub agc_hdot_ms: Option<f64>,
    pub nav_err_alt_m: Option<f64>,
    pub nav_err_hdot_ms: Option<f64>,
    pub drift_ms: f64,
    pub downlink_wps: f64,
    pub ingest_drops: u64,
    pub touchdown: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ServerMsg {
    DskyState(DskyStateMsg),
    Telemetry(TelemetryMsg),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientMsg {
    Key { key: String },
    Pro { pressed: bool },
    Rod { up: bool },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn server_msg_json_shape() {
        let msg = ServerMsg::DskyState(DskyStateMsg {
            schema_version: 1,
            prog: "63".into(), verb: "16".into(), noun: "36".into(),
            r1: "+00031".into(), r2: "      ".into(), r3: "      ".into(),
            lamps: Default::default(),
            verb_noun_flash: false, restart: false, standby: false,
            key_rel: false, opr_err: false, temp: false,
        });
        let j: serde_json::Value = serde_json::to_value(&msg).unwrap();
        assert_eq!(j["type"], "dsky_state");
        assert_eq!(j["verb"], "16");
    }

    #[test]
    fn client_msg_parses() {
        let m: ClientMsg = serde_json::from_str(r#"{"type":"key","key":"VERB"}"#).unwrap();
        assert!(matches!(m, ClientMsg::Key { ref key } if key == "VERB"));
        let m: ClientMsg = serde_json::from_str(r#"{"type":"pro","pressed":true}"#).unwrap();
        assert!(matches!(m, ClientMsg::Pro { pressed: true }));
    }
}
