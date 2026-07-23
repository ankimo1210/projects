//! AGC 15-bit one's-complement word encoding (SP/DP) and B-scaling.

pub fn sp_encode(pulses: i16) -> u16 {
    debug_assert!(pulses.unsigned_abs() < (1 << 14));
    if pulses >= 0 {
        pulses as u16
    } else {
        (!((-pulses) as u16)) & 0o77777
    }
}

pub fn sp_decode(word: u16) -> i16 {
    let word = word & 0o77777;
    if word & 0o40000 == 0 {
        word as i16
    } else {
        let mag = (!word) & 0o37777;
        -(mag as i16)
    }
}

pub fn dp_encode(pulses: i64) -> [u16; 2] {
    debug_assert!(pulses.unsigned_abs() < (1 << 28));
    let neg = pulses < 0;
    let mag = pulses.unsigned_abs();
    let (hi, lo) = ((mag >> 14) as i16, (mag & 0x3FFF) as i16);
    let (hi, lo) = if neg { (-hi, -lo) } else { (hi, lo) };
    [sp_encode(hi), sp_encode(lo)]
}

pub fn dp_decode(w: [u16; 2]) -> i64 {
    (sp_decode(w[0]) as i64) * (1 << 14) + sp_decode(w[1]) as i64
}

/// value → integer pulses for a variable scaled B`b_scale`.
/// SP LSB = 2^(b−14), DP LSB = 2^(b−28) physical units.
pub fn to_pulses(value: f64, b_scale: i32, dp: bool) -> i64 {
    let lsb_exp = b_scale - if dp { 28 } else { 14 };
    (value / (lsb_exp as f64).exp2()).round() as i64
}

pub fn octal5(word: u16) -> String {
    format!("{:05o}", word & 0o77777)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sp_ones_complement() {
        assert_eq!(sp_encode(0), 0);
        assert_eq!(sp_encode(1), 1);
        assert_eq!(sp_encode(-1), 0o77776);
        assert_eq!(sp_encode(16383), 0o37777);
        assert_eq!(sp_encode(-16383), 0o40000);
        for v in [-16383i16, -1, 0, 1, 42, 16383] {
            assert_eq!(sp_decode(sp_encode(v)), v);
        }
        assert_eq!(sp_decode(0o77777), 0); // −0 → +0
    }

    #[test]
    fn dp_split_and_sign() {
        assert_eq!(dp_encode(0), [0, 0]);
        assert_eq!(dp_encode(1), [0, 1]);
        assert_eq!(dp_encode(16384), [1, 0]);            // 2^14
        assert_eq!(dp_encode(16385), [1, 1]);
        assert_eq!(dp_encode(-16385), [0o77776, 0o77776]); // both words negative
        let max = (1i64 << 28) - 1;
        for v in [-max, -16385, -1, 0, 1, 16383, 16384, max] {
            assert_eq!(dp_decode(dp_encode(v)), v, "v={v}");
        }
    }

    #[test]
    fn physical_to_pulses() {
        // SP scaled B14: 1 pulse = 1 unit
        assert_eq!(to_pulses(42.0, 14, false), 42);
        // SP scaled B0: value is a fraction of 1, pulse = 2^-14
        assert_eq!(to_pulses(0.5, 0, false), 8192);
        // DP scaled B28: 1 pulse = 1 unit
        assert_eq!(to_pulses(-123456.0, 28, true), -123456);
        // DP scaled B27 (e.g. lunar position in meters): pulse = 2^-1 m
        assert_eq!(to_pulses(1_000_000.0, 27, true), 2_000_000);
    }

    #[test]
    fn octal_formatting() {
        assert_eq!(octal5(0), "00000");
        assert_eq!(octal5(0o77776), "77776");
        assert_eq!(octal5(0o1234), "01234");
    }
}
