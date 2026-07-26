//! Wave 2 M1 acceptance: the real Luminary099 flies PDI → P63 → P64 → P66
//! to touchdown against our physics, landing radar bypassed in-rope
//! (LRBYPASS — verified, not set: a fresh start already sets FLAGWRD11
//! bit 15, `vendor/virtualagc/Luminary099/FRESH_START_AND_RESTART.agc:623`),
//! errors OFF. Live: needs `make agc`; run with
//! `cargo test -p eagle-runtime --test live_pdi_descent -- --ignored --test-threads=1`.
//!
//! **STATUS 2026-07-26: this test has NEVER been run green — it has never
//! been run at all.** It is the frozen M1 target, written after the flight
//! budget (6 of 6) was spent, and it is expected to FAIL today on the
//! touchdown block below. What six instrumented flights measured
//! (`docs/superpowers/notes/2026-07-26-m1-pdi-flight.md`):
//!
//! - The mode assert PASSES on the measured sequence: `["00","63","64","66"]`
//!   in runs 4, 5 and 6 — PDI → braking → approach → crew-takeover ROD, with
//!   P65 never entered and the radar bypassed in-rope.
//! - The alarm asserts PASS on the same runs: 0 episodes, 0 PROG-lamp
//!   frames after ignition (against 794 lamp frames in run 3, which did go
//!   through P65).
//! - The clock gate PASSES: the AGC ran 0.944-0.952× real time on this
//!   host, inside the ±10 % bound.
//! - **The touchdown block FAILS.** P66's rate loop limit-cycles — run 6
//!   ran the throttle stop-to-stop (0 → 48 132 N) for 218 s with the sink
//!   rate spanning −34.1 to +16.2 m/s — and nothing flies the attitude in
//!   a crewless P66, so the vehicle contacts at v_vert 30.86 m/s, v_horiz
//!   60.04 m/s, tilt 12.8°, classified `Crash`.
//!
//! The thresholds asserted here are the scenario's, and they are the DESIGN
//! limits, deliberately not relaxed to what was measured — see the
//! `[acceptance]` block of `scenarios/pdi-descent.toml`. Do not weaken them
//! to make this green; the open blockers are named in the ledger note
//! ("Open", items 1/1a/2/3).
//!
//! Wall clock: ~20 min. The sim thread is wall-paced at 10 ms/tick, so sim
//! seconds are wall seconds: run 6 reached ENGINE ON at t = 343.6 s and
//! contact 865.1 s later, i.e. ~1209 s of run plus boot and teardown. The
//! budget below keeps ~50 % margin on that.
use eagle_dynamics::touchdown::Touchdown;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::headless::{run_headless, HeadlessCfg};
use eagle_runtime::padload::{PadloadManifest, SymTab};
use eagle_runtime::scenario::Scenario;
use std::path::PathBuf;
use std::time::Duration;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

const WALL_BUDGET_S: u64 = 1800;

#[tokio::test]
#[ignore = "needs make agc artifacts (live acceptance, ~20 min)"]
async fn pdi_full_descent_closed_loop() {
    let sc = Scenario::load(&root().join("scenarios/pdi-descent.toml")).unwrap();
    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(root().join("build/agc/Luminary099.log")).unwrap(),
    )
    .unwrap();
    let manifest = PadloadManifest::load(&root().join(&sc.agc.padload)).unwrap();

    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19905,
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
            trace_out: Some(root().join("build/traces/pdi-acceptance.jsonl")),
            client_rx: None,
            client_rod_rx: None,
        }),
    )
    .await
    .expect("closed loop exceeded the wall-time budget")
    .expect("closed loop returned an error");

    // ---------------------------------------------------------------
    // DIAGNOSTICS FIRST — every measured number this run produced, printed
    // BEFORE any assert. A failing assert unwinds the test, so a
    // diagnostic below one never prints on the very run that needed it
    // (Wave 1's final-review lesson: the 2026-07-25 re-flight had to
    // hand-compute `agc_rate` from the telemetry dump because the
    // touchdown-class assert fired first). Keep every `eprintln!` in this
    // block; put nothing but asserts below it.
    // ---------------------------------------------------------------
    eprintln!("[accept] MM {:?}", result.mm_sequence);
    eprintln!(
        "[accept] touchdown {:?}; descent {:?} s from ENGINE ON",
        result.sim.touchdown, result.descent_s
    );
    eprintln!(
        "[accept] alarm episodes {:?}; PROG lamp frames after ignition {}",
        result.alarms, result.prog_lamp_frames
    );
    let agc_rate = if result.final_t_s > 0.0 {
        1.0 + result.drift_ms / 1000.0 / result.final_t_s
    } else {
        f64::NAN
    };
    eprintln!(
        "[accept] AGC clock {:.3}x real time (drift {:.0} ms over {:.1} s sim); \
         sim pacing lost {:.0} ms; downlink {:.1} wps",
        agc_rate,
        result.drift_ms,
        result.final_t_s,
        result.sim.pacing_lost_ms,
        result.mid_downlink_wps
    );
    // MM65 is a FINDING, not a failure: the spec (§3 M1) says its
    // appearance means the handover altitude needs revisiting, and the
    // flights agree — the two runs that entered P65 (3 and 2) both raised
    // an unidentified PROG alarm within 0.35 s of the MM64→MM65 switch and
    // the guidance stopped modulating the throttle. `[handover] alt_m` is
    // 250 m precisely to fire inside P64.
    if result.mm_sequence.iter().any(|m| m == "65") {
        eprintln!(
            "[accept] FINDING: MM65 appeared — handover altitude needs revisiting \
             (spec §3 M1; ledger note 'Open' item 2)"
        );
    }

    // Mode order: 63 then 64 then 66 (intervening modes allowed).
    // MEASURED PASSING in runs 4/5/6 (2026-07-26).
    let idx = |mm: &str| result.mm_sequence.iter().position(|m| m == mm);
    let (i63, i64_, i66) = (idx("63"), idx("64"), idx("66"));
    assert!(
        matches!((i63, i64_, i66), (Some(a), Some(b), Some(c)) if a < b && b < c),
        "MM sequence must contain 63 then 64 then 66: {:?}",
        result.mm_sequence
    );

    // Touchdown before the timeout, Nominal by the scenario thresholds.
    // All velocities are surface-relative (the gate co-rotates; see
    // docs/coordinate-frames.md "Truth co-rotation").
    // NOT MET as of 2026-07-26 — see the module doc: run 6 contacted at
    // 30.86 / 60.04 m/s and 12.8° of tilt, classified `Crash`.
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
    // Miss distance is REPORTED, never gated. PDI mode has no pre-ignition
    // freeze, so it no longer carries Wave 1's ω·R·cosφ × freeze artifact —
    // but it still carries the frame/time-base caveat written at the top of
    // `scenarios/pdi-descent.toml` (in pdi mode the site is MCI +X at
    // TLAND, not the [site] lat/lon), and the flights that reported it were
    // all crashes off the nominal trajectory (run 3: 11.2 km). A threshold
    // needs provenance from a run that actually flew the profile to
    // contact, which has not happened.
    eprintln!("[accept] miss distance {:.1} m", td.miss_m);

    // Alarms as OBSERVED by this run (printed above): no swallowed PROG
    // alarm is tolerated, not even one whose FAILREG read back zeros.
    // MEASURED PASSING in runs 4/5/6 — 0 episodes, 0 lamp frames.
    assert!(
        result.alarms.is_empty(),
        "PROG alarm episodes during the descent: {:?}",
        result.alarms
    );
    assert_eq!(
        result.prog_lamp_frames, 0,
        "PROG alarm lamp lit during descent"
    );

    // Clock health: gate the AGC clock RATE, never the accumulated offset —
    // any steady rate difference grows without bound over a ~1200 s run, so
    // no fixed millisecond bound is a property of the run. `drift_ms` is
    // the observed downlink-word clock minus the sim TICK clock; the
    // derivation and the "what the deficit IS" caveat are in
    // `live_p66_descent.rs`, which gates the same quantity.
    //
    // MEASURED ON THIS HOST — Wave 1 acceptance runs 0.952×; M1 flights 1
    // and 4 measured 0.949× and 0.944× over ~1000 s of PDI descent
    // (docs/superpowers/notes/2026-07-26-m1-pdi-flight.md). ±10 % keeps
    // ~2× margin on the measured 5-6 % deficit while still failing a
    // stalled counter (rate → 0), a runaway one, or any ≥15 % break.
    const AGC_RATE_TOL: f64 = 0.10;
    assert!(
        result.final_t_s > 0.0,
        "no telemetry frames: cannot rate-check the AGC clock"
    );
    assert!(
        (agc_rate - 1.0).abs() < AGC_RATE_TOL,
        "AGC clock rate {agc_rate:.3}x real time (drift {} ms over {} s)",
        result.drift_ms,
        result.final_t_s
    );
}
