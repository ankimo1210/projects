use clap::Parser;
use eagle_agc_protocol::dsky::DskyState;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::server::{router, to_msg, AppState};
use eagle_runtime::trace::TraceWriter;
use std::path::PathBuf;
use tokio::signal::unix::{signal, SignalKind};
use tokio::sync::{broadcast, mpsc, watch};

mod scenario_mode;

#[derive(Parser)]
struct Args {
    #[arg(long)]
    yaagc: PathBuf,
    #[arg(long)]
    core: PathBuf,
    #[arg(long, default_value_t = 19797)]
    agc_port: u16,
    #[arg(long, default_value_t = 8642)]
    ws_port: u16,
    #[arg(long)]
    trace_out: Option<PathBuf>,
    /// Closed-loop mode: run this scenario (path to a p66-gate-style TOML)
    /// end to end. Without it, behavior is exactly Phase 1 (DSKY only).
    #[arg(long)]
    scenario: Option<PathBuf>,
    /// Repo root for `build/agc/Luminary099.log` symtab (scenario mode).
    #[arg(long, default_value = ".")]
    root: PathBuf,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    let mut session = AgcSession::start(AgcConfig {
        yaagc_bin: args.yaagc,
        core_bin: args.core,
        port: args.agc_port,
    })
    .await?;

    let (state_tx, _) = broadcast::channel::<String>(256);
    let (agc_tx, mut agc_rx) = mpsc::unbounded_channel();
    let latest = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
    let (dsky_tx, dsky_rx) = watch::channel(DskyState::default());
    // Kept alive so `dsky_tx.send` below always has a live receiver (watch
    // send fails with no receivers). Only the Phase-1 DSKY-only loop below
    // uses this channel; scenario mode gets its DSKY watch from `pump`.
    let _keep = dsky_rx;
    let mut trace = TraceWriter::open(args.trace_out.clone())?;

    let (rod_click_tx, rod_click_rx) = mpsc::unbounded_channel::<i32>();
    let app = AppState {
        state_rx: state_tx.clone(),
        agc_tx: agc_tx.clone(),
        latest: latest.clone(),
        rod_click_tx: args.scenario.is_some().then_some(rod_click_tx),
    };
    let listener = tokio::net::TcpListener::bind(("127.0.0.1", args.ws_port)).await?;
    tokio::spawn(async move {
        axum::serve(listener, router(app)).await.unwrap();
    });
    eprintln!("eagle-runtime: ws://127.0.0.1:{}/ws", args.ws_port);

    // Closed-loop mode: hand off to the scenario driver (it owns the socket
    // via `pump`, spawns the sim thread, and runs the choreography).
    if let Some(path) = args.scenario.clone() {
        return scenario_mode::run(scenario_mode::Cfg {
            session,
            scenario: path,
            root: args.root.clone(),
            state_tx: state_tx.clone(),
            latest: latest.clone(),
            trace_out: args.trace_out.clone(),
            client_rx: agc_rx,
            client_rod_rx: rod_click_rx,
        })
        .await;
    }
    // Phase-1 DSKY-only loop below: `agc_rx` wasn't moved (the scenario arm
    // above returned first), and this loop has no client ROD-click source.
    let _ = rod_click_rx;

    let mut sigterm = signal(SignalKind::terminate())?;
    let mut dsky = DskyState::default();
    loop {
        tokio::select! {
            pkt = session.events().recv() => {
                match pkt {
                    Some(pkt) => {
                        trace.log("out", &pkt);
                        if dsky.apply(&pkt) {
                            let _ = dsky_tx.send(dsky);
                            let json = serde_json::to_string(&to_msg(&dsky))?;
                            *latest.lock().unwrap() = json.clone();
                            let _ = state_tx.send(json);
                        }
                    }
                    None => {
                        eprintln!("eagle-runtime: AGC event stream closed (yaAGC died?), shutting down");
                        break;
                    }
                }
            }
            pkt = agc_rx.recv() => {
                match pkt {
                    Some(pkt) => {
                        trace.log("in", &pkt);
                        session.send(pkt)?;
                    }
                    None => {
                        eprintln!("eagle-runtime: AGC command channel closed, shutting down");
                        break;
                    }
                }
            }
            _ = sigterm.recv() => {
                eprintln!("eagle-runtime: SIGTERM received, shutting down");
                break;
            }
            _ = tokio::signal::ctrl_c() => {
                eprintln!("eagle-runtime: SIGINT received, shutting down");
                break;
            }
            else => break,
        }
    }
    session.shutdown();
    Ok(())
}
