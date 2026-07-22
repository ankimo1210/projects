use eagle_agc_protocol::Packet;
use std::path::PathBuf;

/// No-op stub. Task 10 replaces this with real JSONL tracing.
#[allow(dead_code)]
pub struct TraceWriter(Option<std::fs::File>);

impl TraceWriter {
    pub fn open(_path: Option<PathBuf>) -> anyhow::Result<Self> {
        Ok(Self(None))
    }

    pub fn log(&mut self, _dir: &str, _p: &Packet) {}
}
