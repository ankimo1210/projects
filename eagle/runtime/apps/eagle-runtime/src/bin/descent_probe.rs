//! Spike A iteration aid: boots the live AGC, prints every decoded
//! non-Downlink `AgcOutput` and every DSKY change, and takes choreography
//! commands on stdin. Iterate here; freeze what works into
//! `tests/live_spike_p63.rs`.
//!
//! ```text
//! cargo run -p eagle-runtime --bin descent_probe -- --port 19899
//! ```
//!
//! Commands:
//!   keys <SEQ>      raw DSKY keys (V N E C K R + - digits)
//!   pro             PRO/STBY press-release
//!   alarm           V05N09E, print FAILREG codes
//!   clock           read TIME2:TIME1, print cs
//!   disc            init_discretes (ch30-33 + ISS turn-on request)
//!   iss             wait for ch12 bit15, then drop the ISS request
//!   dap [lm] [csm]  V48 DAP init (defaults 33500 / 0 lbs)
//!   pad             load static manifest scenarios/p66-padload.toml
//!   state [lead_s]  generate_state from live clock (default lead 240 s)
//!                   and load it
//!   flags           set REFSMFLG + FLAGWRD8 moon bits
//!   read <octal>    V01N01 read of an ECADR
//!   n43             key V06N43E (lat/long/alt sanity display)
//!   p63             enter_p63 responder (V37E63E ... V99 PRO)
//!   engine [secs]   wait for ENGINE ON on the packet stream
//!   hover on|off    synthetic hover PIPA feeder
//!   att-hold        ch31 := CH31_ATT_HOLD (GUILDENSTERN → P66)
//!   auto            run the whole spike choreography end to end
//!   quit
use anyhow::{Context, Result};
use clap::Parser;
use eagle_agc_protocol::agc_io::{decode_output, AgcOutput};
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::Packet;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::padload::{generate_state, PadloadManifest, StateCfg, SymTab};
use eagle_runtime::runner::{
    self, DescentInit, SyntheticHover, CH31_ATT_HOLD, FLAGWRD3_ECADR, FLAGWRD8_ECADR,
    FLAGWRD8_MOON_BITS, REFSMBIT,
};
use eagle_runtime::script::{pump, DskyScript};
use std::path::PathBuf;
use std::time::Duration;

#[derive(Parser)]
struct Args {
    #[arg(long, default_value_t = 19899)]
    port: u16,
    /// Repo root (defaults to ../../.. from the crate, i.e. eagle/).
    #[arg(long)]
    root: Option<PathBuf>,
    #[arg(long, default_value_t = 30)]
    key_delay_ms: u64,
}

static START: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
fn ts() -> String {
    let t0 = *START.get_or_init(std::time::Instant::now);
    format!("{:8.2}", t0.elapsed().as_secs_f64())
}

fn dsky_line(d: &DskyState) -> String {
    let reg = |r: &eagle_agc_protocol::dsky::RegisterDisplay| -> String {
        std::iter::once(r.sign).chain(r.digits).collect()
    };
    let lamps = [
        (d.lamps.comp_acty, "ACTY"),
        (d.lamps.uplink_acty, "UPLK"),
        (d.lamps.no_att, "NOATT"),
        (d.lamps.gimbal_lock, "GLOCK"),
        (d.lamps.prog_alarm, "PROG!"),
        (d.lamps.tracker, "TRKR"),
        (d.lamps.alt, "ALT"),
        (d.lamps.vel, "VEL"),
        (d.lamps.no_dap, "NODAP"),
        (d.restart, "RESTART"),
        (d.standby, "STBY"),
        (d.opr_err, "OPRERR"),
        (d.key_rel, "KEYREL"),
        (d.temp, "TEMP"),
    ]
    .iter()
    .filter(|(on, _)| *on)
    .map(|(_, n)| *n)
    .collect::<Vec<_>>()
    .join(",");
    format!(
        "P{}{} V{}{}{} N{}{} R1[{}] R2[{}] R3[{}] {}",
        d.prog[0],
        d.prog[1],
        d.verb[0],
        d.verb[1],
        if d.verb_noun_flash { "*" } else { " " },
        d.noun[0],
        d.noun[1],
        reg(&d.r1),
        reg(&d.r2),
        reg(&d.r3),
        lamps
    )
}

async fn load_manifest(
    script: &mut DskyScript,
    manifest: &PadloadManifest,
    symtab: &SymTab,
    verify_every: usize,
) -> Result<()> {
    let words = manifest.resolve(symtab)?;
    let n = words.iter().filter(|w| w.word != 0).count();
    eprintln!("[probe] loading {n} non-zero words ({} total)", words.len());
    let t0 = std::time::Instant::now();
    runner::apply_padload(script, &words, verify_every).await?;
    eprintln!(
        "[probe] pad-load done in {:.1}s",
        t0.elapsed().as_secs_f64()
    );
    Ok(())
}

async fn run_auto(
    init: &mut DescentInit,
    symtab: &SymTab,
    manifest: &PadloadManifest,
    hover: &mut Option<SyntheticHover>,
) -> Result<()> {
    let script = &mut init.script;
    eprintln!("[auto] settle + fresh-start dance");
    tokio::time::sleep(Duration::from_secs(2)).await;
    script.keys("R").await?; // clear the boot RESTART lamp
    script.keys("V37E00E").await?;
    script.wait_prog("00").await.context("P00 after V37E00E")?;

    eprintln!("[auto] hover feeder + discretes (ISS turn-on request)");
    *hover = Some(SyntheticHover::spawn(init.agc_tx.clone()));
    runner::init_discretes(&init.agc_tx).await?;

    eprintln!("[auto] V48 DAP init");
    runner::dap_init(script, 33500, 0).await?;

    eprintln!("[auto] clock read + state generation");
    let epoch_cs = runner::read_clock_cs(script).await?;
    eprintln!("[auto] AGC clock = {epoch_cs} cs");
    let state = PadloadManifest {
        word: generate_state(&StateCfg {
            epoch_now_cs: epoch_cs,
            burn_lead_cs: 36_000.0, // ISS-wait remainder + pad-load + margin
            ..StateCfg::default()
        }),
    };

    // ISS wait BEFORE the pad-load: the packet receiver must drain the
    // ch12-bit15 event before the broadcast buffer wraps (iter-2 lesson:
    // the event fires at boot+90 s while a pad-load would still be keying).
    eprintln!("[auto] waiting for ISS turn-on delay complete");
    let waited =
        runner::wait_iss_turnon(&mut init.packets, &init.agc_tx, Duration::from_secs(150)).await?;
    eprintln!("[auto] ISS delay complete after {waited:?}");
    let _ = init
        .script
        .wait(Duration::from_secs(30), |d| !d.lamps.no_att)
        .await
        .map(|_| eprintln!("[auto] NO ATT out"));

    let script = &mut init.script;
    eprintln!("[auto] static pad-load");
    load_manifest(script, manifest, symtab, 8).await?;
    eprintln!("[auto] state pad-load");
    load_manifest(script, &state, symtab, 8).await?;

    eprintln!("[auto] REFSMFLG + FLAGWRD8 moon bits");
    runner::set_flag_bits(&mut init.script, FLAGWRD8_ECADR, FLAGWRD8_MOON_BITS).await?;
    runner::set_flag_bits(&mut init.script, FLAGWRD3_ECADR, REFSMBIT).await?;

    eprintln!("[auto] V37E63E + responder");
    runner::enter_p63(&mut init.script).await?;

    eprintln!("[auto] awaiting ENGINE ON");
    let rate = runner::wait_engine_on(&mut init.packets, Duration::from_secs(180)).await?;
    eprintln!("[auto] *** ENGINE ON *** (downlink {rate:.1} pkt/s)");
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();
    let root = args
        .root
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../.."));

    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(root.join("build/agc/Luminary099.log"))
            .context("reading build/agc/Luminary099.log (run `make agc`)")?,
    )?;
    let manifest_path = root.join("scenarios/p66-padload.toml");
    let manifest = PadloadManifest::load(&manifest_path)?;

    let session = AgcSession::start(AgcConfig {
        yaagc_bin: root.join("build/agc/yaAGC"),
        core_bin: root.join("build/agc/Luminary099.bin"),
        port: args.port,
    })
    .await?;
    let (dsky_rx, cmd_tx, pkt_rx, _pump_handle) = pump(session);
    let mut script = DskyScript::new(cmd_tx.clone(), dsky_rx.clone());
    script.set_key_delay(Duration::from_millis(args.key_delay_ms));
    let mut init = DescentInit {
        script,
        packets: pkt_rx.resubscribe(),
        agc_tx: cmd_tx,
    };

    // Printer: every DSKY change.
    let mut dsky_watch = dsky_rx.clone();
    tokio::spawn(async move {
        while dsky_watch.changed().await.is_ok() {
            let line = dsky_line(&dsky_watch.borrow());
            eprintln!("[{}][dsky] {line}", ts());
        }
    });
    // Printer: every decoded non-Downlink, non-DSKY output.
    let mut pkt_watch = pkt_rx;
    tokio::spawn(async move {
        loop {
            match pkt_watch.recv().await {
                Ok(p) => {
                    if matches!(p.channel, 0o10 | 0o11 | 0o163) && p.channel != 0o11 {
                        continue; // DSKY relay traffic: covered by [dsky]
                    }
                    match decode_output(&p) {
                        AgcOutput::Downlink => {}
                        AgcOutput::Other(p) if matches!(p.channel, 0o10 | 0o163 | 0o13 | 0o12) => {}
                        out => eprintln!("[{}][agc] {out:?}", ts()),
                    }
                }
                Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => {
                    eprintln!("[agc] (lagged, dropped {n})");
                }
                Err(_) => break,
            }
        }
    });

    let mut hover: Option<SyntheticHover> = None;
    // Plain blocking stdin on its own thread: tokio::io::stdin() trips
    // over non-blocking pipe/FIFO stdin in sandboxed environments (EAGAIN).
    let (line_tx, mut line_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    std::thread::spawn(move || {
        use std::io::BufRead;
        for line in std::io::stdin().lock().lines() {
            match line {
                Ok(l) => {
                    if line_tx.send(l).is_err() {
                        break;
                    }
                }
                Err(_) => std::thread::sleep(Duration::from_millis(50)),
            }
        }
    });
    eprintln!(
        "[probe] ready (port {}); `auto` runs the full choreography",
        args.port
    );
    while let Some(line) = line_rx.recv().await {
        let mut it = line.split_whitespace();
        let Some(cmd) = it.next() else { continue };
        let arg1 = it.next();
        let arg2 = it.next();
        let r: Result<()> = match cmd {
            "quit" | "q" => break,
            "keys" => match arg1 {
                Some(seq) => init.script.keys(seq).await,
                None => {
                    eprintln!("usage: keys <SEQ>");
                    Ok(())
                }
            },
            "pro" => init.script.pro().await,
            "alarm" => match init.script.alarm_codes().await {
                Ok(c) => {
                    eprintln!("[probe] FAILREG: {:05o} {:05o} {:05o}", c[0], c[1], c[2]);
                    Ok(())
                }
                Err(e) => Err(e),
            },
            "clock" => match runner::read_clock_cs(&mut init.script).await {
                Ok(cs) => {
                    eprintln!("[probe] clock = {cs} cs ({:.2} s)", cs / 100.0);
                    Ok(())
                }
                Err(e) => Err(e),
            },
            "disc" => runner::init_discretes(&init.agc_tx).await,
            "iss" => {
                runner::wait_iss_turnon(&mut init.packets, &init.agc_tx, Duration::from_secs(150))
                    .await
                    .map(|d| eprintln!("[probe] ISS delay complete after {d:?}"))
            }
            "dap" => {
                let lm = arg1.and_then(|s| s.parse().ok()).unwrap_or(33500);
                let csm = arg2.and_then(|s| s.parse().ok()).unwrap_or(0);
                runner::dap_init(&mut init.script, lm, csm).await
            }
            "pad" => load_manifest(&mut init.script, &manifest, &symtab, 8).await,
            "state" => {
                let lead_s: f64 = arg1.and_then(|s| s.parse().ok()).unwrap_or(240.0);
                match runner::read_clock_cs(&mut init.script).await {
                    Ok(epoch_cs) => {
                        let m = PadloadManifest {
                            word: generate_state(&StateCfg {
                                epoch_now_cs: epoch_cs,
                                burn_lead_cs: lead_s * 100.0,
                                ..StateCfg::default()
                            }),
                        };
                        load_manifest(&mut init.script, &m, &symtab, 8).await
                    }
                    Err(e) => Err(e),
                }
            }
            "flags" => {
                match runner::set_flag_bits(&mut init.script, FLAGWRD8_ECADR, FLAGWRD8_MOON_BITS)
                    .await
                {
                    Ok(()) => {
                        runner::set_flag_bits(&mut init.script, FLAGWRD3_ECADR, REFSMBIT).await
                    }
                    Err(e) => Err(e),
                }
            }
            "read" => match arg1.and_then(|s| u16::from_str_radix(s, 8).ok()) {
                Some(ecadr) => match init.script.read_erasable(ecadr).await {
                    Ok(w) => {
                        eprintln!("[probe] @{ecadr:05o} = {w:05o}");
                        Ok(())
                    }
                    Err(e) => Err(e),
                },
                None => {
                    eprintln!("usage: read <octal ecadr>");
                    Ok(())
                }
            },
            "n43" => init.script.keys("V06N43E").await,
            "p63" => runner::enter_p63(&mut init.script).await,
            "engine" => {
                let secs: u64 = arg1.and_then(|s| s.parse().ok()).unwrap_or(180);
                runner::wait_engine_on(&mut init.packets, Duration::from_secs(secs))
                    .await
                    .map(|rate| eprintln!("[probe] *** ENGINE ON *** downlink {rate:.1}/s"))
            }
            "hover" => {
                match arg1 {
                    Some("on") => {
                        hover = Some(SyntheticHover::spawn(init.agc_tx.clone()));
                        eprintln!("[probe] hover feeder on");
                    }
                    Some("off") => {
                        if let Some(h) = hover.take() {
                            h.stop();
                        }
                        eprintln!("[probe] hover feeder off");
                    }
                    _ => eprintln!("usage: hover on|off"),
                }
                Ok(())
            }
            "att-hold" => init
                .agc_tx
                .send(Packet::io(0o31, CH31_ATT_HOLD)?)
                .map_err(|_| anyhow::anyhow!("agc tx closed")),
            "auto" => run_auto(&mut init, &symtab, &manifest, &mut hover).await,
            other => {
                eprintln!("[probe] unknown command {other:?}");
                Ok(())
            }
        };
        if let Err(e) = r {
            eprintln!("[probe] ERROR: {e:#}");
        }
    }
    Ok(())
}
