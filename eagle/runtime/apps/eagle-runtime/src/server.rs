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
        ("comp_acty", s.lamps.comp_acty),
        ("uplink_acty", s.lamps.uplink_acty),
        ("no_att", s.lamps.no_att),
        ("gimbal_lock", s.lamps.gimbal_lock),
        ("prog", s.lamps.prog_alarm),
        ("tracker", s.lamps.tracker),
        ("alt", s.lamps.alt),
        ("vel", s.lamps.vel),
        ("no_dap", s.lamps.no_dap),
        ("prio_disp", s.lamps.prio_disp),
    ] {
        lamps.insert(name.to_string(), v);
    }
    ServerMsg::DskyState(DskyStateMsg {
        schema_version: SCHEMA_VERSION,
        prog: s.prog.iter().collect(),
        verb: s.verb.iter().collect(),
        noun: s.noun.iter().collect(),
        r1: reg(&s.r1),
        r2: reg(&s.r2),
        r3: reg(&s.r3),
        lamps,
        verb_noun_flash: s.verb_noun_flash,
        restart: s.restart,
        standby: s.standby,
        key_rel: s.key_rel,
        opr_err: s.opr_err,
        temp: s.temp,
    })
}

#[derive(Clone)]
pub struct AppState {
    pub state_rx: broadcast::Sender<String>, // serialized ServerMsg JSON
    pub agc_tx: mpsc::UnboundedSender<Packet>,
    pub latest: std::sync::Arc<std::sync::Mutex<String>>,
    /// Scenario mode: ROD clicks route here (+1 = slow descent 1 ft/s) and
    /// become `runner::rod_load` RODCOUNT loads. `None` in Phase-1
    /// DSKY-only mode → hardware-faithful ch016 discrete (a documented
    /// no-op on stock yaAGC — see docs/agc-channel-map.md "Rod Switch
    /// Click").
    pub rod_click_tx: Option<mpsc::UnboundedSender<i32>>,
}

pub fn router(app: AppState) -> Router {
    Router::new().route("/ws", get(ws_handler)).with_state(app)
}

async fn ws_handler(ws: WebSocketUpgrade, State(app): State<AppState>) -> impl IntoResponse {
    ws.on_upgrade(move |sock| client_loop(sock, app))
}

/// Route one parsed client message. Pure channel-pushes so it is unit
/// testable; the ws loop just parses JSON and delegates here.
pub fn route_client_msg(msg: ClientMsg, app: &AppState) {
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
        ClientMsg::Rod { up } => match &app.rod_click_tx {
            Some(tx) => {
                let _ = tx.send(if up { 1 } else { -1 });
            }
            None => {
                // Phase-1: press now, release after 100 ms (ch016).
                // NOTE: stock yaAGC raises no interrupt for ch016, so this
                // discrete is observed only on a patched build; the
                // closed-loop path uses runner::rod_load (RODCOUNT)
                // instead. Kept for a hardware-faithful manual button.
                let (press, release) = eagle_agc_protocol::agc_io::rod_click(up);
                let _ = app.agc_tx.send(press);
                let tx = app.agc_tx.clone();
                tokio::spawn(async move {
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                    let _ = tx.send(release);
                });
            }
        },
    }
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
                        route_client_msg(msg, &app);
                    }
                }
                Some(Ok(_)) => continue,
                _ => break,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eagle_schema::ClientMsg;
    use tokio::sync::{broadcast, mpsc};

    fn app(rod: Option<mpsc::UnboundedSender<i32>>) -> (AppState, mpsc::UnboundedReceiver<Packet>) {
        let (state_rx, _) = broadcast::channel(8);
        let (agc_tx, agc_rx) = mpsc::unbounded_channel();
        (
            AppState {
                state_rx,
                agc_tx,
                latest: Default::default(),
                rod_click_tx: rod,
            },
            agc_rx,
        )
    }

    #[tokio::test]
    async fn key_routes_to_agc_channel() {
        let (app, mut agc_rx) = app(None);
        route_client_msg(ClientMsg::Key { key: "VERB".into() }, &app);
        assert!(agc_rx.try_recv().is_ok(), "VERB key must produce a packet");
    }

    #[tokio::test]
    async fn rod_routes_to_click_channel_in_scenario_mode() {
        let (rod_tx, mut rod_rx) = mpsc::unbounded_channel();
        let (app, mut agc_rx) = app(Some(rod_tx));
        route_client_msg(ClientMsg::Rod { up: false }, &app);
        route_client_msg(ClientMsg::Rod { up: true }, &app);
        assert_eq!(rod_rx.recv().await, Some(-1));
        assert_eq!(rod_rx.recv().await, Some(1));
        assert!(
            agc_rx.try_recv().is_err(),
            "no ch016 packets in scenario mode"
        );
    }

    #[tokio::test(start_paused = true)]
    async fn rod_falls_back_to_ch016_press_release_in_dsky_mode() {
        let (app, mut agc_rx) = app(None);
        route_client_msg(ClientMsg::Rod { up: true }, &app);
        let press = agc_rx.recv().await.unwrap();
        assert_eq!((press.channel, press.data), (0o16, 1 << 5));
        tokio::time::sleep(std::time::Duration::from_millis(150)).await;
        let release = agc_rx.recv().await.unwrap();
        assert_eq!((release.channel, release.data), (0o16, 0));
    }
}
