use crate::{Packet, PacketError};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DskyKey {
    D0, D1, D2, D3, D4, D5, D6, D7, D8, D9,
    Verb, Noun, Rset, KeyRel, Plus, Minus, Entr, Clr,
}

impl DskyKey {
    pub fn code(self) -> u16 {
        use DskyKey::*;
        match self {
            D1 => 0o1, D2 => 0o2, D3 => 0o3, D4 => 0o4, D5 => 0o5,
            D6 => 0o6, D7 => 0o7, D8 => 0o10, D9 => 0o11, D0 => 0o20,
            Verb => 0o21, Rset => 0o22, KeyRel => 0o31, Plus => 0o32,
            Minus => 0o33, Entr => 0o34, Clr => 0o36, Noun => 0o37,
        }
    }
    pub fn packet(self) -> Packet {
        Packet::io(0o15, self.code()).expect("static keycodes are in range")
    }
    pub fn from_name(name: &str) -> Option<Self> {
        use DskyKey::*;
        Some(match name {
            "0" => D0, "1" => D1, "2" => D2, "3" => D3, "4" => D4,
            "5" => D5, "6" => D6, "7" => D7, "8" => D8, "9" => D9,
            "VERB" => Verb, "NOUN" => Noun, "RSET" => Rset, "KEY_REL" => KeyRel,
            "PLUS" => Plus, "MINUS" => Minus, "ENTR" => Entr, "CLR" => Clr,
            _ => return None,
        })
    }
}

/// PRO/STBY is not a keycode: it is input channel 032 bit 14, inverted
/// (0 = pressed). Send a bitmask packet claiming bit 14, then the value.
pub fn pro_key_packets(pressed: bool) -> [Packet; 2] {
    let bit = 1u16 << 13; // bit 14, 1-indexed
    let value = if pressed { 0 } else { bit };
    [
        Packet::bitmask(0o32, bit).expect("static"),
        Packet::io(0o32, value).expect("static"),
    ]
}

#[allow(unused)]
fn _err_ty(_: PacketError) {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keycodes_match_channel_map() {
        assert_eq!(DskyKey::D0.code(), 0o20);
        assert_eq!(DskyKey::D9.code(), 0o11);
        assert_eq!(DskyKey::Verb.code(), 0o21);
        assert_eq!(DskyKey::Noun.code(), 0o37);
        assert_eq!(DskyKey::Entr.code(), 0o34);
        assert_eq!(DskyKey::Rset.code(), 0o22);
        assert_eq!(DskyKey::Clr.code(), 0o36);
        assert_eq!(DskyKey::KeyRel.code(), 0o31);
        assert_eq!(DskyKey::Plus.code(), 0o32);
        assert_eq!(DskyKey::Minus.code(), 0o33);
    }

    #[test]
    fn key_packet_targets_ch015() {
        let p = DskyKey::Verb.packet();
        assert_eq!((p.channel, p.data), (0o15, 0o21));
    }

    #[test]
    fn from_name_roundtrip() {
        assert_eq!(DskyKey::from_name("VERB"), Some(DskyKey::Verb));
        assert_eq!(DskyKey::from_name("5"), Some(DskyKey::D5));
        assert_eq!(DskyKey::from_name("bogus"), None);
    }

    #[test]
    fn pro_key_uses_ch032_bit14_inverted() {
        use crate::PacketKind;
        let [mask, val] = pro_key_packets(true);
        assert_eq!(mask.kind, PacketKind::Bitmask);
        assert_eq!((mask.channel, mask.data), (0o32, 1 << 13));
        assert_eq!(val.kind, PacketKind::Io);
        assert_eq!((val.channel, val.data), (0o32, 0)); // pressed => bit low
        let [_, released] = pro_key_packets(false);
        assert_eq!(released.data, 1 << 13);
    }
}
