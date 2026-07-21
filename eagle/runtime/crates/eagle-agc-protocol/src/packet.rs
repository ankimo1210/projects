//! yaAGC 4-byte socket packet codec.
//! Layout (developer.html): 00utpppp 01pppddd 10dddddd 11dddddd
//! u = bitmask flag, t = counter flag, p = 7-bit channel, d = 15-bit data.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PacketKind { Io, Counter, Bitmask }

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Packet {
    pub kind: PacketKind,
    pub channel: u8,
    pub data: u16,
}

pub const PING: [u8; 4] = [0xFF, 0xFF, 0xFF, 0xFF];

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum PacketError {
    #[error("bad packet signature: {0:02x?}")]
    BadSignature([u8; 4]),
    #[error("channel out of range: {0:#o}")]
    ChannelRange(u8),
    #[error("data out of range: {0:#o}")]
    DataRange(u16),
}

impl Packet {
    fn new(kind: PacketKind, channel: u8, data: u16) -> Result<Self, PacketError> {
        if channel > 0x7F { return Err(PacketError::ChannelRange(channel)); }
        if data > 0x7FFF { return Err(PacketError::DataRange(data)); }
        Ok(Self { kind, channel, data })
    }
    pub fn io(channel: u8, data: u16) -> Result<Self, PacketError> {
        Self::new(PacketKind::Io, channel, data)
    }
    pub fn counter(channel: u8, data: u16) -> Result<Self, PacketError> {
        Self::new(PacketKind::Counter, channel, data)
    }
    pub fn bitmask(channel: u8, data: u16) -> Result<Self, PacketError> {
        Self::new(PacketKind::Bitmask, channel, data)
    }

    pub fn encode(&self) -> [u8; 4] {
        let u = matches!(self.kind, PacketKind::Bitmask) as u8;
        let t = matches!(self.kind, PacketKind::Counter) as u8;
        let (ch, d) = (self.channel, self.data);
        [
            (u << 5) | (t << 4) | (ch >> 3),
            0x40 | ((ch & 0b111) << 3) | ((d >> 12) as u8),
            0x80 | (((d >> 6) & 0x3F) as u8),
            0xC0 | ((d & 0x3F) as u8),
        ]
    }

    pub fn decode(b: [u8; 4]) -> Result<Self, PacketError> {
        if b[0] >> 6 != 0b00 || b[1] >> 6 != 0b01
            || b[2] >> 6 != 0b10 || b[3] >> 6 != 0b11 {
            return Err(PacketError::BadSignature(b));
        }
        let kind = match ((b[0] >> 5) & 1, (b[0] >> 4) & 1) {
            (1, _) => PacketKind::Bitmask,
            (0, 1) => PacketKind::Counter,
            _ => PacketKind::Io,
        };
        let channel = ((b[0] & 0x0F) << 3) | ((b[1] >> 3) & 0b111);
        let data = (((b[1] & 0b111) as u16) << 12)
            | (((b[2] & 0x3F) as u16) << 6)
            | ((b[3] & 0x3F) as u16);
        Ok(Self { kind, channel, data })
    }
}

/// Incremental decoder over a TCP byte stream: aligns on signature bits,
/// resyncs by shifting one byte on mismatch, drops ping packets.
#[derive(Default)]
pub struct StreamDecoder { buf: Vec<u8> }

impl StreamDecoder {
    pub fn new() -> Self { Self::default() }

    pub fn push(&mut self, bytes: &[u8]) -> Vec<Packet> {
        self.buf.extend_from_slice(bytes);
        let mut out = Vec::new();
        while self.buf.len() >= 4 {
            let head: [u8; 4] = self.buf[..4].try_into().unwrap();
            if head == PING {
                self.buf.drain(..4);
            } else if let Ok(p) = Packet::decode(head) {
                self.buf.drain(..4);
                out.push(p);
            } else {
                self.buf.remove(0); // resync one byte at a time
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_io_packet() {
        let p = Packet::io(0o15, 0o31).unwrap();
        assert_eq!(Packet::decode(p.encode()).unwrap(), p);
    }

    #[test]
    fn known_vector_ch015_data031() {
        // hand-computed from the 00utpppp 01pppddd 10dddddd 11dddddd layout
        let p = Packet::io(0o15, 0o31).unwrap();
        assert_eq!(p.encode(), [0x01, 0x68, 0x80, 0xD9]);
    }

    #[test]
    fn rejects_bad_signature() {
        assert!(matches!(
            Packet::decode([0xFF, 0x00, 0x80, 0xC0]),
            Err(PacketError::BadSignature(_))
        ));
    }

    #[test]
    fn rejects_out_of_range() {
        assert!(Packet::io(0x80, 0).is_err());
        assert!(Packet::io(0o15, 0x8000).is_err());
    }

    #[test]
    fn stream_decoder_resyncs_and_skips_pings() {
        let good = Packet::io(0o10, 0o12345).unwrap();
        let mut bytes = vec![0xC0, 0x81]; // garbage tail of a torn packet
        bytes.extend_from_slice(&PING);
        bytes.extend_from_slice(&good.encode());
        let mut dec = StreamDecoder::new();
        assert_eq!(dec.push(&bytes), vec![good]);
    }

    #[test]
    fn stream_decoder_handles_split_packets() {
        let good = Packet::io(0o11, 0o4).unwrap();
        let enc = good.encode();
        let mut dec = StreamDecoder::new();
        assert_eq!(dec.push(&enc[..2]), vec![]);
        assert_eq!(dec.push(&enc[2..]), vec![good]);
    }
}
