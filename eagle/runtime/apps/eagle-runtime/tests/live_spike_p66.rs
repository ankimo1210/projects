//! Spike B frozen choreography (Task 7): Spike A's boot → pad-load → P63 →
//! ENGINE ON, then ATT HOLD plus a ROD click into P66, with the THRUST
//! DINC loop closing a real vertical channel and the ROD channel moving
//! the AGC's desired altitude rate.
//!
//! Live test: needs `make agc` artifacts; run with
//! `cargo test -p eagle-runtime --test live_spike_p66 -- --ignored --test-threads=1`
//! Budget: ~8-11 minutes (same real-time TIG countdown as Spike A, plus
//! the ZOOMTIME trim phase that must elapse before GUILDENSTERN runs).
use eagle_runtime::padload::{generate_state, PadloadManifest, StateCfg, SymTab};
use eagle_runtime::runner::{
    self, DescentInit, HoverTruth, SyntheticHover, FLAGWRD3_ECADR, FLAGWRD8_ECADR,
    FLAGWRD8_MOON_BITS, REFSMBIT, SPIKE_B_ALARM_WHITELIST,
};
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::script::{pump, DskyScript};
use std::path::PathBuf;
use std::time::Duration;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

/// Vertical truth the closed loop starts from. High enough to survive the
/// ~26 s ZOOMTIME trim phase at the DPS idle stop (~450 m of altitude)
/// before P66 can take over.
fn initial_truth() -> HoverTruth {
    HoverTruth {
        alt_m: 3_000.0,
        vz_ms: 0.0,
        mass_kg: 15_195.0,
        cmd_pulses: 0,
        thrust_n: 0.0,
        engine_on: false,
    }
}

#[tokio::test]
#[ignore = "needs make agc artifacts (live spike, ~10 min)"]
async fn att_hold_rod_click_enters_p66_and_closes_the_thrust_loop() {
    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19903,
    })
    .await
    .unwrap();
    let (dsky_rx, cmd_tx, pkt_rx, _pump) = pump(session);
    let mut script = DskyScript::new(cmd_tx.clone(), dsky_rx);
    script.set_key_delay(Duration::from_millis(30));
    let mut init = DescentInit {
        script,
        packets: pkt_rx.resubscribe(),
        agc_tx: cmd_tx,
    };

    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(root().join("build/agc/Luminary099.log")).unwrap(),
    )
    .unwrap();
    let static_manifest =
        PadloadManifest::load(&root().join("scenarios/p66-padload.toml")).unwrap();

    // --- Spike A's proven boot → ignition sequence -----------------------
    tokio::time::sleep(Duration::from_secs(2)).await;
    init.script.keys("R").await.unwrap();
    init.script.keys("V37E00E").await.unwrap();
    init.script.wait_prog("00").await.expect("P00 after V37E00E");

    // v1 feeder holds the hover PIPA stream until ignition; the closed loop
    // arms the THRUST responder now because P63's first throttle
    // transaction (MOUT 4096 to the zero stop) happens before ENGINE ON.
    let v1 = SyntheticHover::spawn(init.agc_tx.clone());
    let closed = SyntheticHover::spawn_closed_loop(
        init.agc_tx.clone(),
        init.packets.resubscribe(),
        initial_truth(),
    );
    runner::init_discretes(&init.agc_tx).await.unwrap();
    runner::dap_init(&mut init.script, 33500, 0)
        .await
        .expect("V48 DAP init");

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

    runner::wait_iss_turnon(&mut init.packets, &init.agc_tx, Duration::from_secs(150))
        .await
        .expect("ISS turn-on delay complete");
    init.script
        .wait(Duration::from_secs(30), |d| !d.lamps.no_att)
        .await
        .expect("NO ATT out after ISS turn-on");

    let words = static_manifest
        .resolve(&symtab)
        .expect("static manifest resolves");
    runner::apply_padload(&mut init.script, &words, 8, runner::ALWAYS_VERIFY_ECADRS)
        .await
        .expect("static pad-load");
    let words = state_manifest
        .resolve(&symtab)
        .expect("state manifest resolves");
    runner::apply_padload(&mut init.script, &words, 8, runner::ALWAYS_VERIFY_ECADRS)
        .await
        .expect("state pad-load");

    runner::set_flag_bits(&mut init.script, FLAGWRD8_ECADR, FLAGWRD8_MOON_BITS)
        .await
        .expect("FLAGWRD8 moon bits");
    runner::set_flag_bits(&mut init.script, FLAGWRD3_ECADR, REFSMBIT)
        .await
        .expect("REFSMFLG");

    runner::enter_p63(&mut init.script)
        .await
        .expect("P63 dialog to V99 PRO");
    runner::wait_engine_on(&mut init.packets, Duration::from_secs(180))
        .await
        .expect("ENGINE ON (ch 011 bit13)");
    v1.stop();

    // --- P66 entry: ATT HOLD plus one ROD click --------------------------
    // GUILDENSTERN takes STARTP66 only when the un-attitude-hold discrete
    // is asserted AND RODCOUNT is non-zero
    // (LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:203-217). The click is a direct
    // RODCOUNT load because yaAGC raises no interrupt for channel 016 —
    // see docs/agc-channel-map.md and `runner::rod_load`.
    tokio::time::sleep(Duration::from_secs(2)).await;
    runner::att_hold(&init.agc_tx).await.expect("ATT HOLD");
    runner::rod_load(&mut init.script, -1)
        .await
        .expect("selection ROD click");
    init.script
        .wait_prog("66")
        .await
        .expect("GUILDENSTERN did not reach MM66");

    // --- The vertical channel is actually closed -------------------------
    let truth = closed.truth().expect("closed-loop truth watch");
    let cmd_at_p66 = truth.borrow().cmd_pulses;
    assert!(
        cmd_at_p66 > 0,
        "THRUST DINC loop never moved the actuator off its zero stop"
    );

    // --- ROD moves the AGC's desired altitude rate -----------------------
    // RODCOMP adds RODCOUNT * RODSCAL1 to VDGVERT as a DP product
    // (LLGE:958-963), so two clicks must move VDGVERT by exactly twice the
    // RODSCAL1 word. VDGVERT has no other writer once P66 is running.
    //
    // This is the load done over the unpatched channel-016-blind yaAGC: the
    // ROD "click" is a direct RODCOUNT load (runner::rod_load), never the
    // ch016 switch discrete, so an exact 2 x RODSCAL1 move here IS the
    // proof that no vendor patch is needed for the ROD channel.
    let rodscal1 = eagle_agc_protocol::words::sp_decode(
        init.script
            .read_erasable(runner::RODSCAL1_ECADR)
            .await
            .expect("RODSCAL1"),
    ) as i64;
    // A ROD load is not read-back-verified (RODCOMP zeroes RODCOUNT within a
    // pass), so a load swallowed by the flight display lands as a zero move.
    // Retry only that case; an exact move passes, any other delta is a real
    // failure (wrong scale or a corrupt read).
    let mut moved = None;
    for attempt in 0..3 {
        let vdg_before = runner::read_dp(&mut init.script, runner::VDGVERT_ECADR)
            .await
            .expect("VDGVERT before");
        runner::rod_load(&mut init.script, -2)
            .await
            .expect("two down-clicks");
        tokio::time::sleep(Duration::from_secs(3)).await;
        let vdg_after = match runner::read_dp(&mut init.script, runner::VDGVERT_ECADR).await {
            Ok(v) => v,
            Err(e) => {
                let codes = init.script.alarm_codes().await;
                panic!("VDGVERT after: {e:#}; FAILREG = {codes:?}");
            }
        };
        let delta = vdg_after - vdg_before;
        if delta != 0 {
            moved = Some(delta);
            break;
        }
        eprintln!("[spike-b] ROD load swallowed (attempt {attempt}); retrying");
    }
    assert_eq!(
        moved.expect("ROD load never took effect in 3 attempts"),
        -2 * rodscal1,
        "two ROD clicks did not move VDGVERT by 2 x RODSCAL1"
    );

    // --- Alarms -----------------------------------------------------------
    let codes = init.script.alarm_codes().await.expect("V05N09");
    for code in codes {
        assert!(
            code == 0 || SPIKE_B_ALARM_WHITELIST.contains(&code),
            "non-whitelisted alarm {code:05o} (FAILREG {codes:?})"
        );
    }
}
