//! LM autopilot I/O: counter builders, output decoding, discrete writes.
//! Semantics cited from vendor sources — see docs/agc-channel-map.md.
use crate::packet::{Packet, PacketKind};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PipaAxis { X, Y, Z }
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CduAxis { X, Y, Z }
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThrustPulse { Pout, Mout, Zout }

pub const INC_PINC: u16 = 0;
pub const INC_PCDU: u16 = 1;
pub const INC_MINC: u16 = 2;
pub const INC_MCDU: u16 = 3;
pub const INC_DINC: u16 = 4;
pub const INC_PCDU_FAST: u16 = 0o21;
pub const INC_MCDU_FAST: u16 = 0o23;

const PIPA_ADDR: [u8; 3] = [0o37, 0o40, 0o41];
const CDU_ADDR: [u8; 3] = [0o32, 0o33, 0o34];
pub const THRUST_ADDR: u8 = 0o55;

pub fn pipa_pulse(axis: PipaAxis, positive: bool) -> Packet {
    let inc = if positive { INC_PINC } else { INC_MINC };
    Packet::counter(PIPA_ADDR[axis as usize], inc).expect("static packet")
}

pub fn cdu_pulse(axis: CduAxis, positive: bool, fast: bool) -> Packet {
    let inc = match (positive, fast) {
        (true, false) => INC_PCDU,
        (false, false) => INC_MCDU,
        (true, true) => INC_PCDU_FAST,
        (false, true) => INC_MCDU_FAST,
    };
    Packet::counter(CDU_ADDR[axis as usize], inc).expect("static packet")
}

pub fn thrust_dinc() -> Packet {
    Packet::counter(THRUST_ADDR, INC_DINC).expect("static packet")
}

/// ROD switch click on ch 016: bit5 (+1, slow descent) / bit6 (−1).
/// Returns (press, release); send release at least one tick later so the
/// channel-change interrupt (MARKRUPT→DESCBITS) latches the click.
pub fn rod_click(up: bool) -> (Packet, Packet) {
    let bit = if up { 1 << 5 } else { 1 << 6 };
    (Packet::io(0o16, bit).expect("static"), Packet::io(0o16, 0).expect("static"))
}

/// Bitmask-then-value pair for (possibly inverted) discrete channels.
/// `bits_high` are driven to 1, `bits_low` to 0; untouched bits keep their
/// current value (that is what the bitmask packet guarantees).
pub fn discrete_write(channel: u8, bits_high: u16, bits_low: u16) -> [Packet; 2] {
    [
        Packet::bitmask(channel, bits_high | bits_low).expect("mask"),
        Packet::io(channel, bits_high).expect("value"),
    ]
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgcOutput {
    Jets5 { mask: u8 },
    Jets6 { mask: u8 },
    Engine { on: bool, off: bool },
    Trim { minus_pitch: bool, plus_pitch: bool, minus_roll: bool, plus_roll: bool },
    ThrustDrive(bool),
    ThrustPulse(ThrustPulse),
    CoarseAlign { axis: CduAxis, positive: bool, pulses: u16 },
    Gyro { raw: u16 },
    Downlink,
    Other(Packet),
}

pub fn decode_output(p: &Packet) -> AgcOutput {
    if p.kind == PacketKind::Counter && p.channel == THRUST_ADDR {
        return match p.data {
            0o15 => AgcOutput::ThrustPulse(ThrustPulse::Pout),
            0o16 => AgcOutput::ThrustPulse(ThrustPulse::Mout),
            0o17 => AgcOutput::ThrustPulse(ThrustPulse::Zout),
            _ => AgcOutput::Other(*p),
        };
    }
    match p.channel {
        0o5 => AgcOutput::Jets5 { mask: (p.data & 0xFF) as u8 },
        0o6 => AgcOutput::Jets6 { mask: (p.data & 0xFF) as u8 },
        0o11 => AgcOutput::Engine {
            on: p.data & (1 << 12) != 0,
            off: p.data & (1 << 13) != 0,
        },
        0o12 => AgcOutput::Trim {
            minus_pitch: p.data & (1 << 8) != 0,
            plus_pitch: p.data & (1 << 9) != 0,
            minus_roll: p.data & (1 << 10) != 0,
            plus_roll: p.data & (1 << 11) != 0,
        },
        0o14 => AgcOutput::ThrustDrive(p.data & (1 << 3) != 0),
        0o174 | 0o175 | 0o176 => AgcOutput::CoarseAlign {
            axis: match p.channel { 0o174 => CduAxis::X, 0o175 => CduAxis::Y, _ => CduAxis::Z },
            positive: p.data & 0o40000 == 0,
            pulses: p.data & 0o37777,
        },
        0o177 => AgcOutput::Gyro { raw: p.data },
        0o34 | 0o35 => AgcOutput::Downlink,
        _ => AgcOutput::Other(*p),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pipa_pulse_packets() {
        // PINC to PIPAX (037): counter packet, channel field = octal address, data = IncType 0
        assert_eq!(pipa_pulse(PipaAxis::X, true),
                   Packet::counter(0o37, 0).unwrap());
        // MINC to PIPAZ (041): IncType 2
        assert_eq!(pipa_pulse(PipaAxis::Z, false),
                   Packet::counter(0o41, 2).unwrap());
    }

    #[test]
    fn cdu_pulse_packets() {
        assert_eq!(cdu_pulse(CduAxis::X, true, false), Packet::counter(0o32, 1).unwrap());
        assert_eq!(cdu_pulse(CduAxis::Y, false, false), Packet::counter(0o33, 3).unwrap());
        assert_eq!(cdu_pulse(CduAxis::Z, true, true), Packet::counter(0o34, 0o21).unwrap());
        assert_eq!(cdu_pulse(CduAxis::Z, false, true), Packet::counter(0o34, 0o23).unwrap());
    }

    #[test]
    fn thrust_dinc_packet() {
        assert_eq!(thrust_dinc(), Packet::counter(0o55, 4).unwrap());
    }

    #[test]
    fn rod_click_press_release() {
        let (press, release) = rod_click(true);   // bit 6 = +1 click (slow descent)
        assert_eq!(press, Packet::io(0o16, 1 << 5).unwrap());
        assert_eq!(release, Packet::io(0o16, 0).unwrap());
        let (press, _) = rod_click(false);        // bit 7 = −1 click
        assert_eq!(press, Packet::io(0o16, 1 << 6).unwrap());
    }

    #[test]
    fn discrete_write_bitmask_then_value() {
        // assert ch030 bit5 (write 0), deassert bit3 (write 1): mask covers both bits
        let [mask, value] = discrete_write(0o30, 1 << 2, 1 << 4);
        assert_eq!(mask, Packet::bitmask(0o30, (1 << 2) | (1 << 4)).unwrap());
        assert_eq!(value, Packet::io(0o30, 1 << 2).unwrap());
    }

    #[test]
    fn decode_autopilot_outputs() {
        assert!(matches!(decode_output(&Packet::io(0o5, 0b1010_0001).unwrap()),
            AgcOutput::Jets5 { mask: 0b1010_0001 }));
        assert!(matches!(decode_output(&Packet::io(0o11, 1 << 12).unwrap()),
            AgcOutput::Engine { on: true, off: false }));
        assert!(matches!(decode_output(&Packet::io(0o12, 1 << 9).unwrap()),
            AgcOutput::Trim { plus_pitch: true, minus_pitch: false, .. }));
        assert!(matches!(decode_output(&Packet::io(0o14, 1 << 3).unwrap()),
            AgcOutput::ThrustDrive(true)));
        assert!(matches!(decode_output(&Packet::counter(0o55, 0o15).unwrap()),
            AgcOutput::ThrustPulse(ThrustPulse::Pout)));
        assert!(matches!(decode_output(&Packet::counter(0o55, 0o16).unwrap()),
            AgcOutput::ThrustPulse(ThrustPulse::Mout)));
        // coarse align X: fictitious channel 0174 (fits in 7 bits: 0o174 = 124),
        // direction bit 0o40000, 24 pulses — direction polarity pinned in Step 0
        assert!(matches!(decode_output(&Packet::io(0o174, 0o40000 | 24).unwrap()),
            AgcOutput::CoarseAlign { axis: CduAxis::X, pulses: 24, .. }));
        assert!(matches!(decode_output(&Packet::io(0o177, 0o1234).unwrap()),
            AgcOutput::Gyro { raw: 0o1234 }));
        assert!(matches!(decode_output(&Packet::io(0o34, 0).unwrap()), AgcOutput::Downlink));
    }
}
