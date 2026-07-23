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
//!   hover on|closed|off
//!                   v1 fixed PIPA / Spike-B THRUST loop / stop
//!   att-hold        ch31 := CH31_ATT_HOLD (GUILDENSTERN → P66)
//!   rod +|-         one slow/faster-descent ROD click
//!   truth           print the current Spike-B 1-D truth
//!   auto            run through ENGINE ON, ATT-HOLD, and MM66
//!   quit
use anyhow::{Context, Result};
use clap::Parser;
use eagle_agc_protocol::agc_io::{decode_output, rod_click, AgcOutput, ThrustPulse};
use eagle_agc_protocol::dsky::DskyState;
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::padload::{generate_state, PadloadManifest, StateCfg, SymTab};
use eagle_runtime::runner::{
    self, DescentInit, HoverTruth, SyntheticHover, FLAGWRD3_ECADR, FLAGWRD8_ECADR,
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

fn spike_b_initial_truth() -> HoverTruth {
    HoverTruth {
        alt_m: 500.0,
        vz_ms: 0.0,
        mass_kg: 15_195.0,
        cmd_pulses: 0,
        thrust_n: 0.0,
        engine_on: false,
    }
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
    runner::apply_padload(script, &words, verify_every, runner::ALWAYS_VERIFY_ECADRS).await?;
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
    // Arm the THRUST responder now, not after ENGINE ON: P63's FLATOUT
    // command (the initial +4096 POUT burst) occurs before ignition.
    let closed = SyntheticHover::spawn_closed_loop(
        init.agc_tx.clone(),
        init.packets.resubscribe(),
        spike_b_initial_truth(),
    );
    runner::init_discretes(&init.agc_tx).await?;

    eprintln!("[auto] V48 DAP init");
    runner::dap_init(script, 33500, 0).await?;

    eprintln!("[auto] clock read + state generation");
    let epoch_cs = runner::read_clock_cs(script).await?;
    eprintln!("[auto] AGC clock = {epoch_cs} cs");
    let state = PadloadManifest {
        word: generate_state(&StateCfg {
            epoch_now_cs: epoch_cs,
            // Covers the remaining ISS wait, both pad-loads, and more than
            // two minutes of P63 setup while keeping live iterations bounded.
            burn_lead_cs: 30_000.0,
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

    if let Some(v1) = hover.take() {
        v1.stop();
    }
    let mut truth = closed.truth().context("closed-loop truth watch")?;
    tokio::spawn(async move {
        let mut last = tokio::time::Instant::now() - Duration::from_secs(1);
        while truth.changed().await.is_ok() {
            if last.elapsed() >= Duration::from_secs(1) {
                let s = *truth.borrow();
                eprintln!(
                    "[{}][truth] alt={:.2}m vz={:+.3}m/s mass={:.1}kg cmd={} thrust={:.0}N engine={}",
                    ts(),
                    s.alt_m,
                    s.vz_ms,
                    s.mass_kg,
                    s.cmd_pulses,
                    s.thrust_n,
                    s.engine_on
                );
                last = tokio::time::Instant::now();
            }
        }
    });
    *hover = Some(closed);

    eprintln!("[auto] ENGINE ON +2s: ATT HOLD");
    tokio::time::sleep(Duration::from_secs(2)).await;
    runner::att_hold(&init.agc_tx).await?;
    // In this rope, ATT HOLD alone leaves P63 running when RODCOUNT is zero
    // (`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:203-217`). A ROD click is the
    // event that takes STARTP66; STARTP66 then seeds VDGVERT from HDOTDISP.
    let (press, release) = rod_click(false);
    init.agc_tx
        .send(press)
        .map_err(|_| anyhow::anyhow!("agc tx closed"))?;
    tokio::time::sleep(Duration::from_millis(100)).await;
    init.agc_tx
        .send(release)
        .map_err(|_| anyhow::anyhow!("agc tx closed"))?;
    init.script
        .wait_prog("66")
        .await
        .context("GUILDENSTERN did not reach MM66")?;
    eprintln!("[auto] *** MM66 ***; use `rod -` / `rod +` to calibrate");
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
        let mut last_line = String::new();
        while dsky_watch.changed().await.is_ok() {
            // One DSKY word is assembled over several relay writes. Let the
            // burst settle and print the latest coherent snapshot instead of
            // tens of transient half-register frames per key.
            tokio::time::sleep(Duration::from_millis(500)).await;
            let line = dsky_line(&dsky_watch.borrow());
            if line != last_line {
                eprintln!("[{}][dsky] {line}", ts());
                last_line = line;
            }
        }
    });
    // Printer: decoded non-Downlink, non-DSKY output. Individual THRUST
    // pulses are intentionally suppressed; the 1-Hz truth line reports the
    // accumulated command without flooding stdout at up to 3200 pulses/s.
    let mut pkt_watch = pkt_rx;
    tokio::spawn(async move {
        let mut jets5 = None;
        let mut jets6 = None;
        let mut engine = None;
        let mut trim = None;
        let mut thrust_drive = None;
        let mut thrust_pout = 0u32;
        let mut thrust_mout = 0u32;
        let mut thrust_position = 0i64;
        loop {
            match pkt_watch.recv().await {
                Ok(p) => {
                    if matches!(p.channel, 0o10 | 0o11 | 0o163) && p.channel != 0o11 {
                        continue; // DSKY relay traffic: covered by [dsky]
                    }
                    match decode_output(&p) {
                        AgcOutput::Downlink => {}
                        AgcOutput::ThrustPulse(ThrustPulse::Pout) => {
                            thrust_pout += 1;
                            thrust_position =
                                (thrust_position + 1).min(runner::THRUST_CMD_MAX_PULSES);
                        }
                        AgcOutput::ThrustPulse(ThrustPulse::Mout) => {
                            thrust_mout += 1;
                            thrust_position = (thrust_position - 1).max(0);
                        }
                        AgcOutput::ThrustPulse(ThrustPulse::Zout) => {
                            if thrust_pout != 0 || thrust_mout != 0 {
                                eprintln!(
                                    "[{}][thrust] burst POUT={} MOUT={} delta={:+} position={}",
                                    ts(),
                                    thrust_pout,
                                    thrust_mout,
                                    i64::from(thrust_pout) - i64::from(thrust_mout),
                                    thrust_position
                                );
                            }
                            thrust_pout = 0;
                            thrust_mout = 0;
                        }
                        AgcOutput::Jets5 { mask } if jets5 == Some(mask) => {}
                        AgcOutput::Jets5 { mask } => {
                            jets5 = Some(mask);
                            eprintln!("[{}][agc] Jets5 {{ mask: {mask:#010b} }}", ts());
                        }
                        AgcOutput::Jets6 { mask } if jets6 == Some(mask) => {}
                        AgcOutput::Jets6 { mask } => {
                            jets6 = Some(mask);
                            eprintln!("[{}][agc] Jets6 {{ mask: {mask:#010b} }}", ts());
                        }
                        AgcOutput::Engine { on, off } if engine == Some((on, off)) => {}
                        AgcOutput::Engine { on, off } => {
                            engine = Some((on, off));
                            eprintln!("[{}][agc] Engine {{ on: {on}, off: {off} }}", ts());
                        }
                        AgcOutput::Trim {
                            minus_pitch,
                            plus_pitch,
                            minus_roll,
                            plus_roll,
                        } if trim == Some((minus_pitch, plus_pitch, minus_roll, plus_roll)) => {}
                        AgcOutput::Trim {
                            minus_pitch,
                            plus_pitch,
                            minus_roll,
                            plus_roll,
                        } => {
                            trim = Some((minus_pitch, plus_pitch, minus_roll, plus_roll));
                            eprintln!(
                                "[{}][agc] Trim {{ -P:{minus_pitch} +P:{plus_pitch} -R:{minus_roll} +R:{plus_roll} }}",
                                ts()
                            );
                        }
                        AgcOutput::ThrustDrive(active) if thrust_drive == Some(active) => {}
                        AgcOutput::ThrustDrive(active) => {
                            thrust_drive = Some(active);
                            eprintln!("[{}][agc] ThrustDrive({active})", ts());
                        }
                        AgcOutput::Other(p)
                            if matches!(
                                p.channel,
                                0o10 | 0o12 | 0o13 | 0o30 | 0o31 | 0o32 | 0o33 | 0o163
                            ) => {}
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
                    Some("closed") => {
                        if let Some(h) = hover.take() {
                            h.stop();
                        }
                        hover = Some(SyntheticHover::spawn_closed_loop(
                            init.agc_tx.clone(),
                            init.packets.resubscribe(),
                            HoverTruth {
                                engine_on: true,
                                ..spike_b_initial_truth()
                            },
                        ));
                        eprintln!("[probe] Spike-B closed-loop feeder on");
                    }
                    Some("off") => {
                        if let Some(h) = hover.take() {
                            h.stop();
                        }
                        eprintln!("[probe] hover feeder off");
                    }
                    _ => eprintln!("usage: hover on|closed|off"),
                }
                Ok(())
            }
            "att-hold" => runner::att_hold(&init.agc_tx).await,
            "rod" => match arg1 {
                Some(direction @ ("+" | "-")) => {
                    let (press, release) = rod_click(direction == "+");
                    init.agc_tx
                        .send(press)
                        .map_err(|_| anyhow::anyhow!("agc tx closed"))?;
                    tokio::time::sleep(Duration::from_millis(100)).await;
                    init.agc_tx
                        .send(release)
                        .map_err(|_| anyhow::anyhow!("agc tx closed"))
                }
                _ => {
                    eprintln!("usage: rod +|-");
                    Ok(())
                }
            },
            "truth" => {
                match hover.as_ref().and_then(SyntheticHover::truth) {
                    Some(truth) => eprintln!("[probe] truth: {:?}", *truth.borrow()),
                    None => eprintln!("[probe] closed-loop hover is not running"),
                }
                Ok(())
            }
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
