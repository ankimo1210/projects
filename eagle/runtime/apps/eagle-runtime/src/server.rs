use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::Router;
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::keys::{pro_key_packets, DskyKey};
use eagle_agc_protocol::Packet;
use eagle_schema::{ClientMsg, DskyStateMsg, ServerMsg, SCHEMA_VERSION};
use futures_util::{SinkExt, StreamExt};
use tokio::sync::{broadcast, mpsc};

pub fn to_msg(s: &DskyState) -> ServerMsg {
    let reg = |r: &eagle_agc_protocol::dsky::RegisterDisplay| {
        std::iter::once(r.sign).chain(r.digits).collect::<String>()
    };
    let mut lamps = std::collections::BTreeMap::new();
    for (name, v) in [
        ("comp_acty", s.lamps.comp_acty), ("uplink_acty", s.lamps.uplink_acty),
        ("no_att", s.lamps.no_att), ("gimbal_lock", s.lamps.gimbal_lock),
        ("prog", s.lamps.prog_alarm), ("tracker", s.lamps.tracker),
        ("alt", s.lamps.alt), ("vel", s.lamps.vel),
        ("no_dap", s.lamps.no_dap), ("prio_disp", s.lamps.prio_disp),
    ] { lamps.insert(name.to_string(), v); }
    ServerMsg::DskyState(DskyStateMsg {
        schema_version: SCHEMA_VERSION,
        prog: s.prog.iter().collect(), verb: s.verb.iter().collect(),
        noun: s.noun.iter().collect(),
        r1: reg(&s.r1), r2: reg(&s.r2), r3: reg(&s.r3),
        lamps,
        verb_noun_flash: s.verb_noun_flash, restart: s.restart,
        standby: s.standby, key_rel: s.key_rel, opr_err: s.opr_err,
        temp: s.temp,
    })
}

#[derive(Clone)]
pub struct AppState {
    pub state_rx: broadcast::Sender<String>, // serialized ServerMsg JSON
    pub agc_tx: mpsc::UnboundedSender<Packet>,
    pub latest: std::sync::Arc<std::sync::Mutex<String>>,
}

pub fn router(app: AppState) -> Router {
    Router::new().route("/ws", get(ws_handler)).with_state(app)
}

async fn ws_handler(ws: WebSocketUpgrade, State(app): State<AppState>) -> impl IntoResponse {
    ws.on_upgrade(move |sock| client_loop(sock, app))
}

async fn client_loop(sock: WebSocket, app: AppState) {
    let (mut tx, mut rx) = sock.split();
    // Subscribe before reading/sending the snapshot: a change landing in the
    // gap between reading `latest` and starting to receive broadcasts would
    // otherwise be lost forever for this client. Subscribing first guarantees
    // at-least-once delivery — the worst case is a duplicate full-state frame
    // right after connect, which is harmless since every frame is a complete,
    // idempotent snapshot.
    let mut updates = app.state_rx.subscribe();
    let snapshot = app.latest.lock().unwrap().clone();
    if !snapshot.is_empty() {
        let _ = tx.send(Message::Text(snapshot.into())).await;
    }
    loop {
        tokio::select! {
            u = updates.recv() => match u {
                Ok(json) => { if tx.send(Message::Text(json.into())).await.is_err() { break } }
                Err(broadcast::error::RecvError::Lagged(_)) => continue,
                Err(_) => break,
            },
            m = rx.next() => match m {
                Some(Ok(Message::Text(text))) => {
                    if let Ok(msg) = serde_json::from_str::<ClientMsg>(&text) {
                        match msg {
                            ClientMsg::Key { key } => {
                                if let Some(k) = DskyKey::from_name(&key) {
                                    let _ = app.agc_tx.send(k.packet());
                                }
                            }
                            ClientMsg::Pro { pressed } => {
                                for p in pro_key_packets(pressed) {
                                    let _ = app.agc_tx.send(p);
                                }
                            }
                        }
                    }
                }
                Some(Ok(_)) => continue,
                _ => break,
            },
        }
    }
}
