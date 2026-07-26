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
//!   in runs 4, 5 and 6 — the LAST THREE of the six — PDI → braking →
//!   approach → crew-takeover ROD, with P65 never entered and the radar
//!   bypassed in-rope. Runs 1-3 did not fly that sequence.
//! - `alarms.is_empty()` PASSES on all three: 0 episodes. **This assert is
//!   nearly information-free in PDI mode and must not be read as "no
//!   alarms during the descent."** `HeadlessResult.alarms` only ever
//!   receives `enter_p63_with_alarms`'s return value, and PDI
//!   `run_scenario` returns right after `wait_engine_on`
//!   (`runner.rs:1113-1115`), so nothing can append to it after ignition.
//!   Run 3 reported 0 episodes alongside 794 PROG-lamp frames. Its window
//!   is the PRE-IGNITION P63 dialog.
//! - `prog_lamp_frames == 0` passes on runs 4 and 6 and **FAILS on run 5**,
//!   which counted 21 — every one of them raised AFTER ground contact
//!   (lamp lights at t = 1192.62 s, contact at 1192.21 s), because this
//!   counter keeps running through the sim's ~2 s post-touchdown tail.
//!   Whether the gate should stop at contact is open and deliberately not
//!   answered by loosening it here (ledger "Open" item 2a). Run 3, which
//!   did enter P65, counted 794.
//!
//!   **KNOWN FALSE NEGATIVE — read this before debugging a red run.** That
//!   same ~2 s tail runs after a SOFT landing too, so ONE alarm raised
//!   inside it fails this gate on a flight that deserved to pass. If this
//!   assert is the only thing red and the touchdown block is green, check
//!   the lamp timestamps against `result.sim.touchdown` before changing
//!   anything. The gate is left wide on purpose: narrowing it to
//!   pre-contact frames would discard the only evidence this project has
//!   that the alarm exists, and its code is still unknown because nothing
//!   reads FAILREG after ENGINE ON in PDI mode.
//! - The clock gate PASSES: the AGC ran 0.944× real time on all three runs
//!   (0.949× on run 1), inside the ±10 % bound.
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
    // MEASURED PASSING in runs 4/5/6, the last three of six (2026-07-26).
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
    // Miss distance is REPORTED, never gated.
    //
    // PDI mode DOES have a pre-ignition freeze — the design doc's "runs
    // free from t=0" was overridden by the M1 plan, which governs, and
    // `SimCore::phase4_5_dynamics` pins truth position in BOTH gate modes
    // (only the freeze-phase PIPA feed differs: PDI = 0, hover = support).
    // So this still carries Wave 1's ω·R·cosφ × freeze artifact, unreduced:
    // run 6 froze for 3436 frames, t = 0.01 -> 343.51 s with `alt_m`
    // constant to the last digit, i.e. 1588.5 m of bookkeeping against
    // Wave 1's measured 1585.2 m.
    //
    // It also carries the frame/time-base caveat written at the top of
    // `scenarios/pdi-descent.toml` (in pdi mode the site is MCI +X at
    // TLAND, not the [site] lat/lon), and every flight that reported it was
    // a crash far off the nominal trajectory (runs 5/6: 12.2 / 12.1 km,
    // which swamps the artifact rather than removing it).
    //
    // A threshold therefore needs (a) the freeze phase to co-rotate and
    // (b) SEVERAL runs that flew the profile to contact — one flight fixes
    // no spread, so do not set a bound off the first green run either.
    eprintln!("[accept] miss distance {:.1} m", td.miss_m);

    // Alarms as OBSERVED by this run (printed above): no swallowed PROG
    // alarm is tolerated, not even one whose FAILREG read back zeros.
    // MEASURED PASSING in runs 4/5/6 — 0 episodes on all three.
    //
    // WINDOW: pre-ignition P63 dialog ONLY. `result.alarms` is exactly
    // `enter_p63_with_alarms`'s return value, and PDI `run_scenario`
    // returns right after `wait_engine_on` (`runner.rs:1113-1115`), so
    // nothing appends to it once the engine lights. Run 3 passed this
    // assert while counting 794 PROG-lamp frames. Green here says nothing
    // about the descent; `prog_lamp_frames` below is what covers that.
    assert!(
        result.alarms.is_empty(),
        "PROG alarm episodes during the descent: {:?}",
        result.alarms
    );
    // Lamp frames: 0 in runs 4 and 6, but 21 in run 5 — all of them AFTER
    // ground contact (the counter runs through the sim's ~2 s
    // post-touchdown tail; ledger "Open" item 2a). So this assert is the
    // one non-touchdown gate the measured flights do NOT unanimously meet,
    // and it is left strict on purpose: narrowing it to pre-contact frames
    // would make part of a crash pass, and nobody has yet named the code
    // (nothing reads FAILREG after ENGINE ON in PDI mode).
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
    // MEASURED ON THIS HOST — every M1 flight: 0.949× (run 1), 0.946×
    // (run 2), 0.945× (run 3), 0.944× (runs 4, 5 and 6), read off each
    // run's own `[accept]` line; Wave 1's re-flight measured 0.952×
    // (docs/superpowers/notes/2026-07-25-wave1-reflight.md:56,258 —
    // recomputed there from the final telemetry frame, since the
    // touchdown-class assert fired before the `[accept]` line printed).
    //
    // ±10 % keeps ~2× margin on the measured 5-6 % deficit while still
    // failing a stalled counter (rate → 0), a runaway one, or any ≥15 %
    // break.
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
