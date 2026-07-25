pub mod constants;
pub mod forces;
pub mod frames;
pub mod rk4;
pub mod state;
pub mod touchdown;

#[cfg(test)]
pub(crate) mod testutil {
    use crate::frames::{Rot, V3};
    use crate::state::LmState;

    /// Canonical hover start: 500 m above the landing-site radius on the
    /// MCI x-axis, at rest, identity attitude. Shared by Task 8 and 9 tests.
    pub fn hover_state() -> LmState {
        LmState {
            t: 0.0,
            pos: V3::new(crate::constants::R_SITE + 500.0, 0.0, 0.0),
            vel: V3::zero(),
            att: Rot::identity(),
            omega: V3::zero(),
            mass_kg: 9159.0,
            fuel_dps_kg: 2000.0,
            fuel_rcs_kg: 150.0,
        }
    }
}
