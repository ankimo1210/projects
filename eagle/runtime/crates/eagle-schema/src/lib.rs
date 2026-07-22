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

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ServerMsg {
    DskyState(DskyStateMsg),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientMsg {
    Key { key: String },
    Pro { pressed: bool },
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
