//! Spike A (Task 6): scripted boot → pad-load → P63 → ignition against the
//! live Luminary099/yaAGC. The choreography here is the *empirically
//! confirmed* dialog (see `.superpowers/sdd/task-6-report.md` and the
//! ledger); the vendor citations on each step are the static-analysis
//! starting points that the live runs validated or corrected.

use crate::padload::PadWord;
use crate::script::{DskyScript, EntryStatus};
use anyhow::{bail, ensure, Context, Result};
use eagle_agc_protocol::agc_io::{
    decode_output, discrete_write, pipa_pulse, thrust_dinc, AgcOutput, PipaAxis, ThrustPulse,
};
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::words::octal5;
use eagle_agc_protocol::Packet;
use eagle_dynamics::constants::{
    DINC_MAX_PER_TICK, DPS_MAX_N, DPS_MIN_N, DPS_VE, DT, PIPA_INCR, THRUST_N_PER_PULSE,
};
use std::time::Duration;
use tokio::sync::{broadcast, mpsc, watch};

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
// the un-auto-throttle discrete appears (vendor/virtualagc/Luminary099/
// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:140-148), and P40AUTO checks it
// pre-ignition (vendor/virtualagc/Luminary099/
// BURN,_BABY,_BURN_--_MASTER_IGNITION_ROUTINE.agc:921-925).
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

/// ch 030 bit9 IMU OPERATE ("IMU OPERATE WITH NO MALFUNCTION",
/// `vendor/virtualagc/Luminary099/INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:162`;
/// the CHANNEL 30 block starts at :151).
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
/// `CA BIT6, RAND CHAN33`,
/// vendor/virtualagc/Luminary099/THE_LUNAR_LANDING.agc:245-247).
pub const CH33_BIT6_LR_POS1: u16 = 1 << 5;

/// FLAGWRD3 = STATE +3, unswitched ECADR 0o77 (Luminary099.log:2703:
/// `26,2022  0077  FLAGWRD3 = STATE +3`; STATE = 0o74). REFSMFLG is its
/// BIT13 (vendor/virtualagc/Luminary099/FLAGWORD_ASSIGNMENTS.agc:475-476).
pub const FLAGWRD3_ECADR: u16 = 0o77;
/// REFSMBIT = BIT13
/// (vendor/virtualagc/Luminary099/FLAGWORD_ASSIGNMENTS.agc:476).
pub const REFSMBIT: u16 = 0o10000;
/// FLAGWRD8 = STATE +8, ECADR 0o104 (Luminary099.log:3065). CMOONFLG =
/// BIT12, LMOONFLG = BIT11 (vendor/virtualagc/Luminary099/
/// FLAGWORD_ASSIGNMENTS.agc:853-854,857-858 — the flag numbers are on the
/// first line of each pair, CMOONBIT/LMOONBIT on the second): the
/// permanent CSM/LM state vectors are moon-centered. Deliberately NOT
/// initialized by fresh start (vendor/virtualagc/LUM69R2/PADLOADS.agc:70-73,
/// the FLAGWRD8 pad entry: "CMOON, LMOON, & SURFFLAG ARE NOT INITIALIZED BY
/// FRESH START AS OTHER BITS ARE.") — pad-loaded.
pub const FLAGWRD8_ECADR: u16 = 0o104;
/// CMOONFLG | LMOONFLG.
pub const FLAGWRD8_MOON_BITS: u16 = 0o4000 | 0o2000;
/// FLGWRD11 = STATE +11D, unswitched ECADR 0o107 (`Luminary099.log:3262`:
/// `26,2022  0107  FLGWRD11 = STATE +11D`). LRBYPASS is its BIT15
/// (`vendor/virtualagc/Luminary099/FLAGWORD_ASSIGNMENTS.agc:1040-1041`).
pub const FLGWRD11_ECADR: u16 = 0o107;
/// LRBYBIT = BIT15 — set means "bypass ALL landing-radar updates". Fresh
/// start already sets it: the SWINIT table's 12th word is `OCT 40000` with
/// the comment `BIT 15 = LRBYPASS`
/// (`vendor/virtualagc/Luminary099/FRESH_START_AND_RESTART.agc:623`;
/// SWINIT begins at :611, so word 11 lands on :623). We fly with no
/// landing radar, so `run_scenario` VERIFIES this rather than writing it —
/// a cleared bit means R12 would read our nonexistent radar and the whole
/// descent premise is broken.
pub const LRBYBIT: u16 = 0o40000;

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
/// Spike B starts from Spike A's clean alarm set. Add a code only after a
/// live P66 run diagnoses it and records why the no-radar spike tolerates it.
pub const SPIKE_B_ALARM_WHITELIST: &[u16] = SPIKE_A_ALARM_WHITELIST;

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

/// Select ATT HOLD by writing the complete channel-031 word. GUILDENSTERN
/// reads bit 13 as an inverted discrete and changes an active landing program
/// to P66 (`vendor/virtualagc/Luminary099/
/// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:203-217`).
pub async fn att_hold(tx: &mpsc::UnboundedSender<Packet>) -> Result<()> {
    tx.send(Packet::io(0o31, CH31_ATT_HOLD).context("ATT HOLD packet")?)
        .context("agc tx closed")?;
    Ok(())
}

/// RODCOUNT, the rate-of-descent click accumulator (Luminary099.log:6033:
/// `E7,1745  E7,1746  RODCOUNT  EQUALS  RUNIT +3` → ECADR 0o3746).
pub const RODCOUNT_ECADR: u16 = 0o3746;
/// HDOTDISP (E7,1473), the altitude rate P66 displays as N60's R2 and
/// seeds VDGVERT from at STARTP66 (vendor/virtualagc/Luminary099/
/// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:156-157). DP.
pub const HDOTDISP_ECADR: u16 = 0o3473;
/// VDGVERT (E7,1644), P65/P66's desired altitude rate — the value ROD
/// clicks move (`MP RODSCAL1 / DAS VDGVERT`,
/// vendor/virtualagc/Luminary099/
/// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:958-963). DP.
pub const VDGVERT_ECADR: u16 = 0o3644;
/// RODSCAL1 (E7,1756), the working copy of the RODSCALE pad word taken at
/// STRTP66A (`STODL DELVROD / RODSCALE / STODL RODSCAL1`,
/// vendor/virtualagc/Luminary099/
/// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:173-175). SP.
pub const RODSCAL1_ECADR: u16 = 0o3756;

/// Read a double-precision erasable (two consecutive words, high then low)
/// over V01N01 and decode it to signed pulses, confirming the value with a
/// second full read.
///
/// `read_erasable` handles the P66 repaint collision (KEY REL, gap-wait,
/// retry), but a flight-display frame can still slip past its V01N01 guard
/// on rare occasions, and a corrupt high word turns a 12784-pulse ROD
/// delta into a 26-million-pulse one (spike-B iters 8, 17). VDGVERT and
/// HDOTDISP change only on ROD clicks, so a value read identically twice
/// in a row is trustworthy; a flicker forces another pair of reads.
const DP_READ_ATTEMPTS: u32 = 4;

pub async fn read_dp(script: &mut DskyScript, ecadr: u16) -> Result<i64> {
    let mut last: Option<i64> = None;
    for _ in 0..DP_READ_ATTEMPTS {
        let hi = script.read_erasable(ecadr).await?;
        let lo = script.read_erasable(ecadr + 1).await?;
        let value = eagle_agc_protocol::words::dp_decode([hi, lo]);
        if last == Some(value) {
            return Ok(value);
        }
        last = Some(value);
    }
    bail!(
        "DP read of {:05o} never repeated a value in {DP_READ_ATTEMPTS} reads",
        ecadr
    )
}

/// Click the ROD switch `clicks` times (negative = descend faster, the
/// bit-7 direction) by writing RODCOUNT over V21N01.
///
/// Why not the switch discrete: vendored yaAGC's
/// `vendor/virtualagc/yaAGC/SocketAPI.c:239-249`
/// raises KEYRUPT1 for a channel-015 write but no interrupt at all for
/// channel 016 — `InterruptRequests[6]` is never assigned anywhere in the
/// emulator — so MARKRUPT → DESCBITS never runs and a socket-written
/// click only updates NAVKEYIN, unobserved. DESCBITS' entire effect is
/// `ADS RODCOUNT` with ±1 (vendor/virtualagc/Luminary099/
/// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1233-1238)
/// and RODCOMP consumes the accumulator with `CAF ZERO / XCH RODCOUNT`
/// each P66 pass (:958-963), so loading the count directly is equivalent
/// to the interrupt path and needs no vendor patch. GUILDENSTERN's P66
/// entry test is the same non-zero RODCOUNT read (:214-217).
///
/// Deliberately unverified: a V01N01 read-back would race RODCOMP, which
/// zeroes the word within one 1-second P66 pass.
///
/// `grab_dsky` is not cosmetic. Once P66 is running, VERTDISP repaints
/// V06N60 every guidance pass (VERTDISP, vendor/virtualagc/Luminary099/
/// LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:899-900); a load typed into that
/// stream is
/// rejected mid-sequence with OPR ERR and the KEY REL lamp lit, leaving
/// RODCOUNT unwritten and VDGVERT unmoved (spike-B iter 18 — the same
/// swallow that broke the in-flight reads). Releasing the display and
/// waiting for its repaint burst to subside first is what makes the load
/// land.
pub async fn rod_load(script: &mut DskyScript, clicks: i16) -> Result<EntryStatus> {
    let word = eagle_agc_protocol::words::sp_encode(clicks);
    script
        .grab_dsky()
        .await
        .with_context(|| format!("ROD load {clicks:+} clicks: grab DSKY"))?;
    script
        .keys(&format!(
            "V21N01E{}E{}E",
            octal5(RODCOUNT_ECADR),
            octal5(word)
        ))
        .await
        .with_context(|| format!("ROD load {clicks:+} clicks"))?;
    // Let the AGC answer before sampling its lamps. 300 ms is the settle
    // this file already uses for a register rewrite, and >> the ~120 ms
    // DSKY relay cadence.
    tokio::time::sleep(Duration::from_millis(ROD_SETTLE_MS)).await;
    let status = script.entry_status();
    // Hand the display back whether or not the entry was accepted. A
    // latched KEY REL suppresses P66's VERTDISP for the REST OF THE RUN,
    // which is how flight 7 (2026-07-31) came back with 6 distinct
    // HDOTDISP values in 222 s of P66 and no measurement.
    script
        .release_dsky()
        .await
        .with_context(|| format!("ROD load {clicks:+} clicks: release DSKY"))?;
    Ok(status)
}

/// Settle time between the ROD load's last ENTR and sampling the AGC's
/// rejection lamps.
const ROD_SETTLE_MS: u64 = 300;

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
/// whole pounds — WEIGHT2 "XXXXX. LBS",
/// vendor/virtualagc/Luminary099/PINBALL_NOUN_TABLES.agc:88,450;
/// confirmed live by the AGC redisplaying 33500 as +33502 after its
/// lbs→kg→lbs round-trip) → V24E loads both → PRO (DAPDAT2 sets MASS,
/// deadband, moments of inertia) → FL V06N48 (gimbal trim) →
/// **V34E TERMINATE**, deliberately NOT PRO: PRO starts the TRIMGIMB
/// gimbal-centering drive (DPDAT3, vendor/virtualagc/Luminary099/
/// EXTENDED_VERBS.agc:1470 → WAITLIST → vendor/virtualagc/Luminary099/
/// P40-P47.agc:1384), which FIXDELAYs 60 s at full +pitch/+roll and then
/// calls TWIDDLE/VARDELAY with PITTIME/ROLLTIME — zero on a cold AGC —
/// and a zero-dt waitlist call POODOOs 01204 (WAITPOOH,
/// vendor/virtualagc/Luminary099/WAITLIST.agc:574-576)
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
/// - FL V06N61 (TTG/±xx display via ASTNCLOK,
///   vendor/virtualagc/Luminary099/THE_LUNAR_LANDING.agc:213-216)
///   → PRO ("proceed" hands off to R51P63 via ASTNRETN).
/// - FL V50N25 R1=00014 (R51P63 fine-align offer,
///   vendor/virtualagc/Luminary099/P51-P53.agc:724-731) →
///   ENTR: "ENTER will return to P63SPOT2" — PRO here would start a fine
///   alignment we neither need nor can complete.
/// - FL V50N18 (R60 attitude maneuver request) → PRO the first time (auto
///   maneuver; our REFSMMAT puts the burn attitude at our parked CDUs so
///   it is near-null), ENTR on a repeat (accept attitude, exit R60).
/// - FL V50N25 R1=00500 ("PLEASE CRANK THE SILLY THING AROUND",
///   vendor/virtualagc/Luminary099/THE_LUNAR_LANDING.agc:251-255) → assert
///   ch33 bit6 then PRO.
/// - FL V99Nxx ("PLEASE ENABLE ENGINE", vendor/virtualagc/Luminary099/
///   BURN,_BABY,_BURN_--_MASTER_IGNITION_ROUTINE.agc:778-788) → PRO
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

/// One PROG-alarm EPISODE observed by the P63 responder: the FAILREG
/// triple read at the moment the lamp was seen, plus whether the responder
/// swallowed it (RSET + KEY REL, whitelisted) or aborted the run.
///
/// Episodes are counted, not filtered. A lamp that lights with an
/// all-zero FAILREG is still an episode — the AGC raised an alarm and the
/// responder RSET it away, which is exactly the event the acceptance run
/// must not be blind to. Filtering by "non-zero code" is what made the
/// old `Vec<u16>` return structurally empty (and its assertion
/// tautological) once the whitelists were locked to the empty set.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AlarmEpisode {
    /// FAILREG 1/2/3 as read over V05N09 while the lamp was lit.
    pub codes: [u16; 3],
    /// True: every non-zero code was whitelisted, so the responder RSET
    /// the lamp and carried on. False: the run aborted on this episode.
    pub acknowledged: bool,
}

/// True when every code in the triple is either zero or on `whitelist`.
/// With an empty whitelist this is "FAILREG is all zeros" — which is why
/// it decides only whether the responder may CONTINUE, never whether the
/// episode is recorded.
pub fn alarm_is_whitelisted(codes: &[u16; 3], whitelist: &[u16]) -> bool {
    codes.iter().all(|c| *c == 0 || whitelist.contains(c))
}

impl AlarmEpisode {
    /// Record a lamp-lit episode against a whitelist.
    pub fn new(codes: [u16; 3], whitelist: &[u16]) -> Self {
        Self {
            acknowledged: alarm_is_whitelisted(&codes, whitelist),
            codes,
        }
    }
}

/// V37E63E, then run the flash responder until the V99 engine-enable
/// request has been answered with PRO (or fail on non-whitelisted PROG
/// alarm / timeout / dialog loop). A PROG alarm whose FAILREG codes are
/// all in `SPIKE_A_ALARM_WHITELIST` (∪ {0}) is acknowledged with RSET +
/// KEY REL and the dialog continues; any other code aborts with the
/// codes in the error. Engine-on itself is asserted by the caller on the
/// raw packet stream (ch 011 bit13) — it arrives at TIG-0, after this
/// function returns.
///
/// Returns one `AlarmEpisode` per PROG-alarm lamp it handled — swallowed
/// or not — so the caller asserts on what the run OBSERVED rather than on
/// the whitelist constant. A FAILREG read that fails is a hard error, NOT
/// a silent `[0; 3]`: the old fallback made "V05N09 unreadable" look
/// exactly like "no alarm", so a real PROG alarm could be RSET away
/// unrecorded and still pass.
pub async fn enter_p63_with_alarms(script: &mut DskyScript) -> Result<Vec<AlarmEpisode>> {
    // Budget: the frozen choreography reaches ENGINE ON ~174 s after
    // V37E63E (IGNALG ~5 s + dialog + burn_lead countdown); 600 s ≈ 3.4×
    // margin also covers BURNBABY's TIG-slip path (+30 s) and a slow
    // IGNALG without masking a genuine hang for the whole test timeout.
    const TIMEOUT: Duration = Duration::from_secs(600);
    let mut episodes: Vec<AlarmEpisode> = Vec::new();
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
            // A FAILREG read failure is fatal, never `[0; 3]`: an alarm we
            // cannot identify is an alarm we must not RSET away silently.
            let codes = script
                .alarm_codes()
                .await
                .context("PROG alarm lamp lit but FAILREG (V05N09) could not be read")?;
            // Record the episode BEFORE deciding what to do with it, so
            // the abort path carries its codes too.
            let episode = AlarmEpisode::new(codes, SPIKE_A_ALARM_WHITELIST);
            episodes.push(episode);
            if !episode.acknowledged {
                bail!(
                    "PROG alarm during P63 entry: FAILREG = {:05o} {:05o} {:05o} \
                     (episodes so far: {episodes:?})",
                    codes[0],
                    codes[1],
                    codes[2]
                );
            }
            // Whitelisted: acknowledge like the crew would (RSET clears
            // the lamp — sanctioned for whitelisted codes only), release
            // the display back to the flashing program, and continue. The
            // acceptance run asserts the episode list is empty, so the
            // swallow cannot go unreported.
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
                return Ok(episodes);
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

/// Back-compat wrapper for callers that only care whether the dialog
/// completed (`descent_probe`, the two live spikes).
pub async fn enter_p63(script: &mut DskyScript) -> Result<()> {
    enter_p63_with_alarms(script).await.map(|_| ())
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
// Synthetic hover PIPA feeder and Spike-B 1-D closed loop.
// ---------------------------------------------------------------------

/// Accumulates the AGC's THRUST-counter output. A ch014 drive-enable arms
/// DINC strobes; each returned POUT/MOUT changes the persistent commanded
/// pulse count, and ZOUT ends that drive burst. The semantics are the direct
/// external-hardware counterpart of yaAGC `CounterDINC`
/// (`vendor/virtualagc/yaAGC/agc_engine.c:1278-1308,1570-1606`).
///
/// The physical throttle actuator is a bounded position, not an unbounded
/// signed accumulator. Luminary deliberately emits −4096 pulses while the
/// engine is off (`vendor/virtualagc/Luminary099/P40-P47.agc:490-494`) to
/// seek the zero stop, then +4096
/// for FLATOUT. Pulses beyond either stop therefore leave the position at
/// that stop.
///
/// 4096 is the rope's own `FEXTRA = BIT13`
/// (`vendor/virtualagc/Luminary099/THROTTLE_CONTROL_ROUTINES.agc:226`,
/// `# FEXT +5.13309020 E+4`; loaded at `:107`, and by `FLATOUT` at `:197`
/// as `CAF BIT13  # 4096 PULSES`).
/// Note it is a DRIVE-PAST value, 51 330.9 N of command against the
/// 48 145.4 N stop the same block calls full throttle (`FSAT`,
/// `vendor/virtualagc/Luminary099/CONTROLLED_CONSTANTS.agc:132`) —
/// `dps_envelope` is what models the
/// stop, not this bound.
pub const THRUST_CMD_MAX_PULSES: i64 = 4096;

#[derive(Debug, Default)]
pub struct ThrustResponder {
    pub cmd_pulses: i64,
    armed: bool,
    outstanding: u32,
}

impl ThrustResponder {
    pub fn on_output(&mut self, out: &AgcOutput) {
        match out {
            AgcOutput::ThrustDrive(true) => self.armed = true,
            AgcOutput::ThrustPulse(ThrustPulse::Pout) => {
                self.outstanding = self.outstanding.saturating_sub(1);
                self.cmd_pulses = (self.cmd_pulses + 1).min(THRUST_CMD_MAX_PULSES);
            }
            AgcOutput::ThrustPulse(ThrustPulse::Mout) => {
                self.outstanding = self.outstanding.saturating_sub(1);
                self.cmd_pulses = (self.cmd_pulses - 1).max(0);
            }
            AgcOutput::ThrustPulse(ThrustPulse::Zout) => {
                self.outstanding = self.outstanding.saturating_sub(1);
                self.armed = false;
            }
            _ => {}
        }
    }

    pub fn tick_packets(&mut self) -> Vec<Packet> {
        if !self.armed {
            return Vec::new();
        }
        // Bound requests that have not yet produced POUT/MOUT/ZOUT. Without
        // this credit window, a busy socket pump can queue thousands of
        // DINC strobes before the first ZOUT reaches this task.
        let count = DINC_MAX_PER_TICK.saturating_sub(self.outstanding);
        self.outstanding += count;
        (0..count).map(|_| thrust_dinc()).collect()
    }
}

/// Observable state of the Spike-B one-dimensional truth model.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct HoverTruth {
    pub alt_m: f64,
    pub vz_ms: f64,
    pub mass_kg: f64,
    pub cmd_pulses: i64,
    pub thrust_n: f64,
    pub engine_on: bool,
}

/// Deterministic 10-ms vertical model used before the full six-DoF dynamics
/// crate exists. Positive vertical velocity is up; PIPAX sees positive
/// specific force from the DPS, not gravity.
#[derive(Debug)]
pub struct SyntheticHoverModel {
    truth: HoverTruth,
    pipa_remainder: f64,
}

impl SyntheticHoverModel {
    pub fn new(alt_m: f64, vz_ms: f64, mass_kg: f64) -> Self {
        assert!(mass_kg > 0.0, "synthetic-hover mass must be positive");
        Self {
            truth: HoverTruth {
                alt_m,
                vz_ms,
                mass_kg,
                cmd_pulses: 0,
                thrust_n: 0.0,
                engine_on: false,
            },
            pipa_remainder: 0.0,
        }
    }

    pub fn truth(&self) -> HoverTruth {
        self.truth
    }

    /// Advance one fixed 10-ms tick and return the resulting PIPAX pulses.
    pub fn step(&mut self, cmd_pulses: i64, engine_on: bool) -> Vec<Packet> {
        // The Spike-B gate begins at ignition. Before ENGINE ON we only
        // accumulate THRUST POUT/MOUT in the responder; the v1 feeder remains
        // the sole PIPA source and this local vertical state stays parked.
        if !engine_on {
            self.truth.cmd_pulses = cmd_pulses;
            self.truth.thrust_n = 0.0;
            self.truth.engine_on = false;
            return Vec::new();
        }
        // A lit DPS never produces zero thrust: the throttle actuator's
        // zero stop is the engine's ~10 % idle, and Luminary leaves the
        // throttle parked there for the whole ZOOMTIME trim phase after
        // ignition before FLATOUT drives it up.
        let thrust_n =
            ((cmd_pulses.max(0) as f64) * THRUST_N_PER_PULSE).clamp(DPS_MIN_N, DPS_MAX_N);
        let specific_force = thrust_n / self.truth.mass_kg;
        let az_ms2 = specific_force - HOVER_ACCEL_MS2;

        self.truth.vz_ms += az_ms2 * DT;
        self.truth.alt_m += self.truth.vz_ms * DT;
        self.truth.mass_kg = (self.truth.mass_kg - thrust_n / DPS_VE * DT).max(1.0);
        self.truth.cmd_pulses = cmd_pulses;
        self.truth.thrust_n = thrust_n;
        self.truth.engine_on = engine_on;

        self.pipa_remainder += specific_force * DT / PIPA_INCR;
        let pulse_count = self.pipa_remainder.floor() as usize;
        self.pipa_remainder -= pulse_count as f64;
        (0..pulse_count)
            .map(|_| pipa_pulse(PipaAxis::X, true))
            .collect()
    }
}

/// v1 synthetic PIPA feed: constant specific force of +1.62 m/s² along
/// SM +X (lunar-surface hover), emitted as PINC pulses to PIPAX every
/// 10 ms with a carry-forward accumulator: 1.62 / PIPA_INCR ≈ 27.7
/// pulses/s. No CDU pulses (attitude static, gimbals parked at zero).
/// Runs from boot so AVERAGE-G (PREREAD at TIG-30) sees a live
/// accelerometer. `spawn_closed_loop` replaces this feeder after ENGINE ON.
pub struct SyntheticHover {
    handle: tokio::task::JoinHandle<()>,
    truth_rx: Option<watch::Receiver<HoverTruth>>,
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
        Self {
            handle,
            truth_rx: None,
        }
    }

    /// Spawn the Spike-B THRUST/DINC + vertical-truth loop. The caller should
    /// stop the v1 feeder first so PIPAX has exactly one producer.
    pub fn spawn_closed_loop(
        tx: mpsc::UnboundedSender<Packet>,
        packets: broadcast::Receiver<Packet>,
        initial: HoverTruth,
    ) -> Self {
        Self::spawn_loop(tx, packets, initial, false)
    }

    /// Spawn the same THRUST/DINC loop with the **plant frozen**: the AGC's
    /// throttle commands are tracked, so `cmd_pulses` is live, but they do
    /// not move the vehicle. PIPAX gets a constant lunar-g specific force,
    /// exactly like the v1 feeder, so **the AGC's own altitude rate is
    /// constant by construction**.
    ///
    /// This is what makes an open-loop step test of P66's force law
    /// possible. With `dHDOT` identically zero, stepping `VDGVERT` by a
    /// known amount gives
    ///
    /// ```text
    ///   TAUROD = dVDGVERT / d(a_cmd)
    /// ```
    ///
    /// with no transient to dominate the step and no dependence on the
    /// AGC's navigation agreeing with truth. Both of those sank the first
    /// attempt, which used the live plant: the vehicle free-fell to
    /// −47 m/s during the ZOOMTIME idle phase, and `dHDOT` swamped
    /// `dVDGVERT` 70× (see
    /// `docs/superpowers/notes/2026-07-31-m1b-rod-loop.md` §7a).
    ///
    /// Like the live loop, this stays silent until ENGINE ON so it can be
    /// spawned alongside the v1 feeder without two producers on PIPAX.
    pub fn spawn_frozen_plant(
        tx: mpsc::UnboundedSender<Packet>,
        packets: broadcast::Receiver<Packet>,
        initial: HoverTruth,
    ) -> Self {
        Self::spawn_loop(tx, packets, initial, true)
    }

    fn spawn_loop(
        tx: mpsc::UnboundedSender<Packet>,
        mut packets: broadcast::Receiver<Packet>,
        initial: HoverTruth,
        frozen: bool,
    ) -> Self {
        let (truth_tx, truth_rx) = watch::channel(initial);
        let handle = tokio::spawn(async move {
            let mut tick = tokio::time::interval(Duration::from_millis(10));
            tick.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
            let mut model = SyntheticHoverModel::new(initial.alt_m, initial.vz_ms, initial.mass_kg);
            let mut responder = ThrustResponder::default();
            let mut engine_on = initial.engine_on;
            let mut frozen_pipa = 0.0f64;

            loop {
                tick.tick().await;
                loop {
                    match packets.try_recv() {
                        Ok(packet) => {
                            let out = decode_output(&packet);
                            responder.on_output(&out);
                            if let AgcOutput::Engine { on, off } = out {
                                match (on, off) {
                                    (true, false) => engine_on = true,
                                    (false, true) => engine_on = false,
                                    _ => {}
                                }
                            }
                        }
                        Err(broadcast::error::TryRecvError::Lagged(_)) => continue,
                        Err(broadcast::error::TryRecvError::Empty) => break,
                        Err(broadcast::error::TryRecvError::Closed) => return,
                    }
                }

                for packet in responder.tick_packets() {
                    if tx.send(packet).is_err() {
                        return;
                    }
                }
                if frozen {
                    // Constant lunar-g specific force: the same stream the
                    // v1 feeder emits, so the AGC integrates a vehicle
                    // whose altitude rate never changes. Silent before
                    // ENGINE ON, so the v1 feeder stays the only producer
                    // until the caller stops it.
                    if engine_on {
                        frozen_pipa += HOVER_ACCEL_MS2 / PIPA_INCR * DT;
                        while frozen_pipa >= 1.0 {
                            frozen_pipa -= 1.0;
                            if tx.send(pipa_pulse(PipaAxis::X, true)).is_err() {
                                return;
                            }
                        }
                    }
                    // Report the live command against the pinned vehicle,
                    // which is what a step measurement reads.
                    let mut truth = initial;
                    truth.cmd_pulses = responder.cmd_pulses;
                    truth.thrust_n = (responder.cmd_pulses.max(0) as f64) * THRUST_N_PER_PULSE;
                    truth.engine_on = engine_on;
                    if truth_tx.send(truth).is_err() {
                        return;
                    }
                } else {
                    for packet in model.step(responder.cmd_pulses, engine_on) {
                        if tx.send(packet).is_err() {
                            return;
                        }
                    }
                    if truth_tx.send(model.truth()).is_err() {
                        return;
                    }
                }
            }
        });
        Self {
            handle,
            truth_rx: Some(truth_rx),
        }
    }

    pub fn truth(&self) -> Option<watch::Receiver<HoverTruth>> {
        self.truth_rx.clone()
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

// ---------------------------------------------------------------------
// Productized scenario choreography (Task 14): the Spike A+B dialog driven
// from a Scenario, up to and including P66 entry. The sim thread + a packet
// forwarder run alongside; after this returns, the descent ROD schedule is
// delivered by the caller draining the sim's `rod_clicks`.
// ---------------------------------------------------------------------

/// What the choreography observed, for the acceptance run to assert on.
#[derive(Debug, Default, Clone)]
pub struct ScenarioReport {
    /// Every PROG-alarm episode the P63 responder handled (a
    /// non-whitelisted code aborts instead of landing here, so these were
    /// all swallowed). Empty only if the lamp never lit.
    pub alarms: Vec<AlarmEpisode>,
}

/// Boot → discretes/ISS → V48 → LRBYPASS verify → pad-load (static +
/// generated state) → REFSMFLG → V37E63E → ENGINE ON, then the tail
/// depends on `gate.mode`:
///
/// * `Hover` (Wave 1, unchanged): sleep `flip_atthold_after_engine_on_s`,
///   ATT HOLD + selection ROD click, return once GUILDENSTERN reaches P66.
/// * `Pdi`: return at ENGINE ON. P63 braking, P64 approach and the
///   P64→P66 handover all run afterwards, driven by the sim through
///   `SimEvent` — nothing here may force a mode.
///
/// `packets` is a broadcast receiver of every AGC packet (for the ignition
/// responder and the engine-on wait).
pub async fn run_scenario(
    script: &mut DskyScript,
    sc: &crate::scenario::Scenario,
    symtab: &crate::padload::SymTab,
    static_manifest: &crate::padload::PadloadManifest,
    agc_tx: &mpsc::UnboundedSender<Packet>,
    packets: &mut broadcast::Receiver<Packet>,
) -> Result<ScenarioReport> {
    use crate::padload::{generate_state, PadloadManifest, StateCfg};

    // Fresh-start dance.
    tokio::time::sleep(Duration::from_secs(2)).await;
    script.keys("R").await?;
    script.keys("V37E00E").await?;
    script.wait_prog("00").await.context("P00 after V37E00E")?;

    init_discretes(agc_tx).await?;
    dap_init(script, sc.agc.lm_weight_lbs.round() as u32, 0)
        .await
        .context("V48 DAP init")?;

    // Landing-radar bypass. We model no landing radar, so R12 must never
    // try to incorporate one; fresh start sets LRBYPASS for us
    // (vendor/virtualagc/Luminary099/FRESH_START_AND_RESTART.agc:623),
    // which makes this a read-back
    // VERIFY, not a write — if the assumption ever stops holding we want
    // the run to stop here, not to discover it in the descent data.
    if sc.agc.lrbypass {
        let word = script
            .read_erasable(FLGWRD11_ECADR)
            .await
            .context("read FLGWRD11")?;
        ensure!(
            word & LRBYBIT != 0,
            "LRBYPASS not set after fresh start — radar-bypass precondition broken \
             (FLGWRD11 @{:05o} = {:05o})",
            FLGWRD11_ECADR,
            word
        );
    }

    let epoch_cs = read_clock_cs(script).await.context("clock read")?;
    let state = PadloadManifest {
        word: generate_state(&StateCfg {
            epoch_now_cs: epoch_cs,
            burn_lead_cs: sc.agc.tland_offset_cs as f64,
            ..StateCfg::default()
        }),
    };

    wait_iss_turnon(packets, agc_tx, Duration::from_secs(150))
        .await
        .context("ISS turn-on delay complete")?;
    let _ = script
        .wait(Duration::from_secs(30), |d| !d.lamps.no_att)
        .await;

    let words = static_manifest.resolve(symtab).context("static manifest")?;
    apply_padload(script, &words, 8, ALWAYS_VERIFY_ECADRS)
        .await
        .context("static pad-load")?;
    let words = state.resolve(symtab).context("state manifest")?;
    apply_padload(script, &words, 8, ALWAYS_VERIFY_ECADRS)
        .await
        .context("state pad-load")?;

    set_flag_bits(script, FLAGWRD8_ECADR, FLAGWRD8_MOON_BITS)
        .await
        .context("FLAGWRD8 moon bits")?;
    set_flag_bits(script, FLAGWRD3_ECADR, REFSMBIT)
        .await
        .context("REFSMFLG")?;

    let alarms = enter_p63_with_alarms(script).await.context("P63 dialog")?;
    wait_engine_on(packets, Duration::from_secs(180))
        .await
        .context("ENGINE ON")?;

    // PDI mode ends here: the P64→P66 handover is SIM-driven (armed by
    // MM64, fired at `[handover] alt_m`), delivered by the headless event
    // loop. Running the hover block below would flip ATT HOLD at TIG+2 s —
    // ~15 km up, still in P63 braking — and then block forever on a MM66
    // that the braking phase will never paint.
    if sc.gate.mode == crate::scenario::GateMode::Pdi {
        return Ok(ScenarioReport { alarms });
    }

    // Enter P66: ATT HOLD, then the selection ROD click as a RODCOUNT load.
    tokio::time::sleep(Duration::from_secs_f64(
        sc.agc.flip_atthold_after_engine_on_s,
    ))
    .await;
    att_hold(agc_tx).await.context("ATT HOLD")?;
    rod_load(script, -1).await.context("selection ROD click")?;
    script.wait_prog("66").await.context("reach MM66")?;
    Ok(ScenarioReport { alarms })
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
    fn flgwrd11_constants() {
        // STATE = 0o74 (FLAGWRD3 = STATE +3 = 0o77 is already pinned above);
        // STATE + 11D = 0o74 + 11 = 0o107.
        assert_eq!(FLGWRD11_ECADR, 0o74 + 11);
        assert_eq!(LRBYBIT, 1 << 14); // BIT 15 in AGC 1-based numbering
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

    #[test]
    fn thrust_responder_arms_counts_and_disarms() {
        use eagle_agc_protocol::agc_io::ThrustPulse;

        let mut responder = ThrustResponder::default();
        assert!(responder.tick_packets().is_empty());

        responder.on_output(&AgcOutput::ThrustDrive(true));
        let strobes = responder.tick_packets();
        assert_eq!(strobes.len(), DINC_MAX_PER_TICK as usize);
        assert!(strobes.iter().all(|p| *p == thrust_dinc()));

        responder.on_output(&AgcOutput::ThrustPulse(ThrustPulse::Pout));
        responder.on_output(&AgcOutput::ThrustPulse(ThrustPulse::Pout));
        responder.on_output(&AgcOutput::ThrustPulse(ThrustPulse::Mout));
        assert_eq!(responder.cmd_pulses, 1);
        assert_eq!(responder.tick_packets().len(), 3);

        responder.on_output(&AgcOutput::ThrustPulse(ThrustPulse::Zout));
        assert!(!responder.armed);
        assert!(responder.tick_packets().is_empty());

        let mut bounded = ThrustResponder::default();
        bounded.on_output(&AgcOutput::ThrustPulse(ThrustPulse::Mout));
        assert_eq!(bounded.cmd_pulses, 0);
        bounded.cmd_pulses = THRUST_CMD_MAX_PULSES;
        bounded.on_output(&AgcOutput::ThrustPulse(ThrustPulse::Pout));
        assert_eq!(bounded.cmd_pulses, THRUST_CMD_MAX_PULSES);
    }

    #[test]
    fn synthetic_hover_tracks_hover_equilibrium_for_sixty_seconds() {
        let mut model = SyntheticHoverModel::new(500.0, 0.0, 15_195.0);
        for _ in 0..6_000 {
            let cmd_pulses =
                (model.truth().mass_kg * HOVER_ACCEL_MS2 / THRUST_N_PER_PULSE).round() as i64;
            let _pipa = model.step(cmd_pulses, true);
        }
        assert!(
            model.truth().vz_ms.abs() <= 0.05,
            "hover drifted to {} m/s",
            model.truth().vz_ms
        );
    }

    #[test]
    fn ignition_at_zero_command_holds_minimum_dps_thrust() {
        // The DPS lights at its idle stop: from ENGINE ON until the
        // ZOOMTIME trim phase ends (~26 s) Luminary commands no throttle
        // increase at all, and a zero-thrust model free-falls through the
        // whole burn-in (spike-B iter 6: −42 m/s by MM66).
        let mut model = SyntheticHoverModel::new(500.0, 0.0, 15_195.0);
        model.step(0, true);
        assert_eq!(model.truth().thrust_n, DPS_MIN_N);
    }

    #[test]
    fn synthetic_hover_gate_is_frozen_before_engine_on() {
        let mut model = SyntheticHoverModel::new(500.0, -2.0, 15_195.0);
        assert!(model.step(4_096, false).is_empty());
        assert_eq!(model.truth().alt_m, 500.0);
        assert_eq!(model.truth().vz_ms, -2.0);
        assert_eq!(model.truth().mass_kg, 15_195.0);
        assert_eq!(model.truth().cmd_pulses, 4_096);
        assert_eq!(model.truth().thrust_n, 0.0);
    }

    #[tokio::test]
    async fn att_hold_writes_full_channel_word() {
        let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();
        att_hold(&tx).await.unwrap();
        assert_eq!(
            rx.recv().await.unwrap(),
            Packet::io(0o31, CH31_ATT_HOLD).unwrap()
        );
    }

    #[test]
    fn rodcount_ecadr_matches_assembly_listing() {
        let symtab = crate::padload::SymTab::from_listing(include_str!(
            "../tests/fixtures/symtab_excerpt.txt"
        ))
        .unwrap();
        assert_eq!(symtab.ecadr("RODCOUNT"), Some(RODCOUNT_ECADR));
    }

    #[tokio::test]
    async fn read_dp_combines_the_two_erasable_words() {
        let (mut script, _rx, _wtx) = seeded_script();
        // The fake DSKY answers every V01N01 read-back with R1 = 05050.
        let got = read_dp(&mut script, VDGVERT_ECADR).await.unwrap();
        assert_eq!(got, eagle_agc_protocol::words::dp_decode([0o5050, 0o5050]));
    }

    #[tokio::test]
    async fn read_dp_confirms_the_value_with_a_second_read() {
        // VDGVERT is static except for ROD clicks, so a single flicker in
        // one word (a flight-display frame slipping past the V01N01 guard,
        // spike-B iter 17) shows up as a huge bogus delta. read_dp must
        // read the whole DP twice and only trust a value it saw twice —
        // here that is two full DP reads = four V01N01 entries.
        let (mut script, mut rx, _wtx) = seeded_script();
        read_dp(&mut script, VDGVERT_ECADR).await.unwrap();
        drop(script);
        let verb = eagle_agc_protocol::keys::DskyKey::from_name("VERB")
            .unwrap()
            .packet();
        let mut verbs = 0;
        while let Ok(p) = rx.try_recv() {
            if p == verb {
                verbs += 1;
            }
        }
        assert_eq!(verbs, 4, "read_dp must issue two full DP reads");
    }

    #[test]
    fn p66_calibration_ecadrs_match_assembly_listing() {
        let symtab = crate::padload::SymTab::from_listing(include_str!(
            "../tests/fixtures/symtab_excerpt.txt"
        ))
        .unwrap();
        assert_eq!(symtab.ecadr("HDOTDISP"), Some(HDOTDISP_ECADR));
        assert_eq!(symtab.ecadr("RODSCAL1"), Some(RODSCAL1_ECADR));
        // VDGVERT is defined with `=` rather than EQUALS, so the listing's
        // symbol column never carries it; NEWVEL shares its cell (both are
        // E7,1644 — VDGVERT = ELIDUMMY = TTF/8 +2).
        assert_eq!(symtab.ecadr("NEWVEL"), Some(VDGVERT_ECADR));
    }

    #[tokio::test]
    async fn rod_load_types_signed_click_count_into_rodcount() {
        let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();
        let (_wtx, wrx) = tokio::sync::watch::channel(DskyState::default());
        let mut script = DskyScript::new(tx, wrx);
        script.set_key_delay(Duration::ZERO);

        // Two down-clicks = RODCOUNT −2 = 0o77775 in one's complement.
        rod_load(&mut script, -2).await.unwrap();

        let expected = [
            "KEY_REL", // release the P66 flight display first
            "VERB", "2", "1", "NOUN", "0", "1", "ENTR", // V21N01E
            "0", "3", "7", "4", "6", "ENTR", // RODCOUNT ECADR
            "7", "7", "7", "7", "5", "ENTR",    // −2
            "KEY_REL", // hand the flight display back so VERTDISP repaints
        ];
        for name in expected {
            let want = eagle_agc_protocol::keys::DskyKey::from_name(name)
                .unwrap()
                .packet();
            assert_eq!(rx.recv().await.unwrap(), want, "key {name}");
        }
        // No V01N01 read-back: RODCOMP consumes RODCOUNT with XCH, so a
        // verify would race the AGC and spuriously fail. Acceptance is
        // checked PASSIVELY instead, off the KEY REL / OPR ERR lamps.
        // Nothing after the release — in particular no RSET, which would
        // clear FAILREG along with the lamp.
        assert!(rx.try_recv().is_err());
    }

    #[tokio::test(start_paused = true)]
    async fn frozen_plant_holds_the_vehicle_and_still_tracks_the_command() {
        // The whole point: dHDOT must be identically zero so a VDGVERT
        // step is the only thing moving, while cmd_pulses stays live.
        let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel();
        let (pkt_tx, pkt_rx) = tokio::sync::broadcast::channel(256);
        let initial = HoverTruth {
            alt_m: 3_000.0,
            vz_ms: -1.5,
            mass_kg: 15_000.0,
            cmd_pulses: 0,
            thrust_n: 0.0,
            engine_on: true,
        };
        let hover = SyntheticHover::spawn_frozen_plant(tx, pkt_rx, initial);
        let truth = hover.truth().expect("frozen plant publishes truth");

        // Arm the responder, then drive the throttle up: POUT counter
        // packets are what CounterDINC produces (agc_io.rs:108-115).
        pkt_tx.send(Packet::io(0o14, 1 << 3).unwrap()).unwrap();
        for _ in 0..400 {
            pkt_tx.send(Packet::counter(0o55, 0o15).unwrap()).unwrap();
        }
        tokio::time::sleep(Duration::from_millis(500)).await;

        let t = *truth.borrow();
        assert_eq!(t.alt_m, initial.alt_m, "altitude must not move");
        assert_eq!(t.vz_ms, initial.vz_ms, "the rate must not move — dHDOT ≡ 0");
        assert_eq!(t.mass_kg, initial.mass_kg, "no propellant burn");
        assert!(
            t.cmd_pulses > 0,
            "the command must still be tracked, got {}",
            t.cmd_pulses
        );

        // And PIPAX is fed: a constant lunar-g stream, so the AGC's own
        // altitude rate is constant rather than absent.
        let mut pipa = 0;
        while rx.try_recv().is_ok() {
            pipa += 1;
        }
        assert!(pipa > 0, "frozen plant must still feed PIPAX");
        hover.stop();
    }

    #[tokio::test]
    async fn rod_load_reports_a_rejected_entry() {
        // ch0163 KEY REL = 020: the AGC refused the entry, so RODCOUNT is
        // unwritten and VDGVERT did not move. Flight 7 (2026-07-31) shows
        // what silence costs — a refused load froze the flight display for
        // the remaining 216 s of P66.
        let (tx, _rx) = tokio::sync::mpsc::unbounded_channel();
        let mut rejected = DskyState::default();
        rejected.apply(&Packet::io(0o163, 0o20).unwrap());
        let (_wtx, wrx) = tokio::sync::watch::channel(rejected);
        let mut script = DskyScript::new(tx, wrx);
        script.set_key_delay(Duration::ZERO);

        let status = rod_load(&mut script, -2).await.unwrap();
        assert!(status.rejected(), "{status:?}");
        assert!(status.key_rel);
        assert!(!status.opr_err);
    }

    #[tokio::test]
    async fn rod_load_reports_a_clean_entry() {
        let (tx, _rx) = tokio::sync::mpsc::unbounded_channel();
        let (_wtx, wrx) = tokio::sync::watch::channel(DskyState::default());
        let mut script = DskyScript::new(tx, wrx);
        script.set_key_delay(Duration::ZERO);
        assert!(!rod_load(&mut script, -2).await.unwrap().rejected());
    }

    /// Key-count fixture: a raw (unverified) V21N01 load is 19 keys
    /// (V21N01E + 5 addr + E + 5 data + E); a verified load adds the
    /// V01N01 read-back's 14 keys (KEY REL + V01N01E + 5 addr + E) = 33.
    const RAW_KEYS: usize = 19;
    const VERIFIED_KEYS: usize = 19 + 14;

    /// Relay word: AAAA B CCCCC DDDDD (see `dsky.rs`).
    fn relay(row: u16, c: u16, d: u16) -> Packet {
        Packet::io(0o10, (row << 11) | (c << 5) | d).unwrap()
    }
    fn code(ch: char) -> u16 {
        match ch {
            '0' => 0b10101,
            '1' => 0b00011,
            '2' => 0b11001,
            '3' => 0b11011,
            '4' => 0b01111,
            '5' => 0b11110,
            '6' => 0b11100,
            '7' => 0b10011,
            '8' => 0b11101,
            '9' => 0b11111,
            _ => 0,
        }
    }

    /// A settled V01N01 frame: R1 = 05050 (every verified word below is
    /// deliberately 0o5050) and R3 showing `addr`, which is what PINBALL
    /// paints and what `read_erasable` requires before trusting R1.
    fn display_frame(addr: &str) -> DskyState {
        let a: Vec<char> = addr.chars().collect();
        let mut d = DskyState::default();
        for pkt in [
            relay(10, code('0'), code('1')), // VERB 01
            relay(9, code('0'), code('1')),  // NOUN 01
            relay(8, 0, code('0')),          // R1 = 05050
            relay(7, code('5'), code('0')),
            relay(6, code('5'), code('0')),
            relay(3, 0, code(a[0])), // R3 = addr
            relay(2, code(a[1]), code(a[2])),
            relay(1, code(a[3]), code(a[4])),
        ] {
            d.apply(&pkt);
        }
        d
    }

    fn key_char(p: &Packet) -> Option<char> {
        use eagle_agc_protocol::keys::DskyKey;
        [
            ("0", '0'),
            ("1", '1'),
            ("2", '2'),
            ("3", '3'),
            ("4", '4'),
            ("5", '5'),
            ("6", '6'),
            ("7", '7'),
            ("8", '8'),
            ("9", '9'),
            ("ENTR", 'E'),
        ]
        .into_iter()
        .find(|(name, _)| DskyKey::from_name(name).map(|k| k.packet()) == Some(*p))
        .map(|(_, ch)| ch)
    }

    /// Scripted fake PINBALL: watches the key stream and, on every ENTR
    /// that follows five digits, republishes a V01N01 frame whose R3 is
    /// those digits. That is enough for both the V21N01 load path and its
    /// V01N01 read-back to resolve. Keys are forwarded so tests can still
    /// count them.
    fn seeded_script() -> (
        DskyScript,
        tokio::sync::mpsc::UnboundedReceiver<Packet>,
        tokio::sync::watch::Sender<DskyState>,
    ) {
        let (tx, mut raw_rx) = tokio::sync::mpsc::unbounded_channel::<Packet>();
        let (fwd_tx, fwd_rx) = tokio::sync::mpsc::unbounded_channel::<Packet>();
        let (wtx, wrx) = tokio::sync::watch::channel(display_frame("00000"));
        let wtx_task = wtx.clone();
        tokio::spawn(async move {
            let mut digits = String::new();
            while let Some(p) = raw_rx.recv().await {
                match key_char(&p) {
                    Some(c) if c.is_ascii_digit() => {
                        digits.push(c);
                        if digits.len() > 5 {
                            digits.remove(0);
                        }
                    }
                    Some('E') => {
                        if digits.len() == 5 {
                            let _ = wtx_task.send(display_frame(&digits));
                        }
                        digits.clear();
                    }
                    _ => digits.clear(),
                }
                let _ = fwd_tx.send(p);
            }
        });
        let mut script = DskyScript::new(tx, wrx);
        script.set_key_delay(Duration::ZERO);
        (script, fwd_rx, wtx)
    }

    #[tokio::test]
    async fn apply_padload_verification_cadence_and_always_set() {
        let (mut script, mut rx, _wtx) = seeded_script();
        let words = [
            // loaded index 0: stride-verified (0 % 3 == 0).
            PadWord {
                ecadr: 0o2400,
                word: 0o5050,
            },
            // zero word: skipped entirely (cold-boot erasable is zero).
            PadWord {
                ecadr: 0o2401,
                word: 0,
            },
            // loaded index 1: raw keys, no read-back.
            PadWord {
                ecadr: 0o2402,
                word: 0o7,
            },
            // loaded index 2: the stride (every 3rd) would SKIP this one --
            // the always-verify set must force the read-back anyway. This
            // is ZOOMTIME's ECADR, the exact word the review flagged.
            PadWord {
                ecadr: 0o3422,
                word: 0o5050,
            },
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
        // The always-verify word's read-back is present: the LAST 14 keys
        // are KEY REL + V01N01E + its address; V01's "0","1" digits follow
        // VERB.
        let tail = &keys[keys.len() - 14..];
        assert_eq!(
            tail[0],
            eagle_agc_protocol::keys::DskyKey::from_name("KEY_REL")
                .unwrap()
                .packet()
        );
        assert_eq!(tail[1].data, 0o21); // VERB
        assert_eq!(tail[2].data, 0o20); // 0
        assert_eq!(tail[3].data, 0o1); // 1
    }

    #[tokio::test]
    async fn apply_padload_stride_skips_readback_without_always_set() {
        // Same shape, empty always-set: the 0o3422 word must NOT be
        // verified (stride 3 skips loaded-index 2) -- pins that the
        // always-set is what forces the read-back in the test above.
        let (mut script, mut rx, _wtx) = seeded_script();
        let words = [
            PadWord {
                ecadr: 0o2400,
                word: 0o5050,
            },
            PadWord {
                ecadr: 0o2402,
                word: 0o7,
            },
            PadWord {
                ecadr: 0o3422,
                word: 0o5050,
            },
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

    #[test]
    fn a_lit_lamp_is_an_episode_even_with_an_all_zero_failreg() {
        // The tautology this replaces: the old return filtered out zero
        // codes, so with an empty whitelist the ONLY triple that could
        // survive the whitelist check (all zeros) contributed nothing, and
        // `assert!(alarms.is_empty())` could never fail. Recording the
        // EPISODE keeps the assertion falsifiable: the responder RSET a
        // lamp, and the run must say so.
        let ep = AlarmEpisode::new([0; 3], SPIKE_A_ALARM_WHITELIST);
        assert!(ep.acknowledged, "an all-zero FAILREG is swallowed…");
        assert_eq!(ep.codes, [0; 3]);
        // …and is still a reportable episode, i.e. the acceptance assert
        // `alarms.is_empty()` has a way to fire.
        assert!(![ep].is_empty());
    }

    #[test]
    fn episode_acknowledgement_follows_the_whitelist() {
        // 01406 = ROOTPSRS TTF abort; 01204 = zero-dt WAITLIST POODOO.
        let unknown = AlarmEpisode::new([0o1406, 0, 0], SPIKE_A_ALARM_WHITELIST);
        assert!(!unknown.acknowledged, "a non-whitelisted code must abort");
        let listed = AlarmEpisode::new([0o1406, 0, 0], &[0o1406]);
        assert!(listed.acknowledged);
        // Every non-zero code must be listed, not just the first.
        let partly = AlarmEpisode::new([0o1406, 0o1204, 0], &[0o1406]);
        assert!(!partly.acknowledged);
        let both = AlarmEpisode::new([0o1406, 0o1204, 0], &[0o1406, 0o1204]);
        assert!(both.acknowledged);
    }

    #[test]
    fn whitelist_predicate_ignores_zero_padding() {
        assert!(alarm_is_whitelisted(&[0, 0, 0], &[]));
        assert!(alarm_is_whitelisted(&[0, 0o1204, 0], &[0o1204]));
        assert!(!alarm_is_whitelisted(&[0, 0, 0o1204], &[]));
    }
}
