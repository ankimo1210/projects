//! Closed-loop `--scenario` driver (Task 14/16): a thin wrapper over
//! `headless::run_headless` that also feeds the WebSocket server's
//! broadcast (telemetry + DSKY JSON already ride `state_tx`).
use anyhow::{Context, Result};
use eagle_agc_protocol::Packet;
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
    /// Client → AGC packets from the WebSocket server (web DSKY key presses).
    pub client_rx: tokio::sync::mpsc::UnboundedReceiver<Packet>,
    /// Client ROD clicks (+1 = slow descent) from the ENGR tab.
    pub client_rod_rx: tokio::sync::mpsc::UnboundedReceiver<i32>,
}

pub async fn run(cfg: Cfg) -> Result<()> {
    let sc = Scenario::load(&cfg.scenario)?;
    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(cfg.root.join("build/agc/Luminary099.log"))
            .context("reading build/agc/Luminary099.log (run `make agc`)")?,
    )?;
    let manifest = PadloadManifest::load(&cfg.root.join(&sc.agc.padload))?;

    // Forensic instrument, off by default: sample yaAGC's periodic core
    // dump into a CSV time series of R12's working set. This is the read
    // side of the 2026-08-03 investigation — the downlink cannot reach
    // DELTAH or RGU (no offset/scale matches the AGC's own altitude better
    // than ~300 m median), while the dump gives every word by symbol.
    // Sampling is passive; it does NOT shorten the dump interval, so the
    // `EAGLE_DUMP_TIME` boot hazard is not incurred.
    if let Ok(path) = std::env::var("EAGLE_CORE_SAMPLE") {
        let core = cfg.root.join("build/agc/core");
        let symtab_for_sampler = SymTab::from_listing(
            &std::fs::read_to_string(cfg.root.join("build/agc/Luminary099.log"))
                .context("reading build/agc/Luminary099.log for the core sampler")?,
        )?;
        // Resolve the symbols BEFORE the flight starts, so a bad symbol
        // stops the run here instead of costing a 20-minute descent.
        eagle_runtime::coredump::lr_sample_addrs(&symtab_for_sampler)?;
        eprintln!("scenario: core sampler -> {path}");
        tokio::spawn(async move {
            if let Err(e) = eagle_runtime::coredump::run_lr_sampler(
                core,
                PathBuf::from(path),
                symtab_for_sampler,
            )
            .await
            {
                eprintln!("core sampler stopped: {e:#}");
            }
        });
    }

    eprintln!("scenario: closed loop starting ({})", sc.name);
    let result = run_headless(HeadlessCfg {
        session: cfg.session,
        scenario: sc,
        symtab,
        manifest,
        telem_tx: cfg.state_tx,
        latest: Some(cfg.latest),
        trace_out: cfg.trace_out,
        client_rx: Some(cfg.client_rx),
        client_rod_rx: Some(cfg.client_rod_rx),
    })
    .await?;

    eprintln!(
        "scenario: done — MM {:?}, touchdown {:?}, descent {:?} s, drift {:.0} ms",
        result.mm_sequence,
        touchdown_class(&result),
        result.descent_s,
        result.drift_ms
    );
    // Same diagnostics block the acceptance test prints, so an interactive
    // flight (`make descent-full`) records the run WITHOUT having to
    // re-derive the numbers from the telemetry dump afterwards. The Wave 1
    // re-flight had to hand-compute `agc_rate` out of the EAGLE_TELEM_OUT
    // JSONL for exactly this reason
    // (docs/superpowers/notes/2026-07-25-wave1-reflight.md).
    if let Some(td) = result.sim.touchdown {
        eprintln!(
            "[accept] class {:?} v_vert {:.2} m/s v_horiz {:.2} m/s tilt {:.1} deg \
             miss {:.1} m",
            td.class, td.v_vert_ms, td.v_horiz_ms, td.tilt_deg, td.miss_m
        );
    }
    eprintln!(
        "[accept] alarm episodes {:?}; PROG lamp frames after ignition {} \
         pre-contact, {} post-contact",
        result.alarms, result.prog_lamp_frames, result.prog_lamp_frames_post_contact
    );
    // `agc_rate` — the AGC clock rate the acceptance gate asserts on —
    // alongside `sim pacing lost`, which is what separates a slow AGC from
    // our own scheduling overrun (both look identical in `drift_ms`).
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
    Ok(())
}
