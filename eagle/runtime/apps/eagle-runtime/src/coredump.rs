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
    fn channels_and_erasable_do_not_overlap() {
        // Off-by-one between the channel block and erasable would silently
        // shift every symbol read.
        let text = synth(&[(NUM_CHANNELS - 1, 0o777), (NUM_CHANNELS, 0o111)]);
        let c = CoreDump::parse(&text).unwrap();
        assert_eq!(c.channel(NUM_CHANNELS as u16 - 1), Some(0o777));
        assert_eq!(c.word(0), Some(0o111));
    }
}
