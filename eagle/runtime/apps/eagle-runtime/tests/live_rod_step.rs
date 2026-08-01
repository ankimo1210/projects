//! Open-loop step test for P66's ROD time constant (`TAUROD`).
//!
//! Live test: needs `make agc` artifacts; run with
//! `cargo test -p eagle-runtime --test live_rod_step -- --ignored --test-threads=1`
//! Budget: ~10-12 minutes (the same real-time TIG countdown as spike B,
//! plus ~1 minute of steps).
//!
//! # Why a step test and not a fit off a descent
//!
//! `TAUROD`'s b-scale is unresolved between 11 (the AGC reads the
//! committed 150 cs word as 0.1875 s) and 12 (0.375 s), against an
//! intended 1.5 s — see
//! `docs/superpowers/notes/2026-07-31-m1b-rod-loop.md`. Three regressions
//! against flight data failed to separate them, and the failure is
//! structural rather than an instrumentation gap: **a saturated relay
//! limit cycle carries almost no information about the linear gain inside
//! it.** The most convincing of the three (r² = 0.63) was fitting the
//! cycle's own quarter period — its r² is a periodic function of the
//! assumed command lag, peaking at 5.0 s against a measured 19.4 s period.
//!
//! So identify the loop the way spike B pinned `RODSCALE`: a controlled
//! live step, on the 1-D `SyntheticHover` model where there is no tilt, no
//! horizontal channel and no attitude coupling to confound it — and with
//! the **plant frozen** (`SyntheticHover::spawn_frozen_plant`), so the
//! AGC's own altitude rate is constant by construction.
//!
//! Freezing is not a convenience, it is the whole method. Attempt 1 used
//! the live plant and was meaningless: P63 parks the throttle at the DPS
//! idle stop for the entire ZOOMTIME phase, so the vehicle free-fell to
//! −47 m/s before P66 could take over, and `dHDOT` (−21.4 m/s over the
//! step window) swamped `dVDGVERT` (−0.30 m/s) by 70×. Waiting for a
//! quiescent window instead is circular — P66 limit-cycles precisely
//! because the constant being measured is wrong. See
//! `docs/superpowers/notes/2026-07-31-m1b-rod-loop.md` §7a.
//!
//! # The measurement
//!
//! P66 commands (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1041-1050`)
//!
//! ```text
//!   a_cmd = (VDGVERT - HDOTDISP) / TAUROD + g
//! ```
//!
//! Step `VDGVERT` by a known amount and everything else on the right-hand
//! side is either measured or cancels:
//!
//! ```text
//!   TAUROD = (dVDGVERT - dHDOT) / d(a_cmd),   and dHDOT ≡ 0 here
//! ```
//!
//! `dVDGVERT` is the click count times `RODSCALE` — 1 ft/s per click,
//! the one entry in `padload::P66_BSCALE_TABLE` marked `Verified` by live
//! measurement — and confirmed here by reading `VDGVERT` before and after.
//! `dHDOT` is zero because the frozen plant feeds a constant lunar-g
//! specific force, so the AGC integrates a vehicle whose rate never
//! changes; it is still computed and asserted small rather than assumed.
//! `d(a_cmd)` is the change in commanded thrust over mass.
//!
//! One down-click is chosen so the step lands inside the throttle band on
//! every candidate: at the spike's ~15 200 kg it moves roughly 1970 bits
//! at 0.1875 s, 990 at 0.375 s and 250 at 1.5 s, against a usable band of
//! ~3700 bits. Two step sizes are flown and must agree — that is what
//! catches a step that saturated or was DINC rate-limited, either of which
//! would truncate `d(a_cmd)` and inflate the answer.
use eagle_dynamics::constants::THRUST_N_PER_PULSE;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::padload::{generate_state, PadloadManifest, StateCfg, SymTab};
use eagle_runtime::runner::{
    self, DescentInit, HoverTruth, SyntheticHover, FLAGWRD3_ECADR, FLAGWRD8_ECADR,
    FLAGWRD8_MOON_BITS, REFSMBIT,
};
use eagle_runtime::script::{pump, DskyScript};
use std::path::PathBuf;
use std::time::Duration;
use tokio::sync::watch;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

/// One ROD click moves VDGVERT by 1 ft/s (`RODSCALE`, live-verified).
const ROD_CLICK_MS: f64 = 0.3048;

/// What the pad load intends `TAUROD` to be: 150 cs.
const INTENDED_TAU_S: f64 = 1.5;

/// Seconds to let the command settle after a step. The DINC output slews
/// at up to 800 bits/s, so the largest candidate step (~1970 bits) needs
/// ~2.5 s of slew, plus a guidance pass on either side.
const SETTLE_S: f64 = 5.0;

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

#[derive(Debug, Clone, Copy)]
struct Step {
    clicks: i16,
    cmd_before: i64,
    cmd_after: i64,
    vz_before: f64,
    vz_after: f64,
    mass_kg: f64,
    /// Commanded rate change, m/s.
    d_vdg_ms: f64,
    /// Truth rate change over the settle window, m/s.
    d_hdot_ms: f64,
    /// Commanded acceleration change, m/s².
    d_accel_ms2: f64,
    tau_s: f64,
}

/// Commanded force in newtons. `cmd_pulses` is the raw DINC accumulation,
/// i.e. what the AGC asked for, NOT the plant's clamped delivery — which
/// is what this measurement wants.
fn commanded_n(pulses: i64) -> f64 {
    pulses as f64 * THRUST_N_PER_PULSE
}

/// Sample the truth watch every 100 ms for `secs`, returning the last
/// value and the min/max commanded pulses seen (to spot a stop).
async fn observe(rx: &watch::Receiver<HoverTruth>, secs: f64) -> (HoverTruth, i64, i64) {
    let ticks = (secs * 10.0).round() as u32;
    let mut lo = i64::MAX;
    let mut hi = i64::MIN;
    let mut last = *rx.borrow();
    for _ in 0..ticks {
        tokio::time::sleep(Duration::from_millis(100)).await;
        last = *rx.borrow();
        lo = lo.min(last.cmd_pulses);
        hi = hi.max(last.cmd_pulses);
    }
    (last, lo, hi)
}

/// One step: read the baseline, click, let it settle, and solve for TAUROD.
async fn measure_step(
    script: &mut DskyScript,
    rx: &watch::Receiver<HoverTruth>,
    clicks: i16,
) -> Step {
    let before = *rx.borrow();
    let vdg_before = runner::read_dp(script, runner::VDGVERT_ECADR)
        .await
        .expect("VDGVERT before the step");

    let status = runner::rod_load(script, clicks)
        .await
        .expect("ROD load for the step");
    assert!(
        !status.rejected(),
        "the AGC refused the step's ROD load ({status:?}) — RODCOUNT unwritten, \
         so VDGVERT never moved and there is no step to measure"
    );

    let (after, _lo, _hi) = observe(rx, SETTLE_S).await;

    let vdg_after = runner::read_dp(script, runner::VDGVERT_ECADR)
        .await
        .expect("VDGVERT after the step");
    assert_ne!(
        vdg_after, vdg_before,
        "VDGVERT did not move: the load was accepted but had no effect"
    );

    let d_vdg_ms = f64::from(clicks) * ROD_CLICK_MS;
    let d_hdot_ms = after.vz_ms - before.vz_ms;
    // The frozen plant's contract. If this ever moves, the measurement is
    // back to attempt 1's failure mode and the number below is not a time
    // constant.
    assert!(
        d_hdot_ms.abs() < 0.01,
        "the plant is supposed to be frozen but the rate moved {d_hdot_ms} m/s —          dVDGVERT is {d_vdg_ms} m/s, so the step no longer dominates"
    );
    let d_accel_ms2 =
        (commanded_n(after.cmd_pulses) - commanded_n(before.cmd_pulses)) / before.mass_kg;

    Step {
        clicks,
        cmd_before: before.cmd_pulses,
        cmd_after: after.cmd_pulses,
        vz_before: before.vz_ms,
        vz_after: after.vz_ms,
        mass_kg: before.mass_kg,
        d_vdg_ms,
        d_hdot_ms,
        d_accel_ms2,
        // a_cmd = (VDG - H)/tau + g  ⇒  tau = (dVDG - dH) / da.
        tau_s: (d_vdg_ms - d_hdot_ms) / d_accel_ms2,
    }
}

fn report(s: &Step) {
    eprintln!(
        "[step] clicks {:+}  cmd {} -> {} bits ({:+} )  vz {:.3} -> {:.3} m/s  \
         mass {:.0} kg",
        s.clicks,
        s.cmd_before,
        s.cmd_after,
        s.cmd_after - s.cmd_before,
        s.vz_before,
        s.vz_after,
        s.mass_kg
    );
    eprintln!(
        "[step]   dVDGVERT {:+.4} m/s, dHDOT {:+.4} m/s, d(a_cmd) {:+.4} m/s^2  \
         => TAUROD = {:.4} s",
        s.d_vdg_ms, s.d_hdot_ms, s.d_accel_ms2, s.tau_s
    );
}

#[tokio::test]
#[ignore = "needs make agc artifacts (live step test, ~12 min)"]
async fn rod_step_measures_the_p66_time_constant() {
    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19906,
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

    // --- Spike B's proven boot → ignition sequence -----------------------
    tokio::time::sleep(Duration::from_secs(2)).await;
    init.script.keys("R").await.unwrap();
    init.script.keys("V37E00E").await.unwrap();
    init.script
        .wait_prog("00")
        .await
        .expect("P00 after V37E00E");

    let v1 = SyntheticHover::spawn(init.agc_tx.clone());
    let closed = SyntheticHover::spawn_frozen_plant(
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

    // --- P66 entry ------------------------------------------------------
    tokio::time::sleep(Duration::from_secs(2)).await;
    runner::att_hold(&init.agc_tx).await.expect("ATT HOLD");
    runner::rod_load(&mut init.script, -1)
        .await
        .expect("selection ROD click");
    init.script
        .wait_prog("66")
        .await
        .expect("GUILDENSTERN did not reach MM66");

    let truth = closed.truth().expect("closed-loop truth watch");

    // Let P66 take the throttle and reach a working point off the stops.
    // The vehicle cannot move, so this settles on the AGC's own terms.
    let (settled, lo, hi) = observe(&truth, 10.0).await;
    eprintln!(
        "[step] P66 working point: cmd {} bits (range {}..{} over 10 s), \
         vz {:.3} m/s, alt {:.1} m",
        settled.cmd_pulses, lo, hi, settled.vz_ms, settled.alt_m
    );
    assert!(
        settled.cmd_pulses > 0,
        "THRUST DINC loop never moved the actuator off its zero stop"
    );

    // --- Two steps, which must agree ------------------------------------
    let one = measure_step(&mut init.script, &truth, -1).await;
    report(&one);
    tokio::time::sleep(Duration::from_secs(5)).await;
    let two = measure_step(&mut init.script, &truth, -2).await;
    report(&two);

    let mean = (one.tau_s + two.tau_s) / 2.0;
    let spread = (one.tau_s - two.tau_s).abs() / mean.abs();
    eprintln!(
        "[step] TAUROD: {:.4} s and {:.4} s  (mean {:.4} s, spread {:.1} %)",
        one.tau_s,
        two.tau_s,
        mean,
        spread * 100.0
    );
    eprintln!(
        "[step] candidates — b=11: 0.1875 s, b=12: 0.375 s, b=14 (as shipped): {INTENDED_TAU_S} s"
    );

    // Validity first: a step that saturated or was DINC rate-limited
    // truncates d(a_cmd) and inflates tau, and it does so MORE for the
    // bigger step — so disagreement between the two is exactly that
    // signature. Without this gate a truncated measurement would read as a
    // clean answer.
    assert!(
        spread < 0.25,
        "the two steps disagree by {:.1} % ({:.4} s vs {:.4} s) — at least one \
         was saturated or rate-limited, so neither measures TAUROD",
        spread * 100.0,
        one.tau_s,
        two.tau_s
    );

    // The measurement itself. This is EXPECTED TO FAIL until TAUROD's
    // b-scale is corrected: the pad load intends 150 cs = 1.5 s, and the
    // open question is whether the AGC decodes that word as 0.1875 s
    // (b=11) or 0.375 s (b=12). A failure here naming a value near either
    // candidate is the measurement this test exists to make, not a bug in
    // the test.
    assert!(
        (mean - INTENDED_TAU_S).abs() / INTENDED_TAU_S < 0.20,
        "measured TAUROD = {mean:.4} s against the pad load's intended \
         {INTENDED_TAU_S} s — the b-scale is wrong; nearest candidate is {}",
        if (mean - 0.1875).abs() < (mean - 0.375).abs() {
            "b=11 (0.1875 s)"
        } else {
            "b=12 (0.375 s)"
        }
    );
}
