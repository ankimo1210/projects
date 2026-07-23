//! Spike A frozen choreography (Task 6): boot → discretes/ISS turn-on →
//! V48 DAP init → pad-load (static manifest + live-generated state) →
//! REFSMFLG/FLAGWRD8 → V37E63E → responder dialog → ENGINE ON.
//!
//! Live test: needs `make agc` artifacts; run with
//! `cargo test -p eagle-runtime --test live_spike_p63 -- --ignored --test-threads=1`
//! Budget: one full run is ~8-11 minutes of wall time (90 s ISS turn-on
//! delay, ~2 min of DSKY pad-loading, ~6 min TIG countdown — BURNBABY's
//! pre-TIG integration and the V06N62 countdown are real-time).
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::padload::{generate_state, PadloadManifest, StateCfg, SymTab};
use eagle_runtime::runner::{
    self, DescentInit, SyntheticHover, FLAGWRD3_ECADR, FLAGWRD8_ECADR, FLAGWRD8_MOON_BITS,
    REFSMBIT, SPIKE_A_ALARM_WHITELIST,
};
use eagle_runtime::script::{pump, DskyScript};
use std::path::PathBuf;
use std::time::Duration;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

#[tokio::test]
#[ignore = "needs make agc artifacts (live spike, ~10 min)"]
async fn boot_padload_p63_ignition() {
    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19902,
    })
    .await
    .unwrap();
    let (dsky_rx, cmd_tx, pkt_rx, _pump) = pump(session);
    let mut script = DskyScript::new(cmd_tx.clone(), dsky_rx);
    script.set_key_delay(Duration::from_millis(30));
    let mut init = DescentInit {
        script,
        packets: pkt_rx,
        agc_tx: cmd_tx,
    };

    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(root().join("build/agc/Luminary099.log")).unwrap(),
    )
    .unwrap();
    let static_manifest =
        PadloadManifest::load(&root().join("scenarios/p66-padload.toml")).unwrap();

    // --- Boot, fresh-start dance, hover feed, discretes -----------------
    tokio::time::sleep(Duration::from_secs(2)).await;
    init.script.keys("R").await.unwrap(); // clear boot lamps
    init.script.keys("V37E00E").await.unwrap();
    init.script
        .wait_prog("00")
        .await
        .expect("P00 after V37E00E");

    let _hover = SyntheticHover::spawn(init.agc_tx.clone());
    runner::init_discretes(&init.agc_tx).await.unwrap();

    // --- DAP init (V48/R03), live-confirmed dialog -----------------------
    runner::dap_init(&mut init.script, 33500, 0)
        .await
        .expect("V48 DAP init");

    // --- Clock read + state generation -----------------------------------
    let epoch_cs = runner::read_clock_cs(&mut init.script)
        .await
        .expect("clock read");
    let state_manifest = PadloadManifest {
        word: generate_state(&StateCfg {
            epoch_now_cs: epoch_cs,
            burn_lead_cs: 36_000.0,
            ..StateCfg::default()
        }),
    };

    // --- ISS turn-on completes ~90 s after init_discretes ----------------
    runner::wait_iss_turnon(&mut init.packets, &init.agc_tx, Duration::from_secs(150))
        .await
        .expect("ISS turn-on delay complete");
    init.script
        .wait(Duration::from_secs(30), |d| !d.lamps.no_att)
        .await
        .expect("NO ATT out after ISS turn-on");

    // --- Pad-load: static targets + generated state ----------------------
    // Sparse verification (every 8th word) fits the time budget; the
    // words the spike saw fail live are all in the state manifest, which
    // uses the same cadence plus load_erasable's own read-back on the
    // verified samples.
    let words = static_manifest
        .resolve(&symtab)
        .expect("static manifest resolves");
    runner::apply_padload(&mut init.script, &words, 8)
        .await
        .expect("static pad-load");
    let words = state_manifest
        .resolve(&symtab)
        .expect("state manifest resolves");
    runner::apply_padload(&mut init.script, &words, 8)
        .await
        .expect("state pad-load");

    // --- Flags: permanent-state moon bits, then REFSMFLG last ------------
    runner::set_flag_bits(&mut init.script, FLAGWRD8_ECADR, FLAGWRD8_MOON_BITS)
        .await
        .expect("FLAGWRD8 moon bits");
    runner::set_flag_bits(&mut init.script, FLAGWRD3_ECADR, REFSMBIT)
        .await
        .expect("REFSMFLG");

    // --- P63: V37E63E + responder dialog ---------------------------------
    let mut mm63_watch = init.script.dsky();
    let saw_mm63 = tokio::spawn(async move {
        loop {
            if mm63_watch.borrow().prog == ['6', '3'] {
                return true;
            }
            if mm63_watch.changed().await.is_err() {
                return false;
            }
        }
    });
    runner::enter_p63(&mut init.script)
        .await
        .expect("P63 dialog to V99 PRO");

    // --- ENGINE ON within 180 s of the V99 PRO ---------------------------
    runner::wait_engine_on(&mut init.packets, Duration::from_secs(180))
        .await
        .expect("ENGINE ON (ch 011 bit13)");

    // --- Post-conditions --------------------------------------------------
    assert!(saw_mm63.await.unwrap(), "MM never showed 63");
    // Downlink (ch 034/035) flowing at >=40 pkt/s, measured over a fresh
    // 5 s steady-state window (drift-meter precondition).
    let downlink_rate = runner::measure_downlink_rate(&mut init.packets, Duration::from_secs(5))
        .await
        .expect("downlink rate measurement");
    assert!(
        downlink_rate >= 40.0,
        "downlink rate {downlink_rate:.1}/s below the 40/s drift-meter precondition"
    );
    let codes = init.script.alarm_codes().await.expect("V05N09");
    for code in codes {
        assert!(
            code == 0 || SPIKE_A_ALARM_WHITELIST.contains(&code),
            "non-whitelisted alarm {code:05o} (FAILREG {codes:?})"
        );
    }
}
