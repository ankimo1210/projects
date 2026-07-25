use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const SCHEMA_VERSION: u32 = 2;

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
            prog: "63".into(),
            verb: "16".into(),
            noun: "36".into(),
            r1: "+00031".into(),
            r2: "      ".into(),
            r3: "      ".into(),
            lamps: Default::default(),
            verb_noun_flash: false,
            restart: false,
            standby: false,
            key_rel: false,
            opr_err: false,
            temp: false,
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

    #[test]
    fn telemetry_msg_json_shape() {
        let msg = ServerMsg::Telemetry(TelemetryMsg {
            schema_version: SCHEMA_VERSION,
            t_s: 12.5,
            frozen: false,
            alt_m: 480.0,
            vz_ms: -1.2,
            v_horiz_ms: 0.3,
            tilt_deg: 4.0,
            mass_kg: 9000.0,
            fuel_dps_kg: 1900.0,
            fuel_rcs_kg: 148.0,
            thrust_n: 14800.0,
            throttle_cmd_pulses: 1234,
            jets: 0b0000_0001,
            mm: "66".into(),
            agc_alt_m: None,
            agc_hdot_ms: Some(-1.1),
            nav_err_alt_m: None,
            nav_err_hdot_ms: Some(0.1),
            drift_ms: 2.0,
            downlink_wps: 50.0,
            ingest_drops: 0,
            touchdown: None,
        });
        let j: serde_json::Value = serde_json::to_value(&msg).unwrap();
        assert_eq!(j["type"], "telemetry");
        assert_eq!(j["mm"], "66");
        assert_eq!(j["schema_version"], 2);
        assert_eq!(j["agc_alt_m"], serde_json::Value::Null);
    }

    #[test]
    fn client_rod_parses() {
        let m: ClientMsg = serde_json::from_str(r#"{"type":"rod","up":false}"#).unwrap();
        assert!(matches!(m, ClientMsg::Rod { up: false }));
    }
}
