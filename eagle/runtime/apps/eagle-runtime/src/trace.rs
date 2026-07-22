use anyhow::Result;
use eagle_agc_protocol::{dsky, Packet, PacketKind};
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

pub struct TraceWriter {
    file: Option<std::fs::File>,
    t0: Instant,
}

impl TraceWriter {
    pub fn open(path: Option<PathBuf>) -> Result<Self> {
        let file = match path {
            Some(p) => {
                if let Some(dir) = p.parent() { std::fs::create_dir_all(dir)?; }
                Some(std::fs::File::create(p)?)
            }
            None => None,
        };
        Ok(Self { file, t0: Instant::now() })
    }

    pub fn log(&mut self, dir: &str, p: &Packet) {
        let Some(f) = self.file.as_mut() else { return };
        let kind = match p.kind {
            PacketKind::Io => "io", PacketKind::Counter => "counter",
            PacketKind::Bitmask => "bitmask",
        };
        let _ = writeln!(
            f,
            r#"{{"t_ms":{},"dir":"{}","kind":"{}","channel":"{:03o}","data":"{:05o}"}}"#,
            self.t0.elapsed().as_millis(), dir, kind, p.channel, p.data
        );
    }
}

/// Golden-comparison view of an output stream: ch 010 relay words that carry
/// at least one non-blank digit, deduped consecutively. Event-order only —
/// no timestamps (the process backend is not bit-exact).
pub fn milestones(packets: &[Packet]) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    let mut state = dsky::DskyState::default();
    for p in packets {
        if p.channel != 0o10 { continue; }
        let visible = state.apply(p);
        let c = (p.data >> 5) & 0x1F;
        let d = p.data & 0x1F;
        if !visible || (c == 0 && d == 0) { continue; }
        let entry = (format!("{:03o}", p.channel), format!("{:05o}", p.data));
        if out.last() != Some(&entry) { out.push(entry); }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use eagle_agc_protocol::Packet;

    #[test]
    fn milestones_filters_and_dedupes() {
        let blank = Packet::io(0o10, 11 << 11).unwrap();
        let v88 = Packet::io(0o10, (10 << 11) | (0b11101 << 5) | 0b11101).unwrap();
        let lamp = Packet::io(0o11, 0b10).unwrap();
        let got = milestones(&[blank, v88, v88, lamp]);
        assert_eq!(got, vec![("010".to_string(), format!("{:05o}", v88.data))]);
    }
}
