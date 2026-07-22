use clap::Parser;
use eagle_agc_protocol::dsky::DskyState;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::server::{router, to_msg, AppState};
use eagle_runtime::trace::TraceWriter;
use std::path::PathBuf;
use tokio::sync::{broadcast, mpsc};

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
    let mut trace = TraceWriter::open(args.trace_out)?;

    let app = AppState { state_rx: state_tx.clone(), agc_tx, latest: latest.clone() };
    let listener = tokio::net::TcpListener::bind(("127.0.0.1", args.ws_port)).await?;
    tokio::spawn(async move {
        axum::serve(listener, router(app)).await.unwrap();
    });
    eprintln!("eagle-runtime: ws://127.0.0.1:{}/ws", args.ws_port);

    let mut dsky = DskyState::default();
    loop {
        tokio::select! {
            Some(pkt) = session.events().recv() => {
                trace.log("out", &pkt);
                if dsky.apply(&pkt) {
                    let json = serde_json::to_string(&to_msg(&dsky))?;
                    *latest.lock().unwrap() = json.clone();
                    let _ = state_tx.send(json);
                }
            }
            Some(pkt) = agc_rx.recv() => {
                trace.log("in", &pkt);
                session.send(pkt)?;
            }
            else => break,
        }
    }
    Ok(())
}
