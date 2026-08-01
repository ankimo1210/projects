//! Headless closed-loop driver (Task 16): boot → pump → sim thread →
//! `run_scenario` → descent ROD schedule → touchdown, with no WebSocket
//! server. `main.rs --scenario` and the acceptance test are both callers.
//!
//! Telemetry (and DSKY-state JSON) ride the single `telem_tx` broadcast so
//! a caller that wants a client can serve it directly; a caller that just
//! wants the result subscribes for the summary.
use crate::agc_session::AgcSession;
use crate::padload::{PadloadManifest, SymTab};
use crate::scenario::Scenario;
use crate::script::{pump, DskyScript};
use crate::server::to_msg;
use crate::sim::{spawn_sim, SimCore, SimEvent, SimIn, SimResult};
use crate::{runner, trace::TraceWriter};
use anyhow::{Context, Result};
use eagle_agc_protocol::dsky::DskyState;
use eagle_dynamics::touchdown::Touchdown;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::sync::broadcast;

/// Inputs to a headless run.
pub struct HeadlessCfg {
    pub session: AgcSession,
    pub scenario: Scenario,
    pub symtab: SymTab,
    pub manifest: PadloadManifest,
    /// Telemetry + DSKY JSON are broadcast here.
    pub telem_tx: broadcast::Sender<String>,
    /// Last-frame cache for late subscribers (the server), if any.
    pub latest: Option<Arc<Mutex<String>>>,
    pub trace_out: Option<PathBuf>,
    /// Client → AGC packets from the WebSocket server (scenario mode);
    /// forwarded into the pump so web DSKY keys work mid-run.
    pub client_rx: Option<tokio::sync::mpsc::UnboundedReceiver<eagle_agc_protocol::Packet>>,
    /// Client ROD clicks (+1 = slow descent); merged with the sim's
    /// scheduled clicks into the same RODCOUNT loader.
    pub client_rod_rx: Option<tokio::sync::mpsc::UnboundedReceiver<i32>>,
}

/// What the acceptance test asserts on.
#[derive(Debug, Default, Clone)]
pub struct HeadlessResult {
    pub sim: SimResult,
    /// Major-mode transitions in order (e.g. `["00","63",…,"66"]`).
    pub mm_sequence: Vec<String>,
    /// `drift_ms` from the final telemetry frame.
    pub drift_ms: f64,
    /// `t_s` from the same (final) telemetry frame as `drift_ms` — the sim
    /// seconds `drift_ms` accumulated over, so a caller can turn the
    /// accumulated offset into a scale-free clock RATE.
    pub final_t_s: f64,
    /// A `downlink_wps` sample taken mid-run (post engine-on, pre-touchdown).
    pub mid_downlink_wps: f64,
    /// Seconds of sim time from ENGINE ON (frozen→false) to touchdown.
    pub descent_s: Option<f64>,
    /// PROG-alarm episodes the P63 dialog handled (whitelisted ones only
    /// — anything else aborts the run). One entry per lamp, codes
    /// included; see `runner::AlarmEpisode`.
    pub alarms: Vec<runner::AlarmEpisode>,
    /// DSKY frames with the PROG alarm lamp lit after ENGINE ON and
    /// **before ground contact**. This is the window an acceptance can
    /// gate on: a lamp here was raised while the vehicle was still
    /// flying.
    pub prog_lamp_frames: u64,
    /// DSKY frames with the PROG alarm lamp lit **after** the sim latched
    /// ground contact. `spawn_sim` keeps ticking ~2 s past touchdown with
    /// the AGC still flying a vehicle the sim has already landed, so a
    /// lamp in this window says nothing about whether the landing was
    /// good — M1 run 5's 21 frames were all here. Reported, never gated:
    /// gating it would red an otherwise-good landing, and filtering it
    /// away would discard the only evidence this alarm exists.
    pub prog_lamp_frames_post_contact: u64,
}

#[derive(Default)]
struct Summary {
    mm_sequence: Vec<String>,
    last_mm: String,
    drift_ms: f64,
    last_t_s: f64,
    downlink_samples: Vec<f64>,
    engine_on_t: Option<f64>,
    touchdown_t: Option<f64>,
    prog_lamp_frames: u64,
    prog_lamp_frames_post_contact: u64,
}

impl Summary {
    fn note(&mut self, msg: &eagle_schema::ServerMsg) {
        match msg {
            eagle_schema::ServerMsg::Telemetry(t) => {
                // `trim()`: the DSKY paints a BLANK major mode ("  ") on a
                // fresh boot, which is not a mode transition.
                if t.mm != self.last_mm && !t.mm.trim().is_empty() {
                    self.mm_sequence.push(t.mm.clone());
                    self.last_mm = t.mm.clone();
                }
                self.drift_ms = t.drift_ms;
                self.last_t_s = t.t_s;
                if !t.frozen {
                    if self.engine_on_t.is_none() {
                        self.engine_on_t = Some(t.t_s);
                    }
                    if t.touchdown.is_none() {
                        self.downlink_samples.push(t.downlink_wps);
                    } else if self.touchdown_t.is_none() {
                        self.touchdown_t = Some(t.t_s);
                    }
                }
            }
            eagle_schema::ServerMsg::DskyState(d) => {
                // enter_p63 handles pre-ignition alarms (bails on
                // non-whitelisted). Post-engine-on, nobody else watches
                // the lamp — count lit frames here.
                //
                // Split at ground contact: the sim runs ~2 s past
                // touchdown with the AGC still flying a vehicle it has
                // latched as landed, so a lamp raised in that tail is
                // not evidence about the landing. Ledger open item 2a.
                if self.engine_on_t.is_some() && d.lamps.get("prog").copied().unwrap_or(false) {
                    if self.touchdown_t.is_some() {
                        self.prog_lamp_frames_post_contact += 1;
                    } else {
                        self.prog_lamp_frames += 1;
                    }
                }
            }
        }
    }
}

/// Run the full closed loop to touchdown (or until the sim thread exits).
pub async fn run_headless(cfg: HeadlessCfg) -> Result<HeadlessResult> {
    let (dsky_rx, cmd_tx, pkt_rx, _pump) = pump(cfg.session);

    // Gate: true while `script` (the choreography, or a rod_load call) is
    // mid-sequence. A client keystroke landing between a script's own
    // terminal-key sends (e.g. rod_load's V21N01E…E…E erasable write)
    // would interleave with it and corrupt e.g. RODCOUNT, so the
    // client-key forwarder below drops packets while this is set. ROD
    // clicks are unaffected — they already serialize through the merged
    // loop further down.
    let script_busy = Arc::new(AtomicBool::new(false));

    // Client → AGC packets from the WebSocket server (scenario mode): the
    // fix for silently-dropped web DSKY key presses — forward them into the
    // same pump `cmd_tx` the DSKY choreography uses, unless the script is
    // mid-sequence.
    if let Some(rx) = cfg.client_rx {
        tokio::spawn(forward_client_keys(rx, cmd_tx.clone(), script_busy.clone()));
    }

    let core = SimCore::new(&cfg.scenario, 0.0);
    let (sim_in_tx, sim_in_rx) = std::sync::mpsc::channel::<SimIn>();
    let (event_tx, mut event_rx) = tokio::sync::mpsc::unbounded_channel::<SimEvent>();
    let sim = spawn_sim(
        core,
        sim_in_rx,
        cmd_tx.clone(),
        cfg.telem_tx.clone(),
        event_tx,
    );

    // Packet forwarder: trace, decode → SimIn, and DSKY-state JSON broadcast.
    let mut fwd = pkt_rx.resubscribe();
    let telem_tx = cfg.telem_tx.clone();
    let latest = cfg.latest.clone();
    let trace_out = cfg.trace_out.clone();
    let fwd_in = sim_in_tx.clone();
    tokio::spawn(async move {
        let mut trace = TraceWriter::open(trace_out).ok();
        let mut dsky = DskyState::default();
        loop {
            match fwd.recv().await {
                Ok(pkt) => {
                    if let Some(t) = trace.as_mut() {
                        t.log("out", &pkt);
                    }
                    for ev in crate::sim::agc_packet_to_simin(&pkt, &mut dsky) {
                        let dsky_changed = matches!(ev, SimIn::Dsky(_));
                        let _ = fwd_in.send(ev);
                        if dsky_changed {
                            if let Ok(json) = serde_json::to_string(&to_msg(&dsky)) {
                                if let Some(l) = &latest {
                                    *l.lock().unwrap() = json.clone();
                                }
                                let _ = telem_tx.send(json);
                            }
                        }
                    }
                }
                Err(broadcast::error::RecvError::Lagged(_)) => continue,
                Err(broadcast::error::RecvError::Closed) => break,
            }
        }
    });

    // Telemetry collector: MM transitions, drift, downlink, engine-on/touchdown.
    let summary = Arc::new(Mutex::new(Summary::default()));
    let collector = tokio::spawn(collect_telemetry(cfg.telem_tx.subscribe(), summary.clone()));

    // Choreography, then serve the sim's events. Where the choreography
    // ends is mode-dependent (`runner::run_scenario`): hover mode carries
    // it all the way to MM66, PDI mode stops at ENGINE ON and leaves the
    // P64→P66 handover to the event loop below.
    let mut script = DskyScript::new(cmd_tx.clone(), dsky_rx);
    script.set_key_delay(Duration::from_millis(30));
    let mut responder = pkt_rx.resubscribe();
    script_busy.store(true, Ordering::SeqCst);
    let choreography = runner::run_scenario(
        &mut script,
        &cfg.scenario,
        &cfg.symtab,
        &cfg.manifest,
        &cmd_tx,
        &mut responder,
    )
    .await;
    script_busy.store(false, Ordering::SeqCst);
    // A failed choreography must not leak the sim thread: stop it and join
    // before propagating, or the caller (a test binary) returns with a
    // 100 Hz thread still pumping packets at a dead AGC.
    let report = match choreography.context("scenario choreography") {
        Ok(r) => r,
        Err(e) => {
            let _ = sim.stop.send(());
            drop(sim_in_tx);
            let _ = tokio::task::spawn_blocking(move || sim.join.join()).await;
            collector.abort();
            return Err(e);
        }
    };

    // Deliver sim events (ROD clicks from both sources, and the P64→P66
    // handover) through the one DskyScript. `next_sim_event` biases toward
    // the SIM channel, so it returns `None` only when the SIM channel
    // closes (sim thread exited on touchdown + 2 s); a closed client
    // channel just stops that source. Every action here gates the
    // client-key forwarder above, since each does its own terminal-key
    // sequence (V21N01E…E…E) that a stray client key must not interleave
    // with.
    let mut client_rod_rx = cfg.client_rod_rx;
    while let Some(ev) = next_sim_event(&mut event_rx, &mut client_rod_rx).await {
        script_busy.store(true, Ordering::SeqCst);
        let r = match ev {
            SimEvent::RodClicks(n) => rod_load_verified(&mut script, n as i16, &sim_in_tx).await,
            SimEvent::Handover => {
                // ATT HOLD flips GUILDENSTERN's mode check (STABL?, the
                // un-attitude-hold discrete); the selection click gives it
                // the nonzero RODCOUNT that sends it to STARTP66
                // (vendor/virtualagc/Luminary099/
                // LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:203-217).
                match runner::att_hold(&cmd_tx).await {
                    Ok(()) => rod_load_verified(&mut script, -1, &sim_in_tx).await,
                    Err(e) => Err(e),
                }
            }
        };
        script_busy.store(false, Ordering::SeqCst);
        if let Err(e) = r {
            eprintln!("headless: sim event failed: {e:#}");
        }
    }
    // event_rx closed ⇒ the sim thread exited (touchdown + 2 s or channel close).
    drop(sim_in_tx);
    let sim_result = tokio::task::spawn_blocking(move || sim.join.join())
        .await
        .context("join sim thread")?
        .map_err(|_| anyhow::anyhow!("sim thread panicked"))?;
    collector.abort();

    let s = summary.lock().unwrap();
    let descent_s = match (s.engine_on_t, s.touchdown_t) {
        (Some(e), Some(td)) => Some(td - e),
        _ => None,
    };
    let mid = if s.downlink_samples.is_empty() {
        0.0
    } else {
        s.downlink_samples[s.downlink_samples.len() / 2]
    };
    Ok(HeadlessResult {
        sim: sim_result,
        mm_sequence: s.mm_sequence.clone(),
        drift_ms: s.drift_ms,
        final_t_s: s.last_t_s,
        mid_downlink_wps: mid,
        descent_s,
        alarms: report.alarms,
        prog_lamp_frames: s.prog_lamp_frames,
        prog_lamp_frames_post_contact: s.prog_lamp_frames_post_contact,
    })
}

/// Fold every broadcast frame into `sum` until the channel closes.
///
/// `Lagged` must NOT end this loop. It is a normal event on a 256-slot
/// broadcast (scenario mode, `main.rs:43`) whenever the sim outruns this
/// task for a moment, and returning on it freezes mm_sequence / drift_ms /
/// final_t_s / descent_s / prog_lamp_frames at whatever they last were —
/// after which every acceptance assert passes on stale data instead of
/// ROD loads the AGC has been checked to accept, reporting the applied
/// click count back to the sim.
///
/// The AGC can silently refuse a load: an entry typed into P66's VERTDISP
/// repaint stream is rejected with OPR ERR and KEY REL lit, leaving
/// RODCOUNT unwritten and VDGVERT unmoved (`runner::rod_load`'s note,
/// spike-B iter 18). Before 2026-07-31 nothing noticed, so a refused click
/// vanished: the vehicle flew a commanded rate nobody had asked for, and
/// `rod_clicks_cum` counted it anyway.
///
/// One retry, then give up loudly. `grab_dsky` already waits for a repaint
/// gap, so a retry lands in a different part of the guidance pass than the
/// attempt that failed; retrying forever would just type into a display
/// that is not going to yield.
async fn rod_load_verified(
    script: &mut DskyScript,
    clicks: i16,
    sim_in_tx: &std::sync::mpsc::Sender<SimIn>,
) -> Result<()> {
    const ATTEMPTS: u32 = 2;
    for attempt in 1..=ATTEMPTS {
        let status = runner::rod_load(script, clicks).await?;
        if !status.rejected() {
            // Only clicks the AGC took are clicks VDGVERT moved by.
            let _ = sim_in_tx.send(SimIn::RodApplied(i32::from(clicks)));
            return Ok(());
        }
        eprintln!(
            "headless: ROD load {clicks:+} REJECTED by the AGC              (key_rel={} opr_err={}), attempt {attempt}/{ATTEMPTS}",
            status.key_rel, status.opr_err
        );
    }
    // Not an error: the descent continues, and the run is still worth
    // flying. But the commanded rate is now NOT what the schedule asked
    // for, and every later analysis has to know that.
    eprintln!(
        "headless: ROD load {clicks:+} GAVE UP after {ATTEMPTS} attempts —          VDGVERT did not move; rod_clicks_cum excludes these clicks"
    );
    Ok(())
}

/// failing. The packet forwarder in `run_headless` already does the same
/// `continue`.
async fn collect_telemetry(mut telem_rx: broadcast::Receiver<String>, sum: Arc<Mutex<Summary>>) {
    // Optional per-frame telemetry dump for descent-profile debugging.
    // Fail LOUDLY if the dump cannot be opened. This used to be
    // `.and_then(|p| File::create(p).ok())`, which silently disabled the
    // instrumentation — and since the runtime's cwd is `runtime/` (the
    // Makefile does `cd runtime && cargo run`), the natural
    // `EAGLE_TELEM_OUT=build/traces/x.jsonl` from the repo root resolves
    // to a directory that does not exist and lands in exactly that hole.
    // It cost a full 20-minute descent on 2026-07-31.
    let mut dump = match std::env::var("EAGLE_TELEM_OUT") {
        Ok(path) => Some(std::fs::File::create(&path).unwrap_or_else(|e| {
            panic!(
                "EAGLE_TELEM_OUT={path}: cannot create ({e}). The runtime's cwd \
                 is `runtime/`, so a RELATIVE path resolves under it — pass an \
                 absolute path. Refusing to fly with instrumentation off."
            )
        })),
        Err(_) => None,
    };
    loop {
        let json = match telem_rx.recv().await {
            Ok(json) => json,
            Err(broadcast::error::RecvError::Lagged(n)) => {
                eprintln!("headless: telemetry collector lagged, {n} frame(s) dropped");
                continue;
            }
            Err(broadcast::error::RecvError::Closed) => break,
        };
        // DSKY-state frames ride the same broadcast; both are noted,
        // only telemetry is dumped.
        let Ok(msg) = serde_json::from_str::<eagle_schema::ServerMsg>(&json) else {
            continue;
        };
        if matches!(msg, eagle_schema::ServerMsg::Telemetry(_)) {
            if let Some(f) = dump.as_mut() {
                use std::io::Write;
                let _ = writeln!(f, "{json}");
            }
        }
        sum.lock().unwrap().note(&msg);
    }
}

/// The touchdown classification from a finished run, if any.
pub fn touchdown_class(r: &HeadlessResult) -> Option<Touchdown> {
    r.sim.touchdown.map(|t| t.class)
}

/// Forward client → AGC packets (web DSKY key/PRO presses) into `tx`,
/// dropping them while `busy` is set — a client keystroke landing between
/// a script's own terminal-key sends (choreography, or a `rod_load`
/// erasable write) would interleave with it and corrupt e.g. RODCOUNT.
/// Exits when `rx` closes (the WebSocket server task ended) or `tx`'s
/// receiver is gone (the pump exited).
async fn forward_client_keys(
    mut rx: tokio::sync::mpsc::UnboundedReceiver<eagle_agc_protocol::Packet>,
    tx: tokio::sync::mpsc::UnboundedSender<eagle_agc_protocol::Packet>,
    busy: Arc<AtomicBool>,
) {
    while let Some(pkt) = rx.recv().await {
        if busy.load(Ordering::SeqCst) {
            eprintln!("headless: client key dropped (script busy)");
            continue;
        }
        if tx.send(pkt).is_err() {
            break;
        }
    }
}

/// Merge sim events and client ROD clicks into one stream (a client click
/// arrives as `SimEvent::RodClicks`). Biased toward the SIM channel, so it
/// always wins a race against a backlog of pending client clicks — a
/// closing sim (touchdown + 2 s) must end the loop promptly, not dawdle on
/// client input, and a handover must not queue behind stale clicks.
/// Returns `None` only when the SIM channel closes; a closed client
/// channel just clears `client` and keeps serving the sim side.
async fn next_sim_event(
    event_rx: &mut tokio::sync::mpsc::UnboundedReceiver<SimEvent>,
    client: &mut Option<tokio::sync::mpsc::UnboundedReceiver<i32>>,
) -> Option<SimEvent> {
    loop {
        tokio::select! {
            biased;
            ev = event_rx.recv() => return ev,
            n = async {
                match client.as_mut() {
                    Some(rx) => rx.recv().await,
                    None => std::future::pending().await,
                }
            } => match n {
                Some(n) => return Some(SimEvent::RodClicks(n)),
                None => {
                    *client = None;
                    continue;
                }
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eagle_agc_protocol::Packet;
    use eagle_schema::{DskyStateMsg, ServerMsg, TelemetryMsg, SCHEMA_VERSION};
    use tokio::sync::mpsc;

    fn telem(t_s: f64, mm: &str, frozen: bool) -> ServerMsg {
        ServerMsg::Telemetry(TelemetryMsg {
            schema_version: SCHEMA_VERSION,
            t_s,
            frozen,
            alt_m: 100.0,
            vz_ms: -1.0,
            v_horiz_ms: 0.0,
            tilt_deg: 0.0,
            mass_kg: 9000.0,
            fuel_dps_kg: 1000.0,
            fuel_rcs_kg: 100.0,
            thrust_n: 0.0,
            throttle_cmd_pulses: 0,
            rod_clicks_cum: 0,
            pipa_pulses_cum: [0; 3],
            jets: 0,
            mm: mm.into(),
            agc_alt_m: None,
            agc_hdot_ms: None,
            nav_err_alt_m: None,
            nav_err_hdot_ms: None,
            drift_ms: 0.0,
            downlink_wps: 50.0,
            ingest_drops: 0,
            touchdown: None,
            handover: false,
        })
    }

    fn dsky(prog_lamp: bool) -> ServerMsg {
        let mut m = DskyStateMsg::default();
        m.lamps.insert("prog".into(), prog_lamp);
        ServerMsg::DskyState(m)
    }

    #[test]
    fn summary_tracks_mm_engine_on_and_prog_lamp() {
        let mut s = Summary::default();
        s.note(&telem(1.0, "63", true));
        s.note(&telem(2.0, "63", true));
        s.note(&dsky(true)); // pre-engine-on lamp: enter_p63 handles it
        assert_eq!(s.prog_lamp_frames, 0);
        s.note(&telem(3.0, "63", false)); // engine on
        assert_eq!(s.engine_on_t, Some(3.0));
        s.note(&telem(4.0, "66", false));
        assert_eq!(s.mm_sequence, vec!["63".to_string(), "66".to_string()]);
        s.note(&dsky(true)); // descent-phase PROG lamp must be counted
        s.note(&dsky(false));
        assert_eq!(s.prog_lamp_frames, 1);
    }

    #[test]
    fn prog_lamp_frames_split_at_ground_contact() {
        // Ledger open item 2a: the counter runs through the sim's ~2 s
        // post-touchdown tail, with the AGC still flying a vehicle the
        // sim has latched as landed. Run 5 of the M1 flights counted 21
        // lamp frames, ALL of them after contact, and the acceptance's
        // `prog_lamp_frames == 0` gate would have failed a run that had
        // already landed. Both windows are kept: the gate reads the
        // pre-contact count, and the post-contact count stays visible
        // because it is the only evidence the alarm exists at all.
        let mut s = Summary::default();
        s.note(&telem(1.0, "63", false)); // engine on
        s.note(&dsky(true));
        assert_eq!(s.prog_lamp_frames, 1);
        assert_eq!(s.prog_lamp_frames_post_contact, 0);

        let mut td = telem(2.0, "66", false);
        if let ServerMsg::Telemetry(t) = &mut td {
            t.touchdown = Some("Hard".into());
        }
        s.note(&td);
        s.note(&dsky(true));
        assert_eq!(
            s.prog_lamp_frames, 1,
            "the pre-contact counter must not move after touchdown"
        );
        assert_eq!(s.prog_lamp_frames_post_contact, 1);
    }

    #[test]
    fn summary_ignores_the_blank_major_mode() {
        // The DSKY paints "  " before the first V37, which is not a mode.
        let mut s = Summary::default();
        s.note(&telem(1.0, "  ", true));
        assert!(s.mm_sequence.is_empty(), "blank MM is not a transition");
        s.note(&telem(2.0, "00", true));
        assert_eq!(s.mm_sequence, vec!["00".to_string()]);
    }

    #[tokio::test]
    async fn collector_keeps_collecting_after_broadcast_lag() {
        // A single `RecvError::Lagged` used to end the collector for good,
        // freezing the summary while the acceptance asserts read on. Fill
        // a small channel past its capacity BEFORE the collector polls,
        // then check that a later frame still lands in the summary.
        let (tx, rx) = broadcast::channel::<String>(2);
        for t in 1..=6 {
            tx.send(serde_json::to_string(&telem(f64::from(t), "63", true)).unwrap())
                .unwrap();
        }
        let sum = Arc::new(Mutex::new(Summary::default()));
        let handle = tokio::spawn(collect_telemetry(rx, sum.clone()));

        tx.send(serde_json::to_string(&telem(99.0, "66", false)).unwrap())
            .unwrap();
        // Poll rather than sleep a fixed time: the collector must merely
        // get there, and the lagged frames are dropped by the channel.
        for _ in 0..400 {
            if sum.lock().unwrap().last_t_s == 99.0 {
                break;
            }
            tokio::time::sleep(Duration::from_millis(5)).await;
        }
        let s = sum.lock().unwrap();
        assert_eq!(
            s.last_t_s, 99.0,
            "collector died on Lagged and froze the summary"
        );
        assert_eq!(s.last_mm, "66");
        drop(s);
        handle.abort();
    }

    #[test]
    fn summary_pairs_the_final_drift_with_the_final_clock() {
        // The acceptance gate divides `drift_ms` by the sim seconds it
        // accumulated over, so both must come from the SAME (last) frame.
        let mut s = Summary::default();
        s.note(&telem(1.0, "63", true));
        let ServerMsg::Telemetry(mut t) = telem(410.5, "66", false) else {
            unreachable!()
        };
        t.drift_ms = -17_900.0;
        s.note(&ServerMsg::Telemetry(t));
        assert_eq!(s.drift_ms, -17_900.0);
        assert_eq!(s.last_t_s, 410.5);
    }

    #[tokio::test]
    async fn forward_client_keys_forwards_when_not_busy() {
        let (client_tx, client_rx) = mpsc::unbounded_channel::<Packet>();
        let (out_tx, mut out_rx) = mpsc::unbounded_channel::<Packet>();
        let busy = Arc::new(AtomicBool::new(false));
        tokio::spawn(forward_client_keys(client_rx, out_tx, busy));

        let pkt = Packet::io(0o15, 1).unwrap();
        client_tx.send(pkt).unwrap();
        assert_eq!(out_rx.recv().await, Some(pkt));
    }

    #[tokio::test]
    async fn forward_client_keys_drops_when_busy() {
        let (client_tx, client_rx) = mpsc::unbounded_channel::<Packet>();
        let (out_tx, mut out_rx) = mpsc::unbounded_channel::<Packet>();
        let busy = Arc::new(AtomicBool::new(true));
        tokio::spawn(forward_client_keys(client_rx, out_tx, busy));

        client_tx.send(Packet::io(0o15, 1).unwrap()).unwrap();
        // Give the forwarder task a chance to run and drop the key.
        tokio::task::yield_now().await;
        assert!(
            out_rx.try_recv().is_err(),
            "a busy forwarder must drop the key, not forward it"
        );
    }

    #[tokio::test]
    async fn forward_client_keys_resumes_once_busy_clears() {
        let (client_tx, client_rx) = mpsc::unbounded_channel::<Packet>();
        let (out_tx, mut out_rx) = mpsc::unbounded_channel::<Packet>();
        let busy = Arc::new(AtomicBool::new(true));
        tokio::spawn(forward_client_keys(client_rx, out_tx, busy.clone()));

        // Dropped while busy.
        client_tx.send(Packet::io(0o15, 1).unwrap()).unwrap();
        tokio::task::yield_now().await;
        assert!(out_rx.try_recv().is_err());

        // Forwarded once the gate opens.
        busy.store(false, Ordering::SeqCst);
        let resumed = Packet::io(0o15, 2).unwrap();
        client_tx.send(resumed).unwrap();
        assert_eq!(out_rx.recv().await, Some(resumed));
    }

    #[tokio::test]
    async fn handover_event_passes_through_and_sim_close_still_terminates() {
        // The Task-3 shim dropped `Handover` on the floor; the merged loop
        // must deliver it like any other sim event, and closing the sim
        // channel must still end the loop.
        let (sim_tx, mut sim_rx_holder) = tokio::sync::mpsc::unbounded_channel();
        let mut client: Option<tokio::sync::mpsc::UnboundedReceiver<i32>> = None;
        sim_tx.send(SimEvent::Handover).unwrap();
        assert_eq!(
            next_sim_event(&mut sim_rx_holder, &mut client).await,
            Some(SimEvent::Handover)
        );
        drop(sim_tx);
        assert_eq!(next_sim_event(&mut sim_rx_holder, &mut client).await, None);
    }

    #[tokio::test]
    async fn next_sim_event_delivers_from_both_sources() {
        let (sim_tx, mut sim_rx) = mpsc::unbounded_channel::<SimEvent>();
        let (client_tx, client_rx) = mpsc::unbounded_channel::<i32>();
        let mut client = Some(client_rx);

        sim_tx.send(SimEvent::RodClicks(1)).unwrap();
        client_tx.send(2).unwrap();

        // biased: the sim value is checked (and returned) first even
        // though both are ready.
        assert_eq!(
            next_sim_event(&mut sim_rx, &mut client).await,
            Some(SimEvent::RodClicks(1))
        );
        assert_eq!(
            next_sim_event(&mut sim_rx, &mut client).await,
            Some(SimEvent::RodClicks(2))
        );
    }

    #[tokio::test]
    async fn next_sim_event_keeps_serving_sim_after_client_closes() {
        let (sim_tx, mut sim_rx) = mpsc::unbounded_channel::<SimEvent>();
        let (client_tx, client_rx) = mpsc::unbounded_channel::<i32>();
        let mut client = Some(client_rx);
        drop(client_tx); // client channel closes with nothing pending

        let sender = tokio::spawn(async move {
            // Let next_sim_event observe the closed client channel and
            // clear it before the sim value shows up.
            tokio::task::yield_now().await;
            sim_tx.send(SimEvent::RodClicks(7)).unwrap();
        });

        assert_eq!(
            next_sim_event(&mut sim_rx, &mut client).await,
            Some(SimEvent::RodClicks(7))
        );
        assert!(
            client.is_none(),
            "closed client receiver must be cleared internally"
        );
        sender.await.unwrap();
    }

    #[tokio::test]
    async fn next_sim_event_ends_on_sim_close_even_with_client_pending() {
        let (sim_tx, mut sim_rx) = mpsc::unbounded_channel::<SimEvent>();
        let (client_tx, client_rx) = mpsc::unbounded_channel::<i32>();
        let mut client = Some(client_rx);

        client_tx.send(9).unwrap(); // a client click is waiting…
        drop(sim_tx); // …but the sim channel closes with nothing buffered

        // biased must prefer the (closed) sim arm, so the loop ends with
        // None instead of returning the pending client click.
        assert_eq!(next_sim_event(&mut sim_rx, &mut client).await, None);
    }
}
