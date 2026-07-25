//! Closed-loop `--scenario` driver (Task 14/16): a thin wrapper over
//! `headless::run_headless` that also feeds the WebSocket server's
//! broadcast (telemetry + DSKY JSON already ride `state_tx`).
use anyhow::{Context, Result};
use eagle_runtime::agc_session::AgcSession;
use eagle_runtime::headless::{run_headless, touchdown_class, HeadlessCfg};
use eagle_runtime::padload::{PadloadManifest, SymTab};
use eagle_runtime::scenario::Scenario;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
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

    eprintln!("scenario: closed loop starting ({})", sc.name);
    let result = run_headless(HeadlessCfg {
        session: cfg.session,
        scenario: sc,
        symtab,
        manifest,
        telem_tx: cfg.state_tx,
        latest: Some(cfg.latest),
        trace_out: cfg.trace_out,
    })
    .await?;

    eprintln!(
        "scenario: done — MM {:?}, touchdown {:?}, descent {:?} s, drift {:.0} ms",
        result.mm_sequence,
        touchdown_class(&result),
        result.descent_s,
        result.drift_ms
    );
    Ok(())
}
