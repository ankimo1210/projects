//! Wave 1 acceptance (Task 16): the full Luminary099 closed loop against
//! our 6-DoF physics, asserting a P66 rate-of-descent landing to soft
//! touchdown. **This assertion does not hold today** — the run reaches
//! ground contact before P66 starts and classifies `Crash`; see
//! docs/superpowers/notes/2026-07-25-wave1-reflight.md for the measured
//! numbers and the two blockers.
//! Errors OFF. Live: needs `make agc`; run with
//! `cargo test -p eagle-runtime --test live_p66_descent -- --ignored --test-threads=1`.
//!
//! Timing note: the choreography reaches ENGINE ON ~350 s after boot (the
//! TIG countdown is real-time — Spike A), so the WHOLE run is ~8-11 min and
//! the scenario `timeout_s` is measured from ENGINE ON, not from boot. The
//! wall-time guard is set accordingly (the plan's 300 s predated the live
//! choreography timing).
use eagle_dynamics::touchdown::Touchdown;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::headless::{run_headless, touchdown_class, HeadlessCfg};
use eagle_runtime::padload::{PadloadManifest, SymTab};
use eagle_runtime::scenario::Scenario;
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
            client_rx: None,
            client_rod_rx: None,
        }),
    )
    .await
    .expect("closed loop exceeded the wall-time budget")
    .expect("closed loop returned an error");

    eprintln!(
        "[accept] MM {:?}\n[accept] touchdown {:?} descent {:?}s drift {:.0}ms downlink {:.1}wps",
        result.mm_sequence,
        result.sim.touchdown,
        result.descent_s,
        result.drift_ms,
        result.mid_downlink_wps
    );

    // MM sequence contains 63 then 66 (intervening modes allowed).
    let i63 = result.mm_sequence.iter().position(|m| m == "63");
    let i66 = result.mm_sequence.iter().position(|m| m == "66");
    assert!(
        matches!((i63, i66), (Some(a), Some(b)) if a < b),
        "MM sequence must contain 63 then 66: {:?}",
        result.mm_sequence
    );

    // Touchdown before timeout, Nominal by the scenario thresholds. All
    // velocities are surface-relative (the gate co-rotates; see
    // docs/coordinate-frames.md "Truth co-rotation").
    let td = result.sim.touchdown.expect("no touchdown");
    let descent = result.descent_s.expect("no descent-time measurement");
    assert!(
        descent <= acceptance.timeout_s,
        "touchdown at {descent:.0} s exceeds timeout {}",
        acceptance.timeout_s
    );
    assert_eq!(
        td.class,
        Touchdown::Nominal,
        "not a nominal landing: {:?}",
        td.class
    );
    assert!(
        td.v_vert_ms < acceptance.v_vert_max,
        "v_vert {} >= {}",
        td.v_vert_ms,
        acceptance.v_vert_max
    );
    assert!(
        td.v_horiz_ms < acceptance.v_horiz_max,
        "v_horiz {} >= {}",
        td.v_horiz_ms,
        acceptance.v_horiz_max
    );
    assert!(
        td.tilt_deg < acceptance.tilt_max_deg,
        "tilt {} >= {}",
        td.tilt_deg,
        acceptance.tilt_max_deg
    );
    // Miss distance is REPORTED, not gated. DO NOT turn the number printed
    // below into a threshold: it is currently ~100 % freeze artifact, not
    // guidance error. The sim pins the truth position in MCI through the
    // whole pre-ignition hold while MCMF keeps turning, so the arc is
    // ω·R·cos φ × (freeze duration) — a measured run returned 1585.2 m for
    // a 342.8 s freeze, which that product accounts for entirely; the
    // descent contributed nothing visible. Gating this today would bake
    // ~1.6 km of bookkeeping into the acceptance criteria. A threshold
    // becomes meaningful only after the freeze phase co-rotates (see
    // docs/coordinate-frames.md "Truth co-rotation"); re-measure then and
    // take the provenance from that run.
    eprintln!("[accept] miss distance {:.1} m", td.miss_m);

    // Alarms, as OBSERVED by this run: `enter_p63` aborts on a
    // non-whitelisted code, so anything reaching here was whitelisted and
    // silently acknowledged — the acceptance run tolerates none of it.
    assert!(
        result.alarms.is_empty(),
        "alarms acknowledged during entry: {:?}",
        result.alarms
    );
    // And after MM66 the P63 responder is gone, so the descent's PROG lamp
    // has no other watcher.
    assert_eq!(
        result.prog_lamp_frames, 0,
        "PROG alarm lamp lit during descent"
    );

    // Clock health: gate the AGC clock RATE, never the accumulated offset.
    // `drift_ms` is the observed downlink-word clock (words / 2 / 50 wps)
    // minus the sim TICK clock, which works out to
    //     drift_ms = t_s · 1000 · (downlink_wps / 50 − 1)
    //                + (epoch_s + DT) · 1000
    // — the constant is one tick, because `telemetry()` runs after the
    // state advance but before `tick_index` increments (so +10 ms at
    // epoch 0, negligible against the tolerance below). The t_s term is
    // the point: any steady rate difference grows without bound over a
    // ~600 s run, so no fixed millisecond bound is a property of the run.
    //
    // MEASURED ON THIS HOST — three full acceptance runs (this branch, its
    // parent, and the 2026-07-25 re-flight): drift = −17 900 ms with
    // mid_downlink_wps = 47.6. The re-flight also recorded the quantity
    // this assert actually gates, read off the FINAL telemetry frame:
    //     drift −17 900 ms over t_s = 369.61 s  ⇒  agc_rate = 0.952
    // (docs/superpowers/notes/2026-07-25-wave1-reflight.md, run 1). So the
    // gated number is 4.8 % low and the ±10 % bound below keeps ~2× margin
    // — no longer provisional. (The `[accept] AGC clock ...` line still has
    // not printed on a live run: the touchdown-class assert above fails
    // first, so the value was recomputed from the `EAGLE_TELEM_OUT` dump
    // by the same formula this code uses.)
    //
    // What the deficit IS remains under-determined. A slow AGC, a downlink
    // start dead-time D (which depresses a cumulative average
    // permanently), and downlink packets dropped by our own fan-out
    // (`headless.rs`'s packet forwarder does `RecvError::Lagged(_) =>
    // continue`, silently discarding them — indistinguishable here from a
    // slow AGC) all look identical in this number. A single sample only
    // constrains (D − sim pacing loss) ≈ 17.9 s; the `pacing lost` figure
    // printed below is what will separate them on the next run.
    //
    // ±10 % leaves ~2× margin on the measured deficit while still failing
    // a stalled counter (rate → 0), a runaway one, or any ≥15 % break; the
    // old 500 ms gate was 36× under the measured value on a healthy
    // emulator.
    const AGC_RATE_TOL: f64 = 0.10;
    assert!(
        result.final_t_s > 0.0,
        "no telemetry frames: cannot rate-check the AGC clock"
    );
    let agc_rate = 1.0 + result.drift_ms / 1000.0 / result.final_t_s;
    eprintln!(
        "[accept] AGC clock {:.3}x real time (drift {:.0} ms over {:.1} s sim); \
         sim pacing lost {:.0} ms",
        agc_rate, result.drift_ms, result.final_t_s, result.sim.pacing_lost_ms
    );
    assert!(
        (agc_rate - 1.0).abs() < AGC_RATE_TOL,
        "AGC clock rate {agc_rate:.3}x real time (drift {} ms over {} s)",
        result.drift_ms,
        result.final_t_s
    );
    // Same counter, earlier cutoff, looser bound. NOT a windowed rate:
    // `sim.rs` computes `downlink_wps` as a CUMULATIVE average from t = 0
    // (the whole pre-ignition freeze included), so this and the rate above
    // are the same running average read at two different cutoffs — one at
    // a mid-descent frame, one at the last frame — not two independent
    // windows. Kept as a coarse cross-check; the ±10 % gate above is the
    // one that bounds clock health.
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
            client_rx: None,
            client_rod_rx: None,
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
