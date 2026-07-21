use anyhow::{Context, Result};
use eagle_agc_protocol::{Packet, StreamDecoder};
use std::path::PathBuf;
use std::process::Stdio;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;
use tokio::process::{Child, Command};
use tokio::sync::mpsc;

pub struct AgcConfig {
    pub yaagc_bin: PathBuf,
    pub core_bin: PathBuf,
    pub port: u16,
}

pub struct AgcSession {
    child: Child,
    events_rx: mpsc::Receiver<Packet>,
    cmd_tx: mpsc::UnboundedSender<Packet>,
}

impl AgcSession {
    pub async fn start(cfg: AgcConfig) -> Result<Self> {
        let child = Command::new(&cfg.yaagc_bin)
            .arg(format!("--core={}", cfg.core_bin.display()))
            .arg(format!("--port={}", cfg.port))
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .kill_on_drop(true)
            .spawn()
            .with_context(|| format!("spawning {:?}", cfg.yaagc_bin))?;

        let mut stream = None;
        for _ in 0..50 {
            match TcpStream::connect(("127.0.0.1", cfg.port)).await {
                Ok(s) => { stream = Some(s); break; }
                Err(_) => tokio::time::sleep(std::time::Duration::from_millis(100)).await,
            }
        }
        let stream = stream.context("could not connect to yaAGC")?;
        let (mut rd, mut wr) = stream.into_split();

        let (events_tx, events_rx) = mpsc::channel::<Packet>(1024);
        let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<Packet>();

        tokio::spawn(async move {
            let mut dec = StreamDecoder::new();
            let mut buf = [0u8; 4096];
            loop {
                match rd.read(&mut buf).await {
                    Ok(0) | Err(_) => break,
                    Ok(n) => {
                        for p in dec.push(&buf[..n]) {
                            if events_tx.send(p).await.is_err() { return; }
                        }
                    }
                }
            }
        });
        tokio::spawn(async move {
            while let Some(p) = cmd_rx.recv().await {
                if wr.write_all(&p.encode()).await.is_err() { break; }
            }
        });

        Ok(Self { child, events_rx, cmd_tx })
    }

    pub fn events(&mut self) -> &mut mpsc::Receiver<Packet> { &mut self.events_rx }

    pub fn send(&self, p: Packet) -> Result<()> {
        self.cmd_tx.send(p).map_err(|_| anyhow::anyhow!("agc writer gone"))
    }

    pub fn shutdown(mut self) {
        let _ = self.child.start_kill();
    }
}
