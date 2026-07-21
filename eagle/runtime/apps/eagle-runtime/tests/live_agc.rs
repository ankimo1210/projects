use eagle_agc_protocol::Packet;
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
