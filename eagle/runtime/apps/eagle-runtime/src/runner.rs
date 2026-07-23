//! Spike A (Task 6): scripted boot → pad-load → P63 → ignition against the
//! live Luminary099/yaAGC. The choreography here is the *empirically
//! confirmed* dialog (see `.superpowers/sdd/task-6-report.md` and the
//! ledger); the vendor citations on each step are the static-analysis
//! starting points that the live runs validated or corrected.

use crate::padload::PadWord;
use crate::script::DskyScript;
use anyhow::{bail, ensure, Context, Result};
use eagle_agc_protocol::agc_io::{decode_output, discrete_write, pipa_pulse, AgcOutput, PipaAxis};
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::words::octal5;
use eagle_agc_protocol::Packet;
use eagle_dynamics::constants::PIPA_INCR;
use std::time::Duration;
use tokio::sync::{broadcast, mpsc};

// ---------------------------------------------------------------------
// Boot discretes.
//
// LM_Simulator's channel init strings (lm_simulator.tcl:570-577), inverted
// logic (0 = asserted). Hand re-derivation of the three non-trivial
// conversions (binary strings are the source of truth, MSB = bit 15):
//   wdata(30) = 011 110 011 011 001₂ = 0o36331
//   wdata(32) = 010 001 111 111 111₂ = 0o21777
//   wdata(33) = 101 111 111 111 110₂ = 0o57776
// For P63/P66 we additionally assert AUTO THROTTLE (ch30 bit5, value
// 0o20): 0o36331 & !0o20 = 0o36311 — GUILDENSTERN selects P67 whenever
// the un-auto-throttle discrete appears (LUNAR_LANDING_GUIDANCE_EQUATIONS
// .agc:139-146), and P40AUTO checks it pre-ignition (BURN,_BABY,_BURN:923).
// ---------------------------------------------------------------------

/// ch 030 init: ENGINE ARMED (bit3), AUTO THROTTLE (bit5), IMU OPERATE
/// (bit9), LGC HAS CONTROL (bit10), SM TEMP OK (bit15) asserted.
pub const INIT_CH30: u16 = 0o36311; // LM_Sim 0o36331 & !0o20 (bit5 → computer throttle)
/// ch 031 init: AUTO mode — bit14 (0o20000) asserted, everything else
/// (RHC/THC/att-hold/detent) deasserted. LM_Sim boots all-ones (DAP off);
/// AUTO is required by P40AUTO's G+N,AUTO check.
pub const INIT_CH31: u16 = 0o57777;
/// ch 032 init, straight from LM_Sim wdata(32).
pub const INIT_CH32: u16 = 0o21777;
/// ch 033 init, straight from LM_Sim wdata(33). NOTE: bit6 (LR antenna in
/// position 1) is NOT asserted here; P63SPOT3 checks it and flashes
/// V50N25 code 00500 until it appears — the responder asserts it then
/// (mirroring the crew "cranking the thing around").
pub const INIT_CH33: u16 = 0o57776;
/// ch 031 with ATT HOLD instead of AUTO: bit13 (0o10000) asserted, bit14
/// clear — the mode transition that triggers GUILDENSTERN → P66.
pub const CH31_ATT_HOLD: u16 = 0o67777;

/// ch 030 bit9 IMU OPERATE (INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc).
pub const CH30_BIT9_IMU_OPERATE: u16 = 1 << 8;
/// ch 030 bit14 ISS TURN-ON REQUEST: asserted (low) together with IMU
/// OPERATE at power-up; the AGC answers ~90 s later with ch 012 bit15
/// (ISS TURN-ON DELAY COMPLETE), whereupon the "IMU" (us) drops the
/// request. LM_Simulator models this as the crew switch "ISS TURN ON
/// REQUESTED" (doc/tutorial.txt §1.1).
pub const CH30_BIT14_ISS_REQ: u16 = 1 << 13;
/// ch 012 bit15 ISS TURN-ON DELAY COMPLETE (AGC output).
pub const CH12_BIT15_ISS_DELAY_DONE: u16 = 1 << 14;
/// ch 033 bit6 LR ANTENNA IN POSITION 1 (P63SPOT3 reads it via
/// `CA BIT6, RAND CHAN33`, THE_LUNAR_LANDING.agc:243-247).
pub const CH33_BIT6_LR_POS1: u16 = 1 << 5;

/// FLAGWRD3 = STATE +3, unswitched ECADR 0o77 (Luminary099.log:2703:
/// `26,2022  0077  FLAGWRD3 = STATE +3`; STATE = 0o74). REFSMFLG is its
/// BIT13 (FLAGWORD_ASSIGNMENTS.agc:475-476).
pub const FLAGWRD3_ECADR: u16 = 0o77;
/// REFSMBIT = BIT13 (FLAGWORD_ASSIGNMENTS.agc:476).
pub const REFSMBIT: u16 = 0o10000;
/// FLAGWRD8 = STATE +8, ECADR 0o104 (Luminary099.log:3065). CMOONFLG =
/// BIT12, LMOONFLG = BIT11 (FLAGWORD_ASSIGNMENTS.agc:853,857): the
/// permanent CSM/LM state vectors are moon-centered. Deliberately NOT
/// initialized by fresh start (LUM69R2/PADLOADS.agc:72-76) — pad-loaded.
pub const FLAGWRD8_ECADR: u16 = 0o104;
/// CMOONFLG | LMOONFLG.
pub const FLAGWRD8_MOON_BITS: u16 = 0o4000 | 0o2000;

/// TIME2/TIME1 master clock, unswitched 0o24/0o25; TIME2 counts TIME1
/// overflows (2^14 cs each).
pub const TIME2_ECADR: u16 = 0o24;
pub const TIME1_ECADR: u16 = 0o25;

/// Alarm codes the frozen spike test tolerates. EMPTY: the final
/// choreography completes boot → pad-load → P63 → ENGINE ON with FAILREG
/// = 00000/00000/00000 (spike-A iter 20 and the frozen runs) — every
/// alarm met along the way was diagnosed and eliminated with DATA, never
/// masked:
/// - 01204 (zero-dt WAITLIST POODOO) twice: R03's TRIMGIMB with zero
///   PITTIME/ROLLTIME (answered N48 with V34E instead of PRO), and TIG-0's
///   WAITLIST(ZOOMTIME) with the ZOOMTIME pad word missing (added, 2600 cs).
/// - 01406 (ROOTPSRS TTF abort): REFSMMAT must equal the descent guidance
///   frame (IGNALG pass 1 runs with CG = identity).
/// - 00213/00220 (IMU turn-on/alignment) never fired: ch30 bit9+bit14 are
///   asserted together at init and REFSMFLG is verified before V37E63E.
///
/// Task 16 imports this list; grow it only with a diagnosed, cited entry.
pub const SPIKE_A_ALARM_WHITELIST: &[u16] = &[];

/// Handles produced by `pump` for one live AGC, bundled for the descent
/// choreography (Tasks 7/14/16 consume this shape).
pub struct DescentInit {
    pub script: DskyScript,
    pub packets: broadcast::Receiver<Packet>,
    pub agc_tx: mpsc::UnboundedSender<Packet>,
}

/// Full-word initialization of input channels 030-033 (we own every bit
/// at init time; later mutations go through `discrete_write` pairs so
/// they touch only their own bits). Also asserts the ISS turn-on request
/// (ch30 bit14) in the same breath as IMU OPERATE, mirroring an IMU that
/// is powered when the AGC first samples it.
pub async fn init_discretes(tx: &mpsc::UnboundedSender<Packet>) -> Result<()> {
    for (ch, word) in [
        (0o30u8, INIT_CH30),
        (0o31, INIT_CH31),
        (0o32, INIT_CH32),
        (0o33, INIT_CH33),
    ] {
        tx.send(Packet::io(ch, word).context("packet")?)
            .context("agc tx closed")?;
    }
    // ISS turn-on request: assert (drive low) bit14 of ch30.
    for p in discrete_write(0o30, 0, CH30_BIT14_ISS_REQ) {
        tx.send(p).context("agc tx closed")?;
    }
    Ok(())
}

/// Wait for the AGC's ISS turn-on delay complete (ch 012 bit15, ~90 s
/// after `init_discretes`), then drop the turn-on request like the real
/// ISS would. Returns the elapsed wait.
pub async fn wait_iss_turnon(
    packets: &mut broadcast::Receiver<Packet>,
    tx: &mpsc::UnboundedSender<Packet>,
    timeout: Duration,
) -> Result<Duration> {
    let start = tokio::time::Instant::now();
    let deadline = start + timeout;
    loop {
        let pkt = tokio::select! {
            r = packets.recv() => r,
            _ = tokio::time::sleep_until(deadline) => {
                bail!("ISS turn-on delay complete (ch12 bit15) not seen within {timeout:?}");
            }
        };
        match pkt {
            Ok(p) if p.channel == 0o12 && p.data & CH12_BIT15_ISS_DELAY_DONE != 0 => break,
            Ok(_) => {}
            Err(broadcast::error::RecvError::Lagged(_)) => {} // keep waiting
            Err(broadcast::error::RecvError::Closed) => bail!("packet stream closed"),
        }
    }
    for p in discrete_write(0o30, CH30_BIT14_ISS_REQ, 0) {
        tx.send(p).context("agc tx closed")?;
    }
    Ok(start.elapsed())
}

/// Read the AGC master clock as centiseconds: TIME2·2^14 + TIME1, with a
/// TIME2 re-read to defeat the overflow race (TIME1 wraps every 163.84 s).
pub async fn read_clock_cs(script: &mut DskyScript) -> Result<f64> {
    for _ in 0..3 {
        let hi = script.read_erasable(TIME2_ECADR).await?;
        let lo = script.read_erasable(TIME1_ECADR).await?;
        let hi2 = script.read_erasable(TIME2_ECADR).await?;
        if hi == hi2 {
            return Ok(f64::from(hi) * 16384.0 + f64::from(lo));
        }
    }
    bail!("TIME2 kept changing across three read attempts");
}

/// V48 (R03) DAP data load. Live-confirmed dialog (spike-A iters 4-13):
/// V48E → FL **V01N46** (octal DAPDATR1, fresh-start default 21112 =
/// ascent+descent config; the LM_Simulator tutorial's "V04N46" applies
/// to a different rope) → PRO → FL V06N47 (R1/R2 = LM/CSM weight in
/// whole pounds — WEIGHT2 "XXXXX. LBS", PINBALL_NOUN_TABLES.agc:88,450;
/// confirmed live by the AGC redisplaying 33500 as +33502 after its
/// lbs→kg→lbs round-trip) → V24E loads both → PRO (DAPDAT2 sets MASS,
/// deadband, moments of inertia) → FL V06N48 (gimbal trim) →
/// **V34E TERMINATE**, deliberately NOT PRO: PRO starts the TRIMGIMB
/// gimbal-centering drive (EXTENDED_VERBS.agc DPDAT3 → WAITLIST →
/// P40-P47.agc:1384), which FIXDELAYs 60 s at full +pitch/+roll and then
/// calls TWIDDLE/VARDELAY with PITTIME/ROLLTIME — zero on a cold AGC —
/// and a zero-dt waitlist call POODOOs 01204 (WAITPOOH, WAITLIST.agc:574)
/// exactly 60 s after the PRO (spike-A iters 10-13, reproduced 3x with
/// FAILREG=01204). Everything the descent needs from R03 is already set
/// by the N47 step; the trim drive only centers physical gimbal hardware
/// we don't model in Spike A.
pub async fn dap_init(
    script: &mut DskyScript,
    lm_weight_lbs: u32,
    csm_weight_lbs: u32,
) -> Result<()> {
    ensure!(
        lm_weight_lbs <= 99999 && csm_weight_lbs <= 99999,
        "N47 is XXXXX lbs"
    );
    script.keys("V48E").await?;
    script
        .wait_flash("01", "46")
        .await
        .context("V48: expected FL V01N46")?;
    script.pro().await?;
    script
        .wait_flash("06", "47")
        .await
        .context("V48: expected FL V06N47")?;
    script
        .keys(&format!("V24E+{lm_weight_lbs:05}E+{csm_weight_lbs:05}E"))
        .await?;
    script
        .wait_flash("06", "47")
        .await
        .context("V48: FL V06N47 after V24 load")?;
    script.pro().await?;
    script
        .wait_flash("06", "48")
        .await
        .context("V48: expected FL V06N48")?;
    script.keys("V34E").await?; // terminate R03; do NOT start TRIMGIMB
    Ok(())
}

/// ECADRs that `apply_padload` read-back-verifies REGARDLESS of the
/// sparse stride ("every 8th word + all words the spike ever saw fail",
/// per the brief). No word ever failed a live read-back during the spike
/// (0 drops in ~20 runs at 30 ms key delay), so the seed is the one word
/// whose *absence* cost the most: ZOOMTIME (E7,1422 = 0o3422) — zero
/// there POODOOs 01204 at TIG-0, one instruction before ENGINE ON
/// (spike-A iters 18-19). A stride of 8 over the static manifest happens
/// to skip it, which is exactly why the always-set exists.
pub const ALWAYS_VERIFY_ECADRS: &[u16] = &[0o3422];

/// Uplink a resolved pad-load via V21N01, verifying every `verify_every`-th
/// word with a V01N01 read-back (0 = stride verifies nothing; 1 = every
/// word). Words whose ECADR is in `always_verify` are read-back-verified
/// even when the stride would skip them (pass `ALWAYS_VERIFY_ECADRS`).
/// Zero words are skipped outright: yaAGC cold-boots with zeroed
/// erasable (`--no-resume`), so they are no-ops — this only holds on a
/// fresh boot, which is the only mode the spike test runs in.
pub async fn apply_padload(
    script: &mut DskyScript,
    words: &[PadWord],
    verify_every: usize,
    always_verify: &[u16],
) -> Result<()> {
    let mut loaded = 0usize;
    for w in words {
        if w.word == 0 {
            continue;
        }
        let verify = (verify_every > 0 && loaded.is_multiple_of(verify_every))
            || always_verify.contains(&w.ecadr);
        if verify {
            script
                .load_erasable(w.ecadr, w.word)
                .await
                .with_context(|| format!("pad-load word @{}", octal5(w.ecadr)))?;
        } else {
            script
                .keys(&format!("V21N01E{}E{}E", octal5(w.ecadr), octal5(w.word)))
                .await?;
        }
        loaded += 1;
    }
    Ok(())
}

/// OR `mask` into an erasable flag word (read-modify-write over the DSKY,
/// verified by re-read). Used for REFSMFLG and the FLAGWRD8 moon bits.
pub async fn set_flag_bits(script: &mut DskyScript, ecadr: u16, mask: u16) -> Result<()> {
    let cur = script.read_erasable(ecadr).await?;
    if cur & mask != mask {
        let want = cur | mask;
        script
            .keys(&format!("V21N01E{}E{}E", octal5(ecadr), octal5(want)))
            .await?;
        tokio::time::sleep(Duration::from_millis(200)).await;
    }
    let after = script.read_erasable(ecadr).await?;
    ensure!(
        after & mask == mask,
        "flag bits {:05o} @{:05o} did not latch (read {:05o})",
        mask,
        ecadr,
        after
    );
    Ok(())
}

// ---------------------------------------------------------------------
// P63 entry + PRO-on-flash responder.
// ---------------------------------------------------------------------

/// What the responder does with a given flashing display.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FlashAction {
    /// Key PRO.
    Pro,
    /// Key ENTR.
    Entr,
    /// Assert LR antenna position 1 (ch33 bit6) then PRO.
    LrPos1ThenPro,
    /// Final "please enable engine" (V99Nxx): PRO, then the dialog is done.
    ProAndDone,
    /// Not a dialog we recognize.
    Unknown,
}

/// Dialog table for the P63 → ignition sequence, from the vendor flow
/// pinned in Step 0 and confirmed live (see task-6 report):
///
/// - FL V06N61 (TTG/±xx display via ASTNCLOK, THE_LUNAR_LANDING.agc:214-218)
///   → PRO ("proceed" hands off to R51P63 via ASTNRETN).
/// - FL V50N25 R1=00014 (R51P63 fine-align offer, P51-P53.agc:724-731) →
///   ENTR: "ENTER will return to P63SPOT2" — PRO here would start a fine
///   alignment we neither need nor can complete.
/// - FL V50N18 (R60 attitude maneuver request) → PRO the first time (auto
///   maneuver; our REFSMMAT puts the burn attitude at our parked CDUs so
///   it is near-null), ENTR on a repeat (accept attitude, exit R60).
/// - FL V50N25 R1=00500 ("PLEASE CRANK THE SILLY THING AROUND",
///   THE_LUNAR_LANDING.agc:249-253) → assert ch33 bit6 then PRO.
/// - FL V99Nxx ("PLEASE ENABLE ENGINE", BURN,_BABY,_BURN:778-790) → PRO
///   sets ASTNFLAG; IGNITION fires at TIG-0 → done.
/// - Anything else flashing → PRO after a debounce (the brief's default),
///   handled by the caller via `Unknown`.
pub fn classify_flash(verb: &str, noun: &str, r1: &str, v50n18_seen: u32) -> FlashAction {
    match (verb, noun) {
        ("99", _) => FlashAction::ProAndDone,
        ("50", "25") => match r1.trim_start_matches([' ', '+', '-']) {
            "00014" => FlashAction::Entr,
            "00500" => FlashAction::LrPos1ThenPro,
            _ => FlashAction::Unknown,
        },
        ("50", "18") => {
            if v50n18_seen == 0 {
                FlashAction::Pro
            } else {
                FlashAction::Entr
            }
        }
        ("06", "61") => FlashAction::Pro,
        _ => FlashAction::Unknown,
    }
}

fn reg1_string(d: &DskyState) -> String {
    std::iter::once(d.r1.sign).chain(d.r1.digits).collect()
}
fn vn_strings(d: &DskyState) -> (String, String) {
    (d.verb.iter().collect(), d.noun.iter().collect())
}

/// V37E63E, then run the flash responder until the V99 engine-enable
/// request has been answered with PRO (or fail on non-whitelisted PROG
/// alarm / timeout / dialog loop). A PROG alarm whose FAILREG codes are
/// all in `SPIKE_A_ALARM_WHITELIST` (∪ {0}) is acknowledged with RSET +
/// KEY REL and the dialog continues; any other code aborts with the
/// codes in the error. Engine-on itself is asserted by the caller on the
/// raw packet stream (ch 011 bit13) — it arrives at TIG-0, after this
/// function returns.
pub async fn enter_p63(script: &mut DskyScript) -> Result<()> {
    // Budget: the frozen choreography reaches ENGINE ON ~174 s after
    // V37E63E (IGNALG ~5 s + dialog + burn_lead countdown); 600 s ≈ 3.4×
    // margin also covers BURNBABY's TIG-slip path (+30 s) and a slow
    // IGNALG without masking a genuine hang for the whole test timeout.
    const TIMEOUT: Duration = Duration::from_secs(600);
    script.keys("V37E63E").await?;
    script
        .wait_prog("63")
        .await
        .context("MM did not reach 63 after V37E63E (V37 rejected?)")?;

    let deadline = tokio::time::Instant::now() + TIMEOUT;
    let mut v50n18_seen = 0u32;
    let mut last_responded: Option<(String, String, String)> = None;
    let mut repeats = 0u32;

    loop {
        ensure!(
            tokio::time::Instant::now() < deadline,
            "P63 dialog timed out"
        );
        // Wait for either a flashing display or the PROG alarm lamp.
        let d = script
            .wait(deadline - tokio::time::Instant::now(), |d| {
                d.verb_noun_flash || d.lamps.prog_alarm
            })
            .await
            .context("waiting for P63 dialog")?;
        if d.lamps.prog_alarm {
            let codes = script.alarm_codes().await.unwrap_or([0; 3]);
            let whitelisted = codes
                .iter()
                .all(|c| *c == 0 || SPIKE_A_ALARM_WHITELIST.contains(c));
            if !whitelisted {
                bail!(
                    "PROG alarm during P63 entry: FAILREG = {:05o} {:05o} {:05o}",
                    codes[0],
                    codes[1],
                    codes[2]
                );
            }
            // Whitelisted: acknowledge like the crew would (RSET clears
            // the lamp — sanctioned for whitelisted codes only), release
            // the display back to the flashing program, and continue.
            script.keys("R").await?;
            script.keys("K").await?;
            continue;
        }
        // Debounce: let the display settle, then re-read.
        tokio::time::sleep(Duration::from_secs(1)).await;
        let d = script
            .wait(Duration::from_secs(10), |d| d.verb_noun_flash)
            .await;
        let Ok(d) = d else { continue }; // flash cleared while we debounced
        let (verb, noun) = vn_strings(&d);
        let r1 = reg1_string(&d);

        let key = (verb.clone(), noun.clone(), r1.clone());
        if last_responded.as_ref() == Some(&key) {
            repeats += 1;
            ensure!(
                repeats < 6,
                "dialog loop: {key:?} keeps flashing after responses"
            );
        } else {
            repeats = 0;
        }

        match classify_flash(&verb, &noun, &r1, v50n18_seen) {
            FlashAction::Pro => {
                if (verb.as_str(), noun.as_str()) == ("50", "18") {
                    v50n18_seen += 1;
                }
                script.pro().await?;
            }
            FlashAction::Entr => {
                if (verb.as_str(), noun.as_str()) == ("50", "18") {
                    v50n18_seen += 1;
                }
                script.keys("E").await?;
            }
            FlashAction::LrPos1ThenPro => {
                for p in discrete_write(0o33, 0, CH33_BIT6_LR_POS1) {
                    script.send(p)?;
                }
                tokio::time::sleep(Duration::from_millis(300)).await;
                script.pro().await?;
            }
            FlashAction::ProAndDone => {
                script.pro().await?;
                return Ok(());
            }
            FlashAction::Unknown => {
                // Brief default: PRO on any unrecognized flash (after the
                // debounce above). The repeat guard bounds runaway loops.
                script.pro().await?;
            }
        }
        last_responded = Some(key);
        // Give the program a beat to take down the answered display so we
        // don't immediately re-answer the same frame.
        let _ = script
            .wait(Duration::from_secs(5), {
                let prev = vn_strings(&d);
                move |d| !d.verb_noun_flash || vn_strings(d) != prev
            })
            .await;
    }
}

/// Wait for ENGINE ON (ch 011 bit13 → `AgcOutput::Engine { on: true }`)
/// on the raw packet stream, simultaneously counting downlink packets
/// (ch 034/035). Returns the mean downlink packet rate over the wait —
/// NOTE this includes any buffered backlog, so it over-reads after a
/// long non-consuming stretch; use `measure_downlink_rate` for a honest
/// steady-state figure.
pub async fn wait_engine_on(
    packets: &mut broadcast::Receiver<Packet>,
    timeout: Duration,
) -> Result<f64> {
    let start = tokio::time::Instant::now();
    let deadline = start + timeout;
    let mut downlink = 0u64;
    loop {
        let pkt = tokio::select! {
            r = packets.recv() => r,
            _ = tokio::time::sleep_until(deadline) => {
                bail!("ENGINE ON not observed within {timeout:?}");
            }
        };
        match pkt {
            Ok(p) => match decode_output(&p) {
                AgcOutput::Engine { on: true, .. } => {
                    let secs = start.elapsed().as_secs_f64().max(1e-9);
                    return Ok(downlink as f64 / secs);
                }
                AgcOutput::Downlink => downlink += 1,
                _ => {}
            },
            Err(broadcast::error::RecvError::Lagged(_)) => {}
            Err(broadcast::error::RecvError::Closed) => bail!("packet stream closed"),
        }
    }
}

/// Steady-state downlink packet rate: drain whatever is buffered, then
/// count ch 034/035 packets over a fresh `window` (the drift-meter
/// precondition wants a live ≥40/s figure, not a backlog average).
pub async fn measure_downlink_rate(
    packets: &mut broadcast::Receiver<Packet>,
    window: Duration,
) -> Result<f64> {
    // Drain the backlog without blocking.
    loop {
        match packets.try_recv() {
            Ok(_) => {}
            Err(broadcast::error::TryRecvError::Lagged(_)) => {}
            Err(broadcast::error::TryRecvError::Empty) => break,
            Err(broadcast::error::TryRecvError::Closed) => bail!("packet stream closed"),
        }
    }
    let start = tokio::time::Instant::now();
    let deadline = start + window;
    let mut downlink = 0u64;
    loop {
        let pkt = tokio::select! {
            r = packets.recv() => r,
            _ = tokio::time::sleep_until(deadline) => break,
        };
        match pkt {
            Ok(p) => {
                if matches!(decode_output(&p), AgcOutput::Downlink) {
                    downlink += 1;
                }
            }
            Err(broadcast::error::RecvError::Lagged(_)) => {}
            Err(broadcast::error::RecvError::Closed) => bail!("packet stream closed"),
        }
    }
    Ok(downlink as f64 / window.as_secs_f64().max(1e-9))
}

// ---------------------------------------------------------------------
// Synthetic hover PIPA feeder (v1).
// ---------------------------------------------------------------------

/// v1 synthetic PIPA feed: constant specific force of +1.62 m/s² along
/// SM +X (lunar-surface hover), emitted as PINC pulses to PIPAX every
/// 10 ms with a carry-forward accumulator: 1.62 / PIPA_INCR ≈ 27.7
/// pulses/s. No CDU pulses (attitude static, gimbals parked at zero).
/// Runs from boot so AVERAGE-G (PREREAD at TIG-30) sees a live
/// accelerometer; v2 (Task 7) replaces this with the closed dynamics
/// loop.
pub struct SyntheticHover {
    handle: tokio::task::JoinHandle<()>,
}

/// Hover specific force, m/s² (lunar surface gravity).
pub const HOVER_ACCEL_MS2: f64 = 1.62;

impl SyntheticHover {
    pub fn spawn(tx: mpsc::UnboundedSender<Packet>) -> Self {
        let handle = tokio::spawn(async move {
            let mut tick = tokio::time::interval(Duration::from_millis(10));
            // Delay (not Burst): missed ticks under contention UNDER-credit
            // ΔV rather than bursting pulses. Acceptable for v1, whose only
            // job is AVERAGE-G liveness (a live accelerometer signal);
            // Spike B's v2 feeds real dynamics with proper bookkeeping.
            tick.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
            let pulses_per_tick = HOVER_ACCEL_MS2 / PIPA_INCR * 0.010;
            let mut acc = 0.0f64;
            loop {
                tick.tick().await;
                acc += pulses_per_tick;
                while acc >= 1.0 {
                    acc -= 1.0;
                    if tx.send(pipa_pulse(PipaAxis::X, true)).is_err() {
                        return; // AGC gone; feeder dies with it
                    }
                }
            }
        });
        Self { handle }
    }

    pub fn stop(&self) {
        self.handle.abort();
    }
}

impl Drop for SyntheticHover {
    fn drop(&mut self) {
        self.handle.abort();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn discrete_constants_rederive_from_binary_strings() {
        // Binary source of truth (lm_simulator.tcl:570-577), parsed here
        // independently of the octal literals above.
        let parse = |s: &str| u16::from_str_radix(s, 2).unwrap();
        let ch30 = parse("011110011011001");
        let ch31 = parse("111111111111111");
        let ch32 = parse("010001111111111");
        let ch33 = parse("101111111111110");
        assert_eq!(ch30, 0o36331);
        assert_eq!(ch32, INIT_CH32);
        assert_eq!(ch33, INIT_CH33);
        // AUTO THROTTLE asserted on top of the LM_Sim word:
        assert_eq!(ch30 & !0o20, INIT_CH30);
        // AUTO mode: bit14 asserted out of all-ones:
        assert_eq!(ch31 & !0o20000, INIT_CH31);
        // ATT HOLD: bit13 asserted, bit14 released:
        assert_eq!((ch31 & !0o10000), CH31_ATT_HOLD);
    }

    #[test]
    fn flash_classification_table() {
        use FlashAction::*;
        assert_eq!(classify_flash("06", "61", " 00030", 0), Pro);
        assert_eq!(classify_flash("50", "25", " 00014", 0), Entr);
        assert_eq!(classify_flash("50", "25", "+00014", 0), Entr);
        assert_eq!(classify_flash("50", "25", " 00500", 0), LrPos1ThenPro);
        assert_eq!(classify_flash("50", "25", " 00203", 0), Unknown);
        assert_eq!(classify_flash("50", "18", " 00000", 0), Pro);
        assert_eq!(classify_flash("50", "18", " 00000", 1), Entr);
        assert_eq!(classify_flash("99", "62", " 00000", 0), ProAndDone);
        assert_eq!(classify_flash("16", "36", " 00000", 0), Unknown);
    }

    /// Key-count fixture: a raw (unverified) V21N01 load is 19 keys
    /// (V21N01E + 5 addr + E + 5 data + E); a verified load adds the
    /// V01N01 read-back's 13 keys (V01N01E + 5 addr + E) = 32.
    const RAW_KEYS: usize = 19;
    const VERIFIED_KEYS: usize = 19 + 13;

    fn seeded_script() -> (
        DskyScript,
        tokio::sync::mpsc::UnboundedReceiver<Packet>,
        tokio::sync::watch::Sender<DskyState>,
    ) {
        // Scripted fake AGC: the watch channel is pre-seeded with a DSKY
        // whose R1 already reads " 05050" (the wait_resolves_... pattern),
        // so load_erasable's V01N01 read-back parses immediately and
        // matches every verified word's value (verified words below are
        // deliberately 0o5050).
        let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
        let mut seeded = DskyState::default();
        // Set R1 digits via the relay rows (fields are private): row 8
        // drives R1D1, row 7 R1D2/D3, row 6 R1D4/D5. '0'=0b10101,'5'=0b11110.
        for pkt in [
            Packet::io(0o10, (8 << 11) | 0b10101).unwrap(),
            Packet::io(0o10, (7 << 11) | (0b11110 << 5) | 0b10101).unwrap(),
            Packet::io(0o10, (6 << 11) | (0b11110 << 5) | 0b10101).unwrap(),
        ] {
            seeded.apply(&pkt);
        }
        let (wtx, wrx) = tokio::sync::watch::channel(seeded);
        let mut script = DskyScript::new(tx, wrx);
        script.set_key_delay(Duration::ZERO);
        (script, rx, wtx)
    }

    #[tokio::test]
    async fn apply_padload_verification_cadence_and_always_set() {
        let (mut script, mut rx, _wtx) = seeded_script();
        let words = [
            // loaded index 0: stride-verified (0 % 3 == 0).
            PadWord { ecadr: 0o2400, word: 0o5050 },
            // zero word: skipped entirely (cold-boot erasable is zero).
            PadWord { ecadr: 0o2401, word: 0 },
            // loaded index 1: raw keys, no read-back.
            PadWord { ecadr: 0o2402, word: 0o7 },
            // loaded index 2: the stride (every 3rd) would SKIP this one --
            // the always-verify set must force the read-back anyway. This
            // is ZOOMTIME's ECADR, the exact word the review flagged.
            PadWord { ecadr: 0o3422, word: 0o5050 },
        ];
        assert!(ALWAYS_VERIFY_ECADRS.contains(&0o3422));
        apply_padload(&mut script, &words, 3, ALWAYS_VERIFY_ECADRS)
            .await
            .unwrap();
        drop(script);
        let mut keys = Vec::new();
        while let Some(p) = rx.recv().await {
            keys.push(p);
        }
        // verified + raw + always-verified; the zero word contributes 0.
        assert_eq!(keys.len(), VERIFIED_KEYS + RAW_KEYS + VERIFIED_KEYS);
        // First key of the sequence is VERB (code 0o21 on ch 015).
        assert_eq!(keys[0].data, 0o21);
        // The always-verify word's read-back is present: the LAST 13 keys
        // are V01N01E + its address; V01's "0","1" digits follow VERB.
        let tail = &keys[keys.len() - 13..];
        assert_eq!(tail[0].data, 0o21); // VERB
        assert_eq!(tail[1].data, 0o20); // 0
        assert_eq!(tail[2].data, 0o1); // 1
    }

    #[tokio::test]
    async fn apply_padload_stride_skips_readback_without_always_set() {
        // Same shape, empty always-set: the 0o3422 word must NOT be
        // verified (stride 3 skips loaded-index 2) -- pins that the
        // always-set is what forces the read-back in the test above.
        let (mut script, mut rx, _wtx) = seeded_script();
        let words = [
            PadWord { ecadr: 0o2400, word: 0o5050 },
            PadWord { ecadr: 0o2402, word: 0o7 },
            PadWord { ecadr: 0o3422, word: 0o5050 },
        ];
        apply_padload(&mut script, &words, 3, &[]).await.unwrap();
        drop(script);
        let mut n = 0;
        while rx.recv().await.is_some() {
            n += 1;
        }
        assert_eq!(n, VERIFIED_KEYS + RAW_KEYS + RAW_KEYS);
    }

    #[test]
    fn whitelist_is_octal_and_small() {
        for &code in SPIKE_A_ALARM_WHITELIST {
            assert!(code <= 0o77777);
        }
    }
}
