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
use crate::sim::{spawn_sim, DskyStateSnapshot, SimCore, SimIn, SimResult};
use crate::{runner, trace::TraceWriter};
use anyhow::{Context, Result};
use eagle_agc_protocol::agc_io::decode_output;
use eagle_agc_protocol::dsky::DskyState;
use eagle_dynamics::touchdown::Touchdown;
use std::path::PathBuf;
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
}

/// What the acceptance test asserts on.
#[derive(Debug, Default, Clone)]
pub struct HeadlessResult {
    pub sim: SimResult,
    /// Major-mode transitions in order (e.g. `["00","63",…,"66"]`).
    pub mm_sequence: Vec<String>,
    /// `drift_ms` from the final telemetry frame.
    pub drift_ms: f64,
    /// A `downlink_wps` sample taken mid-run (post engine-on, pre-touchdown).
    pub mid_downlink_wps: f64,
    /// Seconds of sim time from ENGINE ON (frozen→false) to touchdown.
    pub descent_s: Option<f64>,
}

#[derive(Default)]
struct Summary {
    mm_sequence: Vec<String>,
    last_mm: String,
    drift_ms: f64,
    downlink_samples: Vec<f64>,
    engine_on_t: Option<f64>,
    touchdown_t: Option<f64>,
}

/// Run the full closed loop to touchdown (or until the sim thread exits).
pub async fn run_headless(cfg: HeadlessCfg) -> Result<HeadlessResult> {
    let (dsky_rx, cmd_tx, pkt_rx, _pump) = pump(cfg.session);

    let core = SimCore::new(&cfg.scenario, 0.0);
    let (sim_in_tx, sim_in_rx) = std::sync::mpsc::channel::<SimIn>();
    let (rod_tx, mut rod_rx) = tokio::sync::mpsc::unbounded_channel::<i32>();
    let sim = spawn_sim(
        core,
        sim_in_rx,
        cmd_tx.clone(),
        cfg.telem_tx.clone(),
        rod_tx,
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
                    let _ = fwd_in.send(SimIn::Agc(decode_output(&pkt)));
                    if dsky.apply(&pkt) {
                        let _ = fwd_in.send(SimIn::Dsky(DskyStateSnapshot::from_dsky(&dsky)));
                        if let Ok(json) = serde_json::to_string(&to_msg(&dsky)) {
                            if let Some(l) = &latest {
                                *l.lock().unwrap() = json.clone();
                            }
                            let _ = telem_tx.send(json);
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
    let mut telem_rx = cfg.telem_tx.subscribe();
    let sum = summary.clone();
    let collector = tokio::spawn(async move {
        // Optional per-frame telemetry dump for descent-profile debugging.
        let mut dump = std::env::var("EAGLE_TELEM_OUT")
            .ok()
            .and_then(|p| std::fs::File::create(p).ok());
        while let Ok(json) = telem_rx.recv().await {
            let Ok(eagle_schema::ServerMsg::Telemetry(t)) = serde_json::from_str(&json) else {
                continue; // DSKY frames ride the same broadcast
            };
            if let Some(f) = dump.as_mut() {
                use std::io::Write;
                let _ = writeln!(f, "{json}");
            }
            let mut s = sum.lock().unwrap();
            if t.mm != s.last_mm && !t.mm.is_empty() {
                s.mm_sequence.push(t.mm.clone());
                s.last_mm = t.mm.clone();
            }
            s.drift_ms = t.drift_ms;
            if !t.frozen {
                if s.engine_on_t.is_none() {
                    s.engine_on_t = Some(t.t_s);
                }
                if t.touchdown.is_none() {
                    s.downlink_samples.push(t.downlink_wps);
                } else if s.touchdown_t.is_none() {
                    s.touchdown_t = Some(t.t_s);
                }
            }
        }
    });

    // Choreography to MM66, then deliver the descent ROD schedule.
    let mut script = DskyScript::new(cmd_tx.clone(), dsky_rx);
    script.set_key_delay(Duration::from_millis(30));
    let mut responder = pkt_rx.resubscribe();
    runner::run_scenario(
        &mut script,
        &cfg.scenario,
        &cfg.symtab,
        &cfg.manifest,
        &cmd_tx,
        &mut responder,
    )
    .await
    .context("scenario choreography")?;

    while let Some(n) = rod_rx.recv().await {
        if let Err(e) = runner::rod_load(&mut script, n as i16).await {
            eprintln!("headless: ROD load failed: {e:#}");
        }
    }
    // rod_rx closed ⇒ the sim thread exited (touchdown + 2 s or channel close).
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
        mid_downlink_wps: mid,
        descent_s,
    })
}

/// The touchdown classification from a finished run, if any.
pub fn touchdown_class(r: &HeadlessResult) -> Option<Touchdown> {
    r.sim.touchdown.map(|(t, _, _, _)| t)
}
