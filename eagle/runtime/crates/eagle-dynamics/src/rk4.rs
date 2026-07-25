//! Fixed-step classic RK4 over the LM rigid-body state (spec §4: RK4,
//! fixed 10 ms, fixed k1..k4 evaluation order). Quaternion components are
//! integrated linearly and the attitude is normalized exactly once, at the
//! end of each step; fuel is clamped non-negative after the step.
use crate::frames::{qdot, Body, Mci, Rot, V3};
use crate::state::{Derivs, LmState};

/// State time-derivative: everything advances linearly, including the four
/// quaternion components (`dq`), which are re-normalized only once per step.
struct Rates {
    dpos: V3<Mci>,
    dvel: V3<Mci>,
    dq: [f64; 4],
    domega: V3<Body>,
    dmass: f64,
    dfuel_dps: f64,
    dfuel_rcs: f64,
}

fn eval(s: &LmState, f: &impl Fn(&LmState) -> Derivs) -> Rates {
    let d = f(s);
    Rates {
        dpos: s.vel,
        dvel: d.acc,
        dq: qdot(s.att.raw(), s.omega),
        domega: d.alpha,
        dmass: d.mdot_total,
        dfuel_dps: d.mdot_dps,
        dfuel_rcs: d.mdot_rcs,
    }
}

/// `s + k·dt` as a fresh state — the attitude is summed component-wise and
/// left un-normalized (RK4 intermediate stage).
fn advance(s: &LmState, k: &Rates, dt: f64) -> LmState {
    let q = s.att.raw();
    let att = Rot::from_raw_unnormalized([
        q[0] + k.dq[0] * dt,
        q[1] + k.dq[1] * dt,
        q[2] + k.dq[2] * dt,
        q[3] + k.dq[3] * dt,
    ]);
    LmState {
        t: s.t,
        pos: s.pos + k.dpos.scale(dt),
        vel: s.vel + k.dvel.scale(dt),
        att,
        omega: s.omega + k.domega.scale(dt),
        mass_kg: s.mass_kg + k.dmass * dt,
        fuel_dps_kg: s.fuel_dps_kg + k.dfuel_dps * dt,
        fuel_rcs_kg: s.fuel_rcs_kg + k.dfuel_rcs * dt,
    }
}

/// Weighted Simpson combine: `s + dt/6·(k1 + 2k2 + 2k3 + k4)`.
fn combine(s: &LmState, k: &[Rates; 4], dt: f64) -> LmState {
    let w = dt / 6.0;
    let sum = |a: f64, b: f64, c: f64, d: f64| a + 2.0 * b + 2.0 * c + d;
    let vsum = |g: &dyn Fn(&Rates) -> V3<Mci>| -> V3<Mci> {
        g(&k[0]) + g(&k[1]).scale(2.0) + g(&k[2]).scale(2.0) + g(&k[3])
    };
    let bsum = |g: &dyn Fn(&Rates) -> V3<Body>| -> V3<Body> {
        g(&k[0]) + g(&k[1]).scale(2.0) + g(&k[2]).scale(2.0) + g(&k[3])
    };
    let q = s.att.raw();
    let mut qout = q;
    for (i, qo) in qout.iter_mut().enumerate() {
        *qo += w * sum(k[0].dq[i], k[1].dq[i], k[2].dq[i], k[3].dq[i]);
    }
    LmState {
        t: s.t,
        pos: s.pos + vsum(&|r| r.dpos).scale(w),
        vel: s.vel + vsum(&|r| r.dvel).scale(w),
        att: Rot::from_raw_unnormalized(qout),
        omega: s.omega + bsum(&|r| r.domega).scale(w),
        mass_kg: s.mass_kg + w * sum(k[0].dmass, k[1].dmass, k[2].dmass, k[3].dmass),
        fuel_dps_kg: s.fuel_dps_kg
            + w * sum(
                k[0].dfuel_dps,
                k[1].dfuel_dps,
                k[2].dfuel_dps,
                k[3].dfuel_dps,
            ),
        fuel_rcs_kg: s.fuel_rcs_kg
            + w * sum(
                k[0].dfuel_rcs,
                k[1].dfuel_rcs,
                k[2].dfuel_rcs,
                k[3].dfuel_rcs,
            ),
    }
}

/// One classic RK4 step of `dt` seconds under force model `f`. Fixed
/// evaluation order k1..k4; attitude normalized once and fuel clamped
/// non-negative at the end.
pub fn step_rk4(s: &LmState, f: &impl Fn(&LmState) -> Derivs, dt: f64) -> LmState {
    let k1 = eval(s, f);
    let k2 = eval(&advance(s, &k1, dt / 2.0), f);
    let k3 = eval(&advance(s, &k2, dt / 2.0), f);
    let k4 = eval(&advance(s, &k3, dt), f);
    let mut out = combine(s, &[k1, k2, k3, k4], dt);
    out.att = out.att.normalize();
    out.fuel_dps_kg = out.fuel_dps_kg.max(0.0);
    out.fuel_rcs_kg = out.fuel_rcs_kg.max(0.0);
    out.t = s.t + dt;
    out
}

#[cfg(test)]
mod tests {
    use crate::constants::{DT, MU_MOON};
    use crate::frames::{Rot, V3};
    use crate::rk4::step_rk4;
    use crate::state::{gravity, Derivs, LmState};
    use crate::testutil::hover_state;

    #[test]
    fn circular_orbit_energy_stable() {
        let r0 = 1_837_400.0; // 100 km altitude
        let v0 = (MU_MOON / r0).sqrt();
        let mut s = LmState {
            t: 0.0,
            pos: V3::new(r0, 0.0, 0.0),
            vel: V3::new(0.0, v0, 0.0),
            att: Rot::identity(),
            omega: V3::zero(),
            mass_kg: 9000.0,
            fuel_dps_kg: 2000.0,
            fuel_rcs_kg: 150.0,
        };
        let f = |s: &LmState| Derivs {
            acc: gravity(s.pos),
            alpha: V3::zero(),
            mdot_total: 0.0,
            mdot_dps: 0.0,
            mdot_rcs: 0.0,
        };
        let e = |s: &LmState| 0.5 * s.vel.dot(s.vel) - MU_MOON / s.pos.norm();
        let e0 = e(&s);
        for _ in 0..6000 {
            s = step_rk4(&s, &f, DT);
        } // 60 s
        assert!(((e(&s) - e0) / e0).abs() < 1e-10, "energy drift");
        assert!((s.pos.norm() - r0).abs() / r0 < 1e-6, "radius drift");
    }

    #[test]
    fn rk4_fourth_order_convergence() {
        // free rotation about a principal axis has analytic solution; halving dt
        // must shrink attitude error by ~2^4 (accept ≥ 8× to be robust)
        let s0 = LmState {
            omega: V3::new(0.0, 0.0, 0.5),
            ..hover_state()
        };
        let f = |_: &LmState| Derivs {
            acc: V3::zero(),
            alpha: V3::zero(),
            mdot_total: 0.0,
            mdot_dps: 0.0,
            mdot_rcs: 0.0,
        };
        let run = |dt: f64| {
            let mut s = s0.clone();
            let n = (10.0 / dt) as usize;
            for _ in 0..n {
                s = step_rk4(&s, &f, dt);
            }
            // analytic: rotation angle 0.5 rad/s * 10 s about z
            let v = s.att.apply(V3::<crate::frames::Body>::new(1.0, 0.0, 0.0));
            let expect = 5.0f64;
            ((v.y.atan2(v.x) - expect).sin()).abs() // angle error, wrap-safe
        };
        let (e1, e2) = (run(0.02), run(0.01));
        assert!(e1 / e2 > 8.0, "convergence order too low: {e1} / {e2}");
    }

    #[test]
    fn quaternion_stays_normalized_and_fuel_clamps() {
        let mut s = hover_state();
        s.omega = V3::new(0.3, -0.2, 0.1);
        s.fuel_dps_kg = 0.001;
        let f = |_: &LmState| Derivs {
            acc: V3::zero(),
            alpha: V3::new(0.01, 0.0, 0.0),
            mdot_total: -1.0,
            mdot_dps: -1.0,
            mdot_rcs: 0.0,
        };
        for _ in 0..1000 {
            s = step_rk4(&s, &f, DT);
        }
        let n: f64 = s.att.raw().iter().map(|v| v * v).sum::<f64>().sqrt();
        assert!((n - 1.0).abs() < 1e-12);
        assert_eq!(s.fuel_dps_kg, 0.0); // clamped, never negative
    }

    #[test]
    fn determinism_bit_exact() {
        let f = |s: &LmState| Derivs {
            acc: gravity(s.pos),
            alpha: V3::zero(),
            mdot_total: 0.0,
            mdot_dps: 0.0,
            mdot_rcs: 0.0,
        };
        let run = || {
            let mut s = hover_state();
            for _ in 0..500 {
                s = step_rk4(&s, &f, DT);
            }
            s
        };
        let (a, b) = (run(), run());
        assert_eq!(a.pos, b.pos);
        assert_eq!(a.att.raw(), b.att.raw());
    }
}
