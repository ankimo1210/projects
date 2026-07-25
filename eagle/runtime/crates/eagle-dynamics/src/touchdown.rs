//! Touchdown classifier (spec §4): a threshold ladder on vertical speed,
//! horizontal speed, and tilt at ground contact.

/// Landing quality at contact.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Touchdown {
    Nominal,
    Hard,
    Crash,
}

/// Classify a contact from vertical speed (m/s), horizontal speed (m/s) and
/// tilt from vertical (deg). Nominal: <3 / <1.5 / <12. Hard: <6 / <3 / <20.
/// Anything worse on any axis is a Crash.
pub fn classify_touchdown(v_vert: f64, v_horiz: f64, tilt_deg: f64) -> Touchdown {
    if v_vert < 3.0 && v_horiz < 1.5 && tilt_deg < 12.0 {
        Touchdown::Nominal
    } else if v_vert < 6.0 && v_horiz < 3.0 && tilt_deg < 20.0 {
        Touchdown::Hard
    } else {
        Touchdown::Crash
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn touchdown_classification() {
        assert_eq!(classify_touchdown(2.9, 1.4, 11.9), Touchdown::Nominal);
        assert_eq!(classify_touchdown(3.1, 0.0, 0.0), Touchdown::Hard);
        assert_eq!(classify_touchdown(6.1, 0.0, 0.0), Touchdown::Crash);
        assert_eq!(classify_touchdown(0.5, 3.5, 0.0), Touchdown::Crash);
        assert_eq!(classify_touchdown(0.5, 0.1, 25.0), Touchdown::Crash);
    }
}
