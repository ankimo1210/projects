use eagle_agc_protocol::Packet;
use eagle_agc_protocol::{dsky::DskyState, keys::DskyKey};
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use std::path::PathBuf;

fn cfg(port: u16) -> AgcConfig {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..");
    AgcConfig {
        yaagc_bin: root.join("build/agc/yaAGC"),
        core_bin: root.join("build/agc/Luminary099.bin"),
        port,
    }
}

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn boots_and_produces_packets_after_rset() {
    let mut s = AgcSession::start(cfg(19897)).await.unwrap();
    s.send(Packet::io(0o15, 0o22).unwrap()).unwrap(); // RSET
    let p = tokio::time::timeout(std::time::Duration::from_secs(5), s.events().recv())
        .await.expect("timed out").expect("channel closed");
    assert!(p.channel <= 0o177);
    s.shutdown();
}

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn v35e_lights_all_eights() {
    let mut s = AgcSession::start(cfg(19898)).await.unwrap();
    // let Luminary boot before keying
    tokio::time::sleep(std::time::Duration::from_secs(2)).await;
    for k in [DskyKey::Verb, DskyKey::D3, DskyKey::D5, DskyKey::Entr] {
        s.send(k.packet()).unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(200)).await;
    }
    let mut state = DskyState::default();
    let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(5);
    loop {
        let timeout = deadline - tokio::time::Instant::now();
        match tokio::time::timeout(timeout, s.events().recv()).await {
            Ok(Some(p)) => {
                state.apply(&p);
                if state.verb == ['8', '8'] && state.noun == ['8', '8']
                    && state.prog == ['8', '8'] {
                    s.shutdown();
                    return; // lamp test confirmed
                }
            }
            _ => break,
        }
    }
    panic!("V35E did not produce the 88 lamp-test display; last state: {state:?}");
}
