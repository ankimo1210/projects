//! Wave 1 acceptance (Task 16): the full Luminary099 closed loop flies a
//! P66 rate-of-descent landing to soft touchdown against our 6-DoF physics.
//! Errors OFF. Live: needs `make agc`; run with
//! `cargo test -p eagle-runtime --test live_p66_descent -- --ignored --test-threads=1`.
//!
//! Timing note: the choreography reaches ENGINE ON ~350 s after boot (the
//! TIG countdown is real-time — Spike A), so the WHOLE run is ~8-11 min and
//! the scenario `timeout_s` is measured from ENGINE ON, not from boot. The
//! wall-time guard is set accordingly (the plan's 300 s predated the live
//! choreography timing).
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::headless::{run_headless, touchdown_class, HeadlessCfg};
use eagle_runtime::padload::{PadloadManifest, SymTab};
use eagle_runtime::runner::{SPIKE_A_ALARM_WHITELIST, SPIKE_B_ALARM_WHITELIST};
use eagle_runtime::scenario::Scenario;
use eagle_dynamics::touchdown::Touchdown;
use std::path::PathBuf;
use std::time::{Duration, Instant};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

const WALL_BUDGET_S: u64 = 700;

#[tokio::test]
#[ignore = "needs make agc artifacts (live acceptance, ~10 min)"]
async fn p66_soft_landing_closed_loop() {
    let start = Instant::now();
    let sc = Scenario::load(&root().join("scenarios/p66-gate.toml")).unwrap();
    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(root().join("build/agc/Luminary099.log")).unwrap(),
    )
    .unwrap();
    let manifest = PadloadManifest::load(&root().join(&sc.agc.padload)).unwrap();

    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19904,
    })
    .await
    .unwrap();
    let (telem_tx, _keep) = tokio::sync::broadcast::channel::<String>(4096);

    let acceptance = sc.acceptance.clone();
    let result = tokio::time::timeout(
        Duration::from_secs(WALL_BUDGET_S),
        run_headless(HeadlessCfg {
            session,
            scenario: sc,
            symtab,
            manifest,
            telem_tx,
            latest: None,
            trace_out: Some(root().join("build/traces/p66-acceptance.jsonl")),
        }),
    )
    .await
    .expect("closed loop exceeded the wall-time budget")
    .expect("closed loop returned an error");

    // MM sequence contains 63 then 66 (intervening modes allowed).
    let i63 = result.mm_sequence.iter().position(|m| m == "63");
    let i66 = result.mm_sequence.iter().position(|m| m == "66");
    assert!(
        matches!((i63, i66), (Some(a), Some(b)) if a < b),
        "MM sequence must contain 63 then 66: {:?}",
        result.mm_sequence
    );

    // Touchdown before timeout, Nominal by the scenario thresholds.
    let (td, vv, vh, tilt) = result.sim.touchdown.expect("no touchdown");
    let descent = result.descent_s.expect("no descent-time measurement");
    assert!(
        descent <= acceptance.timeout_s,
        "touchdown at {descent:.0} s exceeds timeout {}",
        acceptance.timeout_s
    );
    assert_eq!(td, Touchdown::Nominal, "not a nominal landing: {td:?}");
    assert!(vv < acceptance.v_vert_max, "v_vert {vv} >= {}", acceptance.v_vert_max);
    assert!(vh < acceptance.v_horiz_max, "v_horiz {vh} >= {}", acceptance.v_horiz_max);
    assert!(
        tilt < acceptance.tilt_max_deg,
        "tilt {tilt} >= {}",
        acceptance.tilt_max_deg
    );

    // Alarms: run_headless returns Ok only if every alarm episode was
    // whitelisted (enter_p63 bails otherwise), so reaching here proves it;
    // assert the whitelists are the empty set the wave locked in.
    assert!(
        SPIKE_A_ALARM_WHITELIST.is_empty() && SPIKE_B_ALARM_WHITELIST.is_empty(),
        "acceptance assumes empty alarm whitelists"
    );

    // Drift and downlink health.
    assert!(result.drift_ms.abs() < 500.0, "drift {} ms", result.drift_ms);
    assert!(
        (40.0..=60.0).contains(&result.mid_downlink_wps),
        "downlink {} wps outside [40,60]",
        result.mid_downlink_wps
    );

    assert!(
        start.elapsed() < Duration::from_secs(WALL_BUDGET_S),
        "wall time budget exceeded"
    );
    touchdown_class(&result);
}

/// Error-model run (spec §8, graceful behavior only): the same gate with a
/// mild seeded IMU bias must still reach touchdown without a panic or a
/// non-whitelisted alarm — accuracy is NOT asserted. Gated behind
/// `EAGLE_SLOW=1` (not part of default `make test-integration`).
#[tokio::test]
#[ignore = "needs make agc artifacts + EAGLE_SLOW=1 (live, ~10 min)"]
async fn p66_landing_degrades_gracefully_under_imu_bias() {
    if std::env::var("EAGLE_SLOW").ok().as_deref() != Some("1") {
        eprintln!("skipping: set EAGLE_SLOW=1 to run the error-model descent");
        return;
    }
    let sc = Scenario::load(&root().join("scenarios/p66-gate-imu-bias.toml")).unwrap();
    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(root().join("build/agc/Luminary099.log")).unwrap(),
    )
    .unwrap();
    let manifest = PadloadManifest::load(&root().join(&sc.agc.padload)).unwrap();
    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19904,
    })
    .await
    .unwrap();
    let (telem_tx, _keep) = tokio::sync::broadcast::channel::<String>(4096);

    let result = tokio::time::timeout(
        Duration::from_secs(WALL_BUDGET_S),
        run_headless(HeadlessCfg {
            session,
            scenario: sc,
            symtab,
            manifest,
            telem_tx,
            latest: None,
            trace_out: None,
        }),
    )
    .await
    .expect("closed loop exceeded the wall-time budget")
    .expect("closed loop returned an error (non-whitelisted alarm or panic)");

    // Graceful: it reached touchdown at all. Classification is not asserted.
    assert!(
        result.sim.touchdown.is_some(),
        "error-model run never reached touchdown"
    );
}
