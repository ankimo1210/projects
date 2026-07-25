//! IMU gimbal model and CDU pulse feed (spec §5).
//!
//! Gimbal transform: the Body→SM direction-cosine matrix and its
//! gimbal-angle parametrisation are transcribed from LM_Simulator's
//! `Transform_BodyAxes_StableMember` / `modify_pipaXYZ`
//! (`Contributed/LM_Simulator/modules/AGC_IMU.tcl:614-683`), where
//! IMUX=OGA (outer), IMUY=IGA (inner), IMUZ=MGA (middle). From that matrix
//! `M` (v_sm = M·v_body):
//!   M[1][0] = sin(MGA)              → MGA = asin(M[1][0])
//!   M[0][0] = cos(MGA)cos(IGA), M[2][0] = −cos(MGA)sin(IGA)
//!                                   → IGA = atan2(−M[2][0], M[0][0])
//!   M[1][1] = cos(OGA)cos(MGA), M[1][2] = −sin(OGA)cos(MGA)
//!                                   → OGA = atan2(−M[1][2], M[1][1])
//! so a single body-axis rotation drives exactly one gimbal: X→OGA(gimbal
//! 0), Y→IGA(gimbal 1), Z→MGA(gimbal 2).
use eagle_agc_protocol::agc_io::{cdu_pulse, CduAxis};
use eagle_agc_protocol::Packet;
use eagle_dynamics::constants::{CDU_INCR_DEG, COARSE_INCR_DEG, GYRO_FINE_INCR_DEG};
use eagle_dynamics::frames::{Body, Mci, Rot, Sm, V3};

const RAD_TO_DEG: f64 = 180.0 / std::f64::consts::PI;

/// IMU: the stable-member orientation plus per-axis coarse-align offsets.
#[derive(Debug, Clone)]
pub struct Imu {
    sm_to_mci: Rot<Sm, Mci>,
    /// Coarse-align gimbal offsets, degrees (added to the extracted angles).
    coarse_offset_deg: [f64; 3],
}

impl Imu {
    pub fn new(sm_to_mci: Rot<Sm, Mci>) -> Self {
        Self {
            sm_to_mci,
            coarse_offset_deg: [0.0; 3],
        }
    }

    pub fn sm_to_mci(&self) -> Rot<Sm, Mci> {
        self.sm_to_mci
    }

    /// The three IMU gimbal angles (deg) for a Body→MCI attitude:
    /// `[IMUX/OGA, IMUY/IGA, IMUZ/MGA]`, plus any coarse-align offset.
    pub fn gimbals_deg(&self, att: &Rot<Body, Mci>) -> [f64; 3] {
        // v_sm = (SM→MCI)^-1 · att · v_body, so Body→SM = att.then(sm⁻¹).
        let body_to_sm: Rot<Body, Sm> = att.then(self.sm_to_mci.inverse());
        // Columns of M are the images of the body basis in SM coords.
        let c0 = body_to_sm.apply(V3::new(1.0, 0.0, 0.0));
        let c1 = body_to_sm.apply(V3::new(0.0, 1.0, 0.0));
        let c2 = body_to_sm.apply(V3::new(0.0, 0.0, 1.0));
        // M[row][col]: row = SM axis, col = body axis.
        let m10 = c0.y;
        let m00 = c0.x;
        let m20 = c0.z;
        let m11 = c1.y;
        let m12 = c2.y;
        let mga = m10.clamp(-1.0, 1.0).asin();
        let iga = (-m20).atan2(m00);
        let oga = (-m12).atan2(m11);
        [
            oga * RAD_TO_DEG + self.coarse_offset_deg[0],
            iga * RAD_TO_DEG + self.coarse_offset_deg[1],
            mga * RAD_TO_DEG + self.coarse_offset_deg[2],
        ]
    }

    /// Coarse align: shift a gimbal reference by `signed_pulses` IMU
    /// coarse-align increments (0.043948°/pulse, `lm_simulator.tcl:143`).
    pub fn apply_coarse(&mut self, axis: CduAxis, signed_pulses: i32) {
        self.coarse_offset_deg[axis as usize] += signed_pulses as f64 * COARSE_INCR_DEG;
    }

    /// Gyro fine-align torque. The channel-0177 word packs the ch014 gyro
    /// select/direction nibble in bits 11-14 and the pulse count in bits
    /// 0-10 (`agc_engine.c:2354-2390`; ch014 bit7=SELECT B, bit8=SELECT A,
    /// bit9=NEGATIVE, `INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc:122-125`).
    /// Wave 1: the count rotates the stable member by GYRO_FINE_INCR per
    /// pulse about the selected SM axis; the SELECT A/B → axis assignment
    /// (1=X, 2=Y, 3=Z) is an assumption — no in-flight fine align is
    /// exercised in Wave 1 (REFSMFLG is pad-loaded).
    pub fn apply_gyro(&mut self, raw: u16) {
        let count = (raw & 0o3777) as i32;
        if count == 0 {
            return;
        }
        let sel_b = (raw >> 12) & 1;
        let sel_a = (raw >> 13) & 1;
        let negative = (raw >> 14) & 1 == 1;
        let axis = match (sel_a << 1) | sel_b {
            1 => V3::<Sm>::new(1.0, 0.0, 0.0),
            2 => V3::<Sm>::new(0.0, 1.0, 0.0),
            3 => V3::<Sm>::new(0.0, 0.0, 1.0),
            _ => return,
        };
        let mut angle = count as f64 * GYRO_FINE_INCR_DEG / RAD_TO_DEG;
        if negative {
            angle = -angle;
        }
        // Torquing rotates the stable member about `axis` (SM coords)
        // before the existing SM→MCI reference.
        let dr: Rot<Sm, Sm> = Rot::from_axis_angle(axis, angle);
        self.sm_to_mci = dr.then(self.sm_to_mci);
    }
}

/// CDU: drives the three IMU gimbal counters toward the commanded gimbal
/// angles with fast PCDU/MCDU pulses, ≤ 64 per axis per tick, X→Y→Z order,
/// carrying the sub-pulse remainder in the emitted-count integers.
#[derive(Debug, Default, Clone)]
pub struct Cdu {
    emitted: [i64; 3],
}

const CDU_MAX_PER_TICK: i64 = 64;

impl Cdu {
    /// Emit this tick's CDU pulses toward `gimbals_deg`.
    pub fn step(&mut self, gimbals_deg: [f64; 3]) -> Vec<Packet> {
        let axes = [CduAxis::X, CduAxis::Y, CduAxis::Z];
        let mut out = Vec::new();
        for (i, axis) in axes.into_iter().enumerate() {
            let target = (gimbals_deg[i] / CDU_INCR_DEG).round() as i64;
            let delta = (target - self.emitted[i]).clamp(-CDU_MAX_PER_TICK, CDU_MAX_PER_TICK);
            let positive = delta > 0;
            for _ in 0..delta.abs() {
                out.push(cdu_pulse(axis, positive, true));
            }
            self.emitted[i] += delta;
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eagle_dynamics::constants::CDU_INCR_DEG;
    use eagle_dynamics::frames::retag;

    fn identity_sm() -> Rot<Sm, Mci> {
        retag(Rot::<Sm, Sm>::identity())
    }

    #[test]
    fn gimbals_zero_when_body_equals_sm() {
        let imu = Imu::new(identity_sm());
        let g = imu.gimbals_deg(&Rot::identity());
        assert!(g.iter().all(|a| a.abs() < 1e-12));
    }

    #[test]
    fn single_axis_rotation_hits_single_gimbal() {
        // X body → OGA (gimbal 0), Y → IGA (1), Z → MGA (2); each +10°.
        let imu = Imu::new(identity_sm());
        let axes = [
            V3::<Body>::new(1.0, 0.0, 0.0),
            V3::<Body>::new(0.0, 1.0, 0.0),
            V3::<Body>::new(0.0, 0.0, 1.0),
        ];
        for (hit, axis) in axes.into_iter().enumerate() {
            let att: Rot<Body, Mci> =
                retag(Rot::<Body, Body>::from_axis_angle(axis, 10f64.to_radians()));
            let g = imu.gimbals_deg(&att);
            assert!((g[hit] - 10.0).abs() < 1e-9, "gimbal {hit}: {g:?}");
            for (k, v) in g.iter().enumerate() {
                if k != hit {
                    assert!(v.abs() < 1e-9, "gimbal {k} should be ~0: {g:?}");
                }
            }
        }
    }

    #[test]
    fn cdu_budget_and_convergence() {
        let mut c = Cdu::default();
        // 5° step on X: 5 / (360/32768) ≈ 455 pulses → 8 ticks at 64/axis
        let mut sent = 0usize;
        for tick in 0..20 {
            let pk = c.step([5.0, 0.0, 0.0]);
            assert!(pk.len() <= 64 * 3, "budget");
            sent += pk.len();
            if pk.is_empty() {
                assert!(tick >= 7, "converged too fast?");
                break;
            }
        }
        assert_eq!(sent, (5.0 / CDU_INCR_DEG).round() as usize);
        // all packets are fast-mode PCDU on CDUX
        let mut c2 = Cdu::default();
        let first = &c2.step([5.0, 0.0, 0.0])[0];
        assert_eq!(*first, cdu_pulse(CduAxis::X, true, true));
    }

    #[test]
    fn coarse_align_shifts_gimbal_reference() {
        let mut imu = Imu::new(identity_sm());
        imu.apply_coarse(CduAxis::X, 100); // 100 × 0.043948°
        let g = imu.gimbals_deg(&Rot::identity());
        assert!(
            (g[0] - (-100.0 * COARSE_INCR_DEG)).abs() < 1e-9
                || (g[0] - 100.0 * COARSE_INCR_DEG).abs() < 1e-9
        );
    }

    #[test]
    fn gyro_torque_rotates_stable_member_by_count_increment() {
        let mut imu = Imu::new(identity_sm());
        // SELECT B set (bit12) → axis code 1 = X; 200 pulses, positive.
        let raw = (1 << 12) | 200;
        imu.apply_gyro(raw);
        // sm_to_mci rotated by 200 × GYRO_FINE_INCR about SM x.
        let v = imu.sm_to_mci().apply(V3::<Sm>::new(0.0, 1.0, 0.0));
        let expect = (200.0 * GYRO_FINE_INCR_DEG).to_radians();
        let angle = v.z.atan2(v.y); // rotation of ŷ toward ẑ about x
        assert!((angle - expect).abs() < 1e-9, "angle {angle} vs {expect}");
    }
}
