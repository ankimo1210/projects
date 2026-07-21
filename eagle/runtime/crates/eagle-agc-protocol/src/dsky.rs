//! DSKY display-state decoder for output channels 010/011/0163.
//! Sources: docs/agc-channel-map.md (row/bit tables with citations).

use crate::Packet;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RegisterDisplay {
    pub sign: char,
    pub digits: [char; 5],
}

impl Default for RegisterDisplay {
    fn default() -> Self { Self { sign: ' ', digits: [' '; 5] } }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Lamps {
    pub comp_acty: bool,
    pub uplink_acty: bool,
    pub no_att: bool,
    pub gimbal_lock: bool,
    pub prog_alarm: bool,
    pub tracker: bool,
    pub alt: bool,
    pub vel: bool,
    pub no_dap: bool,
    pub prio_disp: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct DskyState {
    pub prog: [char; 2],
    pub verb: [char; 2],
    pub noun: [char; 2],
    pub r1: RegisterDisplay,
    pub r2: RegisterDisplay,
    pub r3: RegisterDisplay,
    pub lamps: Lamps,
    pub verb_noun_flash: bool,
    pub restart: bool,
    pub standby: bool,
    pub key_rel: bool,
    pub opr_err: bool,
    pub temp: bool,
    // internal: sign is driven by two rows (plus-row and minus-row). Not
    // part of crew-visible state, so deliberately excluded from PartialEq
    // below (see `apply`'s change-detection contract).
    plus: [bool; 3],
    minus: [bool; 3],
}

/// Equality (and thus `apply`'s change-detection) is defined over the
/// crew-visible fields only. `plus`/`minus` are internal per-register sign
/// bookkeeping: two rows can toggle them without changing the resolved
/// `sign` (e.g. the `+` row already set, then the `-` row toggles — `+`
/// keeps priority), and they never appear in any public field. Including
/// them in equality would make `apply()` report spurious "visible change"
/// events for state nobody can see.
impl PartialEq for DskyState {
    fn eq(&self, other: &Self) -> bool {
        self.prog == other.prog
            && self.verb == other.verb
            && self.noun == other.noun
            && self.r1 == other.r1
            && self.r2 == other.r2
            && self.r3 == other.r3
            && self.lamps == other.lamps
            && self.verb_noun_flash == other.verb_noun_flash
            && self.restart == other.restart
            && self.standby == other.standby
            && self.key_rel == other.key_rel
            && self.opr_err == other.opr_err
            && self.temp == other.temp
    }
}

impl Eq for DskyState {}

impl Default for DskyState {
    fn default() -> Self {
        Self {
            prog: [' '; 2], verb: [' '; 2], noun: [' '; 2],
            r1: Default::default(), r2: Default::default(), r3: Default::default(),
            lamps: Default::default(),
            verb_noun_flash: false, restart: false, standby: false,
            key_rel: false, opr_err: false, temp: false,
            plus: [false; 3], minus: [false; 3],
        }
    }
}

fn digit(code: u16) -> char {
    match code {
        0 => ' ',
        0b10101 => '0', 0b00011 => '1', 0b11001 => '2', 0b11011 => '3',
        0b01111 => '4', 0b11110 => '5', 0b11100 => '6', 0b10011 => '7',
        0b11101 => '8', 0b11111 => '9',
        _ => '?',
    }
}

impl DskyState {
    /// Apply one decoded packet to the display state. Returns `true` if any
    /// field visible to the crew changed as a result.
    pub fn apply(&mut self, p: &Packet) -> bool {
        let before = *self;
        match p.channel {
            0o10 => self.apply_relay(p.data),
            0o11 => {
                // ch011 bits (yaDSKY2.cpp:184 UplinkActy=04, :198 Temp=010;
                // ActOnIncomingIO ~2085: bit1(value2)=COMP ACTY, bit2(value4)=UPLINK ACTY)
                let b = |n: u16| p.data & (1 << (n - 1)) != 0;
                self.lamps.comp_acty = b(2);
                self.lamps.uplink_acty = b(3);
            }
            0o163 => {
                // ch0163 bits, agc_engine.h:283-290 (DSKY_* masks, octal):
                // TEMP=010(bit4), KEY_REL=020(bit5), VN_FLASH=040(bit6),
                // OPER_ERR=0100(bit7), RESTART=0200(bit8), STBY=0400(bit9).
                let b = |n: u16| p.data & (1 << (n - 1)) != 0;
                self.temp = b(4);
                self.key_rel = b(5);
                self.verb_noun_flash = b(6);
                self.opr_err = b(7);
                self.restart = b(8);
                self.standby = b(9);
            }
            _ => {}
        }
        for i in 0..3 {
            let sign = match (self.plus[i], self.minus[i]) {
                (true, _) => '+',
                (false, true) => '-',
                _ => ' ',
            };
            match i { 0 => self.r1.sign = sign, 1 => self.r2.sign = sign, _ => self.r3.sign = sign }
        }
        *self != before
    }

    fn apply_relay(&mut self, data: u16) {
        let row = (data >> 11) & 0xF;
        let b = (data >> 10) & 1 != 0;
        let c = digit((data >> 5) & 0x1F);
        let d = digit(data & 0x1F);
        match row {
            11 => { self.prog = [c, d]; }
            10 => { self.verb = [c, d]; }
            9 => { self.noun = [c, d]; }
            8 => { self.r1.digits[0] = d; }
            7 => { self.plus[0] = b; self.r1.digits[1] = c; self.r1.digits[2] = d; }
            6 => { self.minus[0] = b; self.r1.digits[3] = c; self.r1.digits[4] = d; }
            5 => { self.plus[1] = b; self.r2.digits[0] = c; self.r2.digits[1] = d; }
            4 => { self.minus[1] = b; self.r2.digits[2] = c; self.r2.digits[3] = d; }
            3 => { self.r2.digits[4] = c; self.r3.digits[0] = d; }
            2 => { self.plus[2] = b; self.r3.digits[1] = c; self.r3.digits[2] = d; }
            1 => { self.minus[2] = b; self.r3.digits[3] = c; self.r3.digits[4] = d; }
            12 => {
                // row 12 lamps: yaDSKY2.cpp:181-207 Inds[] table, Latched=1,
                // RowMask=074000, Row=060000 (row 12); Bitmask field gives
                // the bit within the low 10 bits of the relay word.
                let l = |n: u16| data & (1 << n) != 0;
                self.lamps.prio_disp = l(0);
                self.lamps.no_dap = l(1);
                self.lamps.vel = l(2);
                self.lamps.no_att = l(3);
                self.lamps.alt = l(4);
                self.lamps.gimbal_lock = l(5);
                self.lamps.tracker = l(7);
                self.lamps.prog_alarm = l(8);
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Packet;

    // relay word helper: AAAA B CCCCC DDDDD
    fn relay(row: u16, b: u16, c: u16, d: u16) -> Packet {
        Packet::io(0o10, (row << 11) | (b << 10) | (c << 5) | d).unwrap()
    }

    #[test]
    fn decodes_prog_63() {
        let mut s = DskyState::default();
        // row 11 drives M1/M2 (PROG). '6' = 0b11100, '3' = 0b11011
        s.apply(&relay(11, 0, 0b11100, 0b11011));
        assert_eq!(s.prog, ['6', '3']);
    }

    #[test]
    fn decodes_verb_noun() {
        let mut s = DskyState::default();
        s.apply(&relay(10, 0, 0b00011, 0b11100)); // VERB 16
        s.apply(&relay(9, 0, 0b11011, 0b11100)); // NOUN 36
        assert_eq!(s.verb, ['1', '6']);
        assert_eq!(s.noun, ['3', '6']);
    }

    #[test]
    fn decodes_r1_with_sign() {
        let mut s = DskyState::default();
        s.apply(&relay(8, 0, 0, 0b10101));       // R1D1 = '0'
        s.apply(&relay(7, 1, 0b10101, 0b10101)); // +sign, R1D2, R1D3
        s.apply(&relay(6, 0, 0b11011, 0b00011)); // no -sign, R1D4='3', R1D5='1'
        assert_eq!(s.r1.sign, '+');
        assert_eq!(s.r1.digits, ['0', '0', '0', '3', '1']);
    }

    #[test]
    fn blank_code_blanks_digit() {
        let mut s = DskyState::default();
        s.apply(&relay(11, 0, 0b11101, 0b11101)); // "88"
        s.apply(&relay(11, 0, 0, 0));             // blank both
        assert_eq!(s.prog, [' ', ' ']);
    }

    #[test]
    fn lamp_channel_011() {
        let mut s = DskyState::default();
        assert!(s.apply(&Packet::io(0o11, 1 << 1).unwrap())); // bit 2: COMP ACTY
        assert!(s.lamps.comp_acty);
        s.apply(&Packet::io(0o11, 0).unwrap());
        assert!(!s.lamps.comp_acty);
    }

    #[test]
    fn flash_and_restart_on_0163() {
        let mut s = DskyState::default();
        // bit 6 = VERB/NOUN flash, bit 8 = RESTART (verify in Step 0)
        s.apply(&Packet::io(0o163, (1 << 5) | (1 << 7)).unwrap());
        assert!(s.verb_noun_flash);
        assert!(s.restart);
    }

    #[test]
    fn apply_reports_change() {
        let mut s = DskyState::default();
        let p = relay(10, 0, 0b00011, 0b11100);
        assert!(s.apply(&p));
        assert!(!s.apply(&p)); // same word again: no visible change
    }

    #[test]
    fn internal_sign_bookkeeping_change_is_not_visible() {
        let mut s = DskyState::default();
        // Row 7 sets the R1 "+" row: resolved sign flips ' ' -> '+', a
        // visible change.
        assert!(s.apply(&relay(7, 1, 0, 0)));
        assert_eq!(s.r1.sign, '+');
        // Row 6 now sets the R1 "-" row too. This flips the internal
        // `minus[0]` bookkeeping bit, but `+` keeps priority so the
        // resolved sign (and every digit) is unchanged: nothing visible
        // changed, so apply() must report false even though a private
        // field flipped.
        assert!(!s.apply(&relay(6, 1, 0, 0)));
        assert_eq!(s.r1.sign, '+');
    }
}
