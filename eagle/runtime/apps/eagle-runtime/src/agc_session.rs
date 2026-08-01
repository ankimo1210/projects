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
        // Canonicalize before spawning so relative paths keep resolving from
        // this process's cwd even though the child's cwd is pinned below to
        // core_bin's directory (build/agc/, already git-ignored) — that's
        // where yaAGC writes its "core" erasable-memory checkpoint file, and
        // without this it lands wherever the child happens to inherit its
        // cwd from (e.g. the crate manifest dir under `cargo test`).
        let yaagc_bin = std::fs::canonicalize(&cfg.yaagc_bin)
            .with_context(|| format!("canonicalizing {:?}", cfg.yaagc_bin))?;
        let core_bin = std::fs::canonicalize(&cfg.core_bin)
            .with_context(|| format!("canonicalizing {:?}", cfg.core_bin))?;
        let core_dir = core_bin
            .parent()
            .with_context(|| format!("{core_bin:?} has no parent directory"))?;

        // `EAGLE_DUMP_TIME` shortens yaAGC's erasable-checkpoint interval
        // from the default 10 s (agc_cli.c:188) so a forensic run can
        // capture every 2 s servicer pass instead of one in five.
        //
        // OFF BY DEFAULT, and it must stay that way: the dump is a
        // synchronous ~18 KB write in yaAGC's main loop, and at 1 s it
        // delayed the AGC enough to blow the pad-load read-back
        // (`V01N01 read of 02027 failed 3 times`) — flight 12 died before
        // ignition. Raise it only for a run whose purpose is the dump,
        // and expect the boot choreography to be the thing at risk.
        let dump_time = std::env::var("EAGLE_DUMP_TIME").ok();
        let mut child = Command::new(&yaagc_bin)
            .arg(format!("--core={}", core_bin.display()))
            .arg(format!("--port={}", cfg.port))
            // Cold boot, always: without this yaAGC silently RESUMES
            // erasable (clock, flags, half-loaded pad-loads...) from the
            // periodic "core" checkpoint file in its cwd
            // (agc_simulator.c:88, SimManageCoreDump:235), which leaks
            // state between test runs (spike-A iter 5: the AGC clock grew
            // across separate boots by exactly the cumulative run time,
            // and a stale-state POODOO aborted P00).
            .arg("--no-resume")
            .args(dump_time.iter().map(|d| format!("--dump-time={d}")))
            .current_dir(core_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .kill_on_drop(true)
            .spawn()
            .with_context(|| format!("spawning {:?}", yaagc_bin))?;

        let mut stream = None;
        let mut last_err: Option<std::io::Error> = None;
        for _ in 0..50 {
            if let Some(status) = child.try_wait()? {
                anyhow::bail!("yaAGC exited early with {status} before accepting a connection");
            }
            match TcpStream::connect(("127.0.0.1", cfg.port)).await {
                Ok(s) => {
                    stream = Some(s);
                    break;
                }
                Err(e) => {
                    last_err = Some(e);
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                }
            }
        }
        let stream = stream.with_context(|| {
            format!(
                "could not connect to yaAGC on 127.0.0.1:{} (last error: {last_err:?})",
                cfg.port
            )
        })?;
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
                            if events_tx.send(p).await.is_err() {
                                return;
                            }
                        }
                    }
                }
            }
        });
        tokio::spawn(async move {
            while let Some(p) = cmd_rx.recv().await {
                if wr.write_all(&p.encode()).await.is_err() {
                    break;
                }
            }
        });

        Ok(Self {
            child,
            events_rx,
            cmd_tx,
        })
    }

    pub fn events(&mut self) -> &mut mpsc::Receiver<Packet> {
        &mut self.events_rx
    }

    pub fn send(&self, p: Packet) -> Result<()> {
        self.cmd_tx
            .send(p)
            .map_err(|_| anyhow::anyhow!("agc writer gone"))
    }

    pub fn shutdown(mut self) {
        let _ = self.child.start_kill();
    }
}
