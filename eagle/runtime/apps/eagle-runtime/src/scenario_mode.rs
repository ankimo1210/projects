//! Closed-loop `--scenario` driver (Task 14). Owns the yaAGC socket via
//! `pump`, spawns the sim thread, forwards packets both ways, runs the
//! productized choreography (`runner::run_scenario`) up to P66, then keeps
//! delivering the descent ROD schedule the sim emits (as RODCOUNT loads).
use anyhow::{Context, Result};
use eagle_agc_protocol::dsky::DskyState;
use eagle_runtime::agc_session::AgcSession;
use eagle_runtime::padload::{PadloadManifest, SymTab};
use eagle_runtime::scenario::Scenario;
use eagle_runtime::script::{pump, DskyScript};
use eagle_runtime::server::to_msg;
use eagle_runtime::sim::{spawn_sim, SimCore, SimIn};
use eagle_runtime::{runner, trace::TraceWriter};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::sync::broadcast;

/// Everything the driver needs from `main`.
pub struct Cfg {
    pub session: AgcSession,
    pub scenario: PathBuf,
    pub root: PathBuf,
    pub state_tx: broadcast::Sender<String>,
    pub latest: Arc<Mutex<String>>,
    pub trace_out: Option<PathBuf>,
}

pub async fn run(cfg: Cfg) -> Result<()> {
    let sc = Scenario::load(&cfg.scenario)?;
    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(cfg.root.join("build/agc/Luminary099.log"))
            .context("reading build/agc/Luminary099.log (run `make agc`)")?,
    )?;
    let manifest = PadloadManifest::load(&cfg.root.join(&sc.agc.padload))?;

    let (dsky_rx, cmd_tx, pkt_rx, _pump) = pump(cfg.session);

    // Sim thread: fed by the packet forwarder, sends PIPA/CDU/DINC back via
    // the same command channel, broadcasts telemetry, and signals ROD clicks.
    let core = SimCore::new(&sc, 0.0);
    let (sim_in_tx, sim_in_rx) = std::sync::mpsc::channel::<SimIn>();
    let (rod_tx, mut rod_rx) = tokio::sync::mpsc::unbounded_channel::<i32>();
    let _sim = spawn_sim(core, sim_in_rx, cmd_tx.clone(), cfg.state_tx.clone(), rod_tx);

    // Forwarder: every AGC packet → trace, DSKY JSON broadcast, and SimIn.
    let mut fwd_pkts = pkt_rx.resubscribe();
    let state_tx = cfg.state_tx.clone();
    let latest = cfg.latest.clone();
    let trace_out = cfg.trace_out.clone();
    let fwd_sim_in = sim_in_tx.clone();
    tokio::spawn(async move {
        let mut trace = TraceWriter::open(trace_out).ok();
        let mut dsky = DskyState::default();
        loop {
            match fwd_pkts.recv().await {
                Ok(pkt) => {
                    if let Some(t) = trace.as_mut() {
                        t.log("out", &pkt);
                    }
                    let changed = dsky.apply(&pkt);
                    let _ = fwd_sim_in.send(SimIn::Agc(
                        eagle_agc_protocol::agc_io::decode_output(&pkt),
                    ));
                    if changed {
                        let _ = fwd_sim_in.send(SimIn::Dsky(
                            eagle_runtime::sim::DskyStateSnapshot::from_dsky(&dsky),
                        ));
                        if let Ok(json) = serde_json::to_string(&to_msg(&dsky)) {
                            *latest.lock().unwrap() = json.clone();
                            let _ = state_tx.send(json);
                        }
                    }
                }
                Err(broadcast::error::RecvError::Lagged(_)) => continue,
                Err(broadcast::error::RecvError::Closed) => break,
            }
        }
    });

    // Choreography: boot → pad-load → P63 → ENGINE ON → ATT HOLD → MM66.
    let mut script = DskyScript::new(cmd_tx.clone(), dsky_rx);
    script.set_key_delay(Duration::from_millis(30));
    let mut responder_pkts = pkt_rx.resubscribe();
    runner::run_scenario(
        &mut script,
        &sc,
        &symtab,
        &manifest,
        &cmd_tx,
        &mut responder_pkts,
    )
    .await
    .context("scenario choreography")?;
    eprintln!("scenario: *** MM66 *** — descent ROD schedule now live");

    // Deliver the sim's descent ROD schedule as RODCOUNT loads until the
    // sim thread finishes (channel closes) or a shutdown signal arrives.
    loop {
        tokio::select! {
            clicks = rod_rx.recv() => match clicks {
                Some(n) => {
                    if let Err(e) = runner::rod_load(&mut script, n as i16).await {
                        eprintln!("scenario: ROD load failed: {e:#}");
                    }
                }
                None => break,
            },
            _ = tokio::signal::ctrl_c() => break,
        }
    }
    // Keep sim_in_tx alive for the whole run.
    drop(sim_in_tx);
    Ok(())
}
