use clap::Parser;
use eagle_agc_protocol::dsky::DskyState;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::server::{router, to_msg, AppState};
use eagle_runtime::trace::TraceWriter;
use std::path::PathBuf;
use tokio::signal::unix::{signal, SignalKind};
use tokio::sync::{broadcast, mpsc, watch};

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
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    let mut session = AgcSession::start(AgcConfig {
        yaagc_bin: args.yaagc, core_bin: args.core, port: args.agc_port,
    }).await?;

    let (state_tx, _) = broadcast::channel::<String>(256);
    let (agc_tx, mut agc_rx) = mpsc::unbounded_channel();
    let latest = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
    let (dsky_tx, dsky_rx) = watch::channel(DskyState::default());
    // Kept alive so `dsky_tx.send` below has a live receiver; Task 14 will
    // consume `dsky_rx` (e.g. hand it to a `DskyScript`) instead of this
    // placeholder binding.
    let _keep = dsky_rx;
    let mut trace = TraceWriter::open(args.trace_out)?;

    let app = AppState { state_rx: state_tx.clone(), agc_tx, latest: latest.clone() };
    let listener = tokio::net::TcpListener::bind(("127.0.0.1", args.ws_port)).await?;
    tokio::spawn(async move {
        axum::serve(listener, router(app)).await.unwrap();
    });
    eprintln!("eagle-runtime: ws://127.0.0.1:{}/ws", args.ws_port);

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
