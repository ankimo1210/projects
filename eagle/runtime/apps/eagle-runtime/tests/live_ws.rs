use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::tungstenite::Message;

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn v16n36_shows_running_clock_over_ws() {
    let root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let mut child = tokio::process::Command::new(env!("CARGO_BIN_EXE_eagle-runtime"))
        .arg("--yaagc").arg(root.join("build/agc/yaAGC"))
        .arg("--core").arg(root.join("build/agc/Luminary099.bin"))
        .arg("--agc-port").arg("19899")
        .arg("--ws-port").arg("8899")
        .kill_on_drop(true)
        .spawn().unwrap();

    tokio::time::sleep(std::time::Duration::from_secs(3)).await; // AGC boot
    let (mut ws, _) = tokio_tungstenite::connect_async("ws://127.0.0.1:8899/ws")
        .await.expect("ws connect");

    for key in ["VERB", "1", "6", "NOUN", "3", "6", "ENTR"] {
        ws.send(Message::Text(format!(r#"{{"type":"key","key":"{key}"}}"#).into()))
            .await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(300)).await;
    }

    // Collect r1 (hours), r2 (minutes), r3 (seconds*100) readings for ~4 s;
    // the centiseconds register must change => the clock is running.
    let mut r3_values = std::collections::HashSet::new();
    let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(4);
    while tokio::time::Instant::now() < deadline {
        let Ok(Some(Ok(Message::Text(t)))) = tokio::time::timeout(
            std::time::Duration::from_millis(500), ws.next()).await else { continue };
        let v: serde_json::Value = serde_json::from_str(&t).unwrap();
        if v["type"] == "dsky_state" && v["verb"] == "16" && v["noun"] == "36" {
            r3_values.insert(v["r3"].as_str().unwrap().to_string());
        }
    }
    child.kill().await.ok();
    assert!(r3_values.len() >= 2,
        "expected V16N36 R3 (seconds) to tick, got {r3_values:?}");
}
