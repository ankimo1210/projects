//! Read the AGC's erasable memory straight out of yaAGC's core dump.
//!
//! yaAGC writes its whole state to a `core` file in its cwd every
//! `-dump-time` seconds (default 10; `agc_cli.c:188`,
//! `agc_simulator.c:224-238`), and `AgcSession` already pins the child's
//! cwd to `build/agc/` so it lands somewhere known. The format is plain
//! text, one octal word per line:
//!
//! ```text
//!   512 lines   I/O channels          (NUM_CHANNELS, agc_engine.h:273)
//!  2048 lines   erasable, 8 banks x 0400 words
//!   ...         CPU state (cycle counter, ExtraCode, ...)
//! ```
//! (`agc_engine_init.c:441-471`.)
//!
//! **This is the instrument of first resort for any question about what
//! the AGC believes.** It gives every erasable word exactly, by symbol,
//! with no frame anchoring, no slot map, no drop handling and no
//! correlation fitting. The 2026-07-31 investigation spent most of a
//! session reverse-engineering the telemetry downlink for state the
//! `core` file had on disk the whole time — see
//! `docs/superpowers/notes/2026-07-31-m1b-rod-loop.md` §9d/§9g. Reach for
//! the downlink only for things the dump cannot give: a *time series*
//! (the dump is periodic and overwrites itself) or a live, in-flight read.
use anyhow::{bail, Context, Result};

/// `NUM_CHANNELS` (`vendor/virtualagc/yaAGC/agc_engine.h:273`).
const NUM_CHANNELS: usize = 512;
/// 8 erasable banks of 0400 words (`agc_engine_init.c:464-466`).
const BANKS: usize = 8;
const BANK_WORDS: usize = 0o400;
pub const ERASABLE_WORDS: usize = BANKS * BANK_WORDS;

/// A parsed yaAGC core dump: the AGC's erasable memory at one instant.
#[derive(Debug, Clone)]
pub struct CoreDump {
    channels: Vec<u16>,
    erasable: Vec<u16>,
}

impl CoreDump {
    pub fn parse(text: &str) -> Result<CoreDump> {
        let mut words = Vec::new();
        for (n, line) in text.lines().enumerate() {
            let t = line.trim();
            if t.is_empty() {
                continue;
            }
            // The CPU-state tail includes a 64-bit cycle counter that does
            // not fit a word; stop cleanly once memory is read.
            if words.len() >= NUM_CHANNELS + ERASABLE_WORDS {
                break;
            }
            let w = u32::from_str_radix(t, 8)
                .with_context(|| format!("core dump line {}: {t:?} is not octal", n + 1))?;
            words.push(w as u16);
        }
        if words.len() < NUM_CHANNELS + ERASABLE_WORDS {
            bail!(
                "core dump truncated: {} words, need {}",
                words.len(),
                NUM_CHANNELS + ERASABLE_WORDS
            );
        }
        let erasable = words.split_off(NUM_CHANNELS);
        Ok(CoreDump {
            channels: words,
            erasable,
        })
    }

    pub fn load(path: &std::path::Path) -> Result<CoreDump> {
        let text =
            std::fs::read_to_string(path).with_context(|| format!("reading core dump {path:?}"))?;
        CoreDump::parse(&text)
    }

    /// One erasable word by ECADR (`bank * 0400 + offset`), as the AGC
    /// stores it: 15 bits, one's complement.
    pub fn word(&self, ecadr: u16) -> Option<u16> {
        self.erasable.get(usize::from(ecadr)).copied()
    }

    pub fn channel(&self, ch: u16) -> Option<u16> {
        self.channels.get(usize::from(ch)).copied()
    }

    /// A single-precision word as a signed integer.
    pub fn sp(&self, ecadr: u16) -> Option<i32> {
        self.word(ecadr).map(i15)
    }

    /// A double-precision word: the high half carries the top 14 bits.
    /// The halves may legally disagree in sign.
    pub fn dp(&self, ecadr: u16) -> Option<i64> {
        let hi = i64::from(self.sp(ecadr)?);
        let lo = i64::from(self.sp(ecadr.checked_add(1)?)?);
        Some(hi * 16384 + lo)
    }

    /// A DP word as a physical quantity at b-scale `b`.
    pub fn dp_at(&self, ecadr: u16, b: i32) -> Option<f64> {
        self.dp(ecadr).map(|v| v as f64 * 2f64.powi(b - 28))
    }

    /// Three consecutive DP words (an AGC vector) at b-scale `b`.
    pub fn vec_at(&self, ecadr: u16, b: i32) -> Option<[f64; 3]> {
        Some([
            self.dp_at(ecadr, b)?,
            self.dp_at(ecadr.checked_add(2)?, b)?,
            self.dp_at(ecadr.checked_add(4)?, b)?,
        ])
    }
}

/// AGC 15-bit one's complement to signed.
fn i15(w: u16) -> i32 {
    let w = w & 0o77777;
    if w < 0o40000 {
        i32::from(w)
    } else {
        -i32::from(w ^ 0o77777)
    }
}

/// HMEAS is stored in raw landing-radar counts, one count = 1.079 ft
/// ("LRH DATA 1.079 FT/BIT", `SERVICER.agc:1550`; `HSCAL` = .3288792
/// = 1.079 ft in metres, `CONTROLLED_CONSTANTS.agc:168`). SCALADJ has
/// already multiplied a high-scale reading by 5 before it lands here, so
/// this single factor is correct on both range scales.
pub const HMEAS_M_PER_COUNT: f64 = 1.079 * 0.3048;

/// The R12 landing-radar working set, sampled as one row of a time series.
///
/// This is the measurement the 2026-08-03 investigation prescribed: the
/// rope's own measured altitude (`HMEAS`), its computed altitude
/// (`HCALC`), their difference as R12 forms it (`DELTAH`), the navigation
/// state the update moves (`RGU`/`VGU`), and the flags and counters that
/// decide whether the update happens at all. Every field is read by
/// symbol out of the core dump — no frame anchoring, no slot map. See the
/// module doc for why that matters, and
/// `docs/superpowers/notes/2026-08-03-v57-lr-incorporation.md` §8 for what
/// this instrument was built to decide.
pub const LR_SAMPLE_HEADER: &str = "time2_s,piptime_s,hmeas_m,hcalc_m,deltah_m,\
rgu_x_m,rgu_y_m,rgu_z_m,vgu_x_ms,vgu_y_ms,vgu_z_ms,rnrad,flgwrd11,radmodes,ch33,\
lrlctr,lrrctr,lrsctr,lrmctr,failreg1,failreg2,failreg3";

/// Symbols the sampler requires. Missing any of them is a hard error at
/// start-up rather than a silently empty column mid-flight — the failure
/// mode `EAGLE_TELEM_OUT` used to have (§ "swallowed a bad path").
pub const LR_SAMPLE_SYMBOLS: &[&str] = &[
    "PIPTIME", "HMEAS", "HCALC", "DELTAH", "RGU", "VGU", "FLGWRD11", "RADMODES", "LRLCTR",
    "LRRCTR", "LRSCTR", "LRMCTR", "FAILREG",
];

/// Counters the symbol table cannot supply. Both are hardware counters
/// rather than assigned erasables, so their listing lines carry no
/// address column and `SymTab` — correctly — does not resolve them
/// (`agc_state` prints TIME2 as "not found" for exactly this reason).
///
/// `TIME2` is the DP pair TIME2/TIME1 at 0o24, the same address and
/// convention `runner::read_clock_cs` uses: centiseconds at b=28.
pub const TIME2_ECADR: u16 = 0o24;
/// `RNRAD`, the radar counter (`ERASABLE_ASSIGNMENTS.agc:141`) — the word
/// the LR responder shifts its count into.
pub const RNRAD_ECADR: u16 = 0o46;

/// Resolve every sampler symbol, or say exactly which one is missing.
pub fn lr_sample_addrs(
    symtab: &crate::padload::SymTab,
) -> Result<std::collections::HashMap<&'static str, u16>> {
    let mut out = std::collections::HashMap::new();
    for sym in LR_SAMPLE_SYMBOLS {
        let ecadr = symtab
            .ecadr(sym)
            .with_context(|| format!("symbol {sym} not in the Luminary listing"))?;
        out.insert(*sym, ecadr);
    }
    out.insert("TIME2", TIME2_ECADR);
    out.insert("RNRAD", RNRAD_ECADR);
    Ok(out)
}

/// One CSV row of the R12 working set, or `None` if the dump is unusable.
///
/// b-scales, all cited where this project established them: `HCALC` and
/// `DELTAH` b=24 m (`SERVICER.agc:1147-1154`, "ALTITUDE AT 2(24) M" /
/// "DELTA H AT 2(24) M"), `RGU` b=24 m (`LAND` shares it and the rope
/// differences them), `VGU` b=10 m/cs, clocks b=28 cs.
pub fn lr_sample_row(
    dump: &CoreDump,
    addr: &std::collections::HashMap<&'static str, u16>,
) -> Option<String> {
    let dp24 = |sym: &str| dump.dp_at(*addr.get(sym)?, 24);
    let time2_s = dump.dp_at(*addr.get("TIME2")?, 28)? / 100.0;
    let piptime_s = dump.dp_at(*addr.get("PIPTIME")?, 28)? / 100.0;
    let hmeas_m = dump.dp(*addr.get("HMEAS")?)? as f64 * HMEAS_M_PER_COUNT;
    let hcalc_m = dp24("HCALC")?;
    let deltah_m = dp24("DELTAH")?;
    let rgu = dump.vec_at(*addr.get("RGU")?, 24)?;
    let vgu = dump.vec_at(*addr.get("VGU")?, 10)?.map(|v| v * 100.0);
    let sp = |sym: &str| dump.sp(*addr.get(sym)?);
    let word = |sym: &str| dump.word(*addr.get(sym)?);
    let failreg = *addr.get("FAILREG")?;
    Some(format!(
        "{time2_s:.2},{piptime_s:.2},{hmeas_m:.2},{hcalc_m:.2},{deltah_m:.2},\
{:.2},{:.2},{:.2},{:.4},{:.4},{:.4},{},{:05o},{:05o},{:05o},{},{},{},{},{:05o},{:05o},{:05o}",
        rgu[0],
        rgu[1],
        rgu[2],
        vgu[0],
        vgu[1],
        vgu[2],
        sp("RNRAD")?,
        word("FLGWRD11")?,
        word("RADMODES")?,
        dump.channel(0o33)?,
        sp("LRLCTR")?,
        sp("LRRCTR")?,
        sp("LRSCTR")?,
        sp("LRMCTR")?,
        dump.word(failreg)?,
        dump.word(failreg + 1)?,
        dump.word(failreg + 2)?,
    ))
}

/// Watch yaAGC's periodic core dump and append one `lr_sample_row` per
/// distinct AGC clock value.
///
/// The dump is a synchronous write in yaAGC's main loop, so this reader
/// stays strictly passive: it polls the file's modification time, and a
/// dump caught mid-write simply fails to parse and is skipped. Sampling
/// costs the AGC nothing; only shortening `EAGLE_DUMP_TIME` does, and
/// that is the documented hazard in `agc_session`.
pub async fn run_lr_sampler(
    core_path: std::path::PathBuf,
    out_path: std::path::PathBuf,
    symtab: crate::padload::SymTab,
) -> Result<()> {
    use std::io::Write;
    let addr = lr_sample_addrs(&symtab)?;
    let mut out = std::fs::File::create(&out_path).with_context(|| {
        format!(
            "EAGLE_CORE_SAMPLE={}: cannot create. The runtime's cwd is `runtime/` \
             — pass an absolute path.",
            out_path.display()
        )
    })?;
    writeln!(out, "{LR_SAMPLE_HEADER}").context("writing sampler header")?;
    // yaAGC's dump file survives between runs (`--no-resume` stops the AGC
    // reading it, not yaAGC writing it), so the file on disk when sampling
    // starts belongs to the PREVIOUS flight. Run 34's first row was that
    // stale state — 19.5 km of HMEAS from Run 33's crash, in the middle of
    // an otherwise clean descent. Only dumps written after this moment
    // count.
    let started = std::time::SystemTime::now();
    let mut last_mtime = None;
    let mut last_time2 = String::new();
    loop {
        tokio::time::sleep(std::time::Duration::from_millis(250)).await;
        let Ok(meta) = std::fs::metadata(&core_path) else {
            continue;
        };
        let Ok(mtime) = meta.modified() else { continue };
        if mtime < started {
            continue;
        }
        if last_mtime == Some(mtime) {
            continue;
        }
        last_mtime = Some(mtime);
        // A torn read of a dump being written fails to parse; skip it and
        // catch the next one rather than recording a half-file.
        let Ok(dump) = CoreDump::load(&core_path) else {
            continue;
        };
        let Some(row) = lr_sample_row(&dump, &addr) else {
            continue;
        };
        let stamp = row.split(',').next().unwrap_or_default().to_string();
        if stamp == last_time2 {
            continue;
        }
        last_time2 = stamp;
        let _ = writeln!(out, "{row}");
        let _ = out.flush();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn synth(set: &[(usize, u16)]) -> String {
        let mut w = vec![0u16; NUM_CHANNELS + ERASABLE_WORDS];
        for &(i, v) in set {
            w[i] = v;
        }
        let mut s: String = w.iter().map(|x| format!("{x:06o}\n")).collect();
        // The real file has a CPU-state tail, including a 64-bit counter
        // that is not a word — parsing must not choke on it.
        s.push_str("1234567890123456\n0\n1\n");
        s
    }

    #[test]
    fn reads_a_word_by_ecadr() {
        // ECADR 0o2540 is bank 5, offset 0o140 -> erasable index
        // 5 * 0o400 + 0o140 = 0o2540 = 1376.
        let text = synth(&[(NUM_CHANNELS + 0o2540, 0o2260)]);
        let c = CoreDump::parse(&text).unwrap();
        assert_eq!(c.word(0o2540), Some(0o2260));
        assert_eq!(c.word(0o2541), Some(0));
    }

    #[test]
    fn decodes_taurod_at_its_measured_b_scale() {
        // The real flown value: 0o2260,0 is 150 cs at b=11 = 1.5 s, which
        // is what the 2026-07-31 step test measured the scale to be.
        let text = synth(&[(NUM_CHANNELS + 0o2540, 0o2260)]);
        let c = CoreDump::parse(&text).unwrap();
        let cs = c.dp_at(0o2540, 11).unwrap();
        assert!((cs - 150.0).abs() < 1e-6, "{cs}");
        // At the old, wrong b=14 the same bits read 12 s.
        assert!((c.dp_at(0o2540, 14).unwrap() / 100.0 - 12.0).abs() < 1e-6);
    }

    #[test]
    fn one_s_complement_handles_negatives() {
        let text = synth(&[
            (NUM_CHANNELS + 0o100, 0o77775), // -2
            (NUM_CHANNELS + 0o101, 0o00003),
        ]);
        let c = CoreDump::parse(&text).unwrap();
        assert_eq!(c.sp(0o100), Some(-2));
        assert_eq!(c.dp(0o100), Some(-2 * 16384 + 3));
    }

    #[test]
    fn rejects_a_truncated_dump() {
        let short: String = (0..100).map(|_| "000000\n").collect();
        assert!(CoreDump::parse(&short).is_err());
    }

    #[test]
    fn lr_sample_row_reads_every_field_by_symbol() {
        // A synthetic dump with known words at made-up ECADRs, driven
        // through the same address map the flight path uses. The point is
        // the wiring: each column must come from ITS symbol at ITS scale.
        let addrs: std::collections::HashMap<&'static str, u16> = [
            ("TIME2", 0o100),
            ("PIPTIME", 0o102),
            ("HMEAS", 0o104),
            ("HCALC", 0o106),
            ("DELTAH", 0o110),
            ("RGU", 0o112),
            ("VGU", 0o120),
            ("RNRAD", 0o126),
            ("FLGWRD11", 0o127),
            ("RADMODES", 0o130),
            ("LRLCTR", 0o131),
            ("LRRCTR", 0o132),
            ("LRSCTR", 0o133),
            ("LRMCTR", 0o134),
            ("FAILREG", 0o135),
        ]
        .into_iter()
        .collect();
        // DELTAH = +200 m at b=24: 200 / 2^24 * 2^28 = 3200 counts.
        // HMEAS = 1000 counts of 1.079 ft = 328.8792 m.
        let text = synth(&[
            (NUM_CHANNELS + 0o104, 0), // HMEAS hi
            (NUM_CHANNELS + 0o105, 1000),
            (NUM_CHANNELS + 0o110, 0), // DELTAH hi
            (NUM_CHANNELS + 0o111, 3200),
            (NUM_CHANNELS + 0o127, 0o200), // FLGWRD11: LRINH set
            (NUM_CHANNELS + 0o131, 7),     // LRLCTR
            (NUM_CHANNELS + 0o135, 0o1520),
            (0o33, 0o77777), // channel 33 as the LR presents it
        ]);
        let dump = CoreDump::parse(&text).unwrap();
        let row = lr_sample_row(&dump, &addrs).expect("row");
        let cols: Vec<&str> = row.split(',').collect();
        let head: Vec<&str> = LR_SAMPLE_HEADER.split(',').collect();
        assert_eq!(cols.len(), head.len(), "row must match the header width");
        let get = |name: &str| cols[head.iter().position(|h| *h == name).unwrap()];
        assert_eq!(get("hmeas_m"), "328.88");
        assert_eq!(get("deltah_m"), "200.00");
        assert_eq!(get("flgwrd11"), "00200");
        assert_eq!(get("ch33"), "77777");
        assert_eq!(get("lrlctr"), "7");
        assert_eq!(get("failreg1"), "01520");
    }

    #[test]
    fn lr_sample_addrs_names_the_symbol_it_cannot_find() {
        // A missing symbol must stop the run at start-up, not leave a
        // silently empty column in a 20-minute flight's only instrument.
        let symtab = crate::padload::SymTab::from_listing("").unwrap();
        let err = lr_sample_addrs(&symtab).unwrap_err().to_string();
        assert!(err.contains("PIPTIME"), "{err}");
        // TIME2 must NOT be looked up in the listing: it is a hardware
        // counter with no symbol, and requiring it there would make the
        // sampler impossible to start against a real build.
        assert!(!LR_SAMPLE_SYMBOLS.contains(&"TIME2"));
        assert!(!LR_SAMPLE_SYMBOLS.contains(&"RNRAD"));
        assert_eq!(TIME2_ECADR, crate::runner::TIME2_ECADR);
        assert_eq!(RNRAD_ECADR, u16::from(crate::sim::RNRAD_ADDR));
    }

    #[test]
    fn channels_and_erasable_do_not_overlap() {
        // Off-by-one between the channel block and erasable would silently
        // shift every symbol read.
        let text = synth(&[(NUM_CHANNELS - 1, 0o777), (NUM_CHANNELS, 0o111)]);
        let c = CoreDump::parse(&text).unwrap();
        assert_eq!(c.channel(NUM_CHANNELS as u16 - 1), Some(0o777));
        assert_eq!(c.word(0), Some(0o111));
    }
}
