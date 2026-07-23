//! Live smoke test for the DSKY scripting harness (`script.rs`): boots the
//! real yaAGC/Luminary099, drives it entirely through `pump()` +
//! `DskyScript`, and checks the three choreography steps from the Task 4
//! brief: a V35E lamp test observed end to end through `keys()`, an
//! erasable read-back via `read_erasable`, and `alarm_codes` returning.
use eagle_agc_protocol::dsky::DskyState;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::script::{pump, DskyScript};
use std::path::PathBuf;
use std::time::Duration;
use tokio::sync::watch;

fn root() -> PathBuf { PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..") }

/// Quiet-check analog of `golden_v35e.rs`'s `settle_dsky`, adapted to the
/// `DskyScript`/`pump()` layer: we no longer have raw packet access (pump()
/// owns the `AgcSession` internally), but `DskyState::apply` already scopes
/// itself to exactly the three DSKY-relevant channels (010/011/0163) that
/// the original helper filters for, and the watch channel only fires on a
/// crew-visible change (`apply`'s change-detection contract) — so "no
/// `changed()` for 100 ms" is the same signal, one layer up.
async fn settle_dsky(rx: &mut watch::Receiver<DskyState>) {
    let start = tokio::time::Instant::now();
    loop {
        match tokio::time::timeout(Duration::from_millis(100), rx.changed()).await {
            Ok(Ok(())) => {} // saw a visible change; keep waiting for quiet
            Ok(Err(_)) => break, // pump's sender side is gone
            Err(_) => break,     // 100 ms elapsed with no change => quiet
        }
        assert!(start.elapsed() < Duration::from_secs(5),
            "settle_dsky did not settle within 5s safety cap");
    }
}

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn dsky_script_drives_lamp_test_and_reads_erasables() {
    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19901,
    }).await.unwrap();

    let (dsky_rx, cmd_tx, _pump_handle) = pump(session);
    let mut settle_rx = dsky_rx.clone();
    let mut script = DskyScript::new(cmd_tx, dsky_rx);
    script.set_key_delay(Duration::from_millis(80));

    // Let Luminary boot before keying (mirrors live_agc.rs / live_ws.rs),
    // then flush boot-time DSKY chatter before the scripted sequence starts.
    tokio::time::sleep(Duration::from_secs(2)).await;
    settle_dsky(&mut settle_rx).await;

    // 1) V35E lamp test observed end to end through keys() — proves the
    //    keys() -> pump() -> live AGC -> watch<DskyState> path works.
    script.keys("V35E").await.unwrap();
    let lamp = script.wait(Duration::from_secs(5), |d| {
        d.verb == ['8', '8'] && d.noun == ['8', '8'] && d.prog == ['8', '8']
    }).await.unwrap();
    assert_eq!((lamp.verb, lamp.noun, lamp.prog), (['8', '8'], ['8', '8'], ['8', '8']));

    // The V35 lamp test auto-reverts ~5s after ENTR (agc_engine.c
    // DSKY_FLASH_PERIOD teardown, cross-checked in golden_v35e.rs). Wait for
    // that before issuing further V/N entries so they land in a clean idle
    // state rather than racing the lamp test's own teardown.
    script.wait(Duration::from_secs(8), |d| {
        d.verb != ['8', '8'] || d.noun != ['8', '8'] || d.prog != ['8', '8']
    }).await.unwrap();

    // 2) read_erasable(0o0) parses (register A, value arbitrary — this is a
    //    read-only smoke check, not a specific-value assertion).
    let a_reg = script.read_erasable(0o0).await.unwrap();
    assert!(a_reg <= 0o77777);

    // 3) alarm_codes() returns without timeout.
    let codes = script.alarm_codes().await.unwrap();
    assert_eq!(codes.len(), 3);
}
