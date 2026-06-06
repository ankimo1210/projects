//! Chance-duplication invariance: inserting k payoff-irrelevant, unseen
//! chance outcomes at the root multiplies each infoset's history count by k
//! but must not change the game. Per-visit (rather than per-iteration)
//! discounting breaks this; this test pins the per-iteration semantics.

use gto_hu::solver::{CfrVariant, Game, ScalarCfr};

/// Zero-sum matrix game A=[[3,-1],[-2,1]] (payoff to P0), encoded
/// sequentially with P1 unable to see P0's move. Equilibrium:
/// x*=(3/7,4/7), y*=(2/7,5/7), value 1/7. A root chance node with `dup`
/// identical outcomes pads history counts without affecting payoffs.
struct DupMatrix {
    dup: usize,
}

#[derive(Clone)]
struct S {
    chance_done: bool,
    p0: Option<usize>,
    p1: Option<usize>,
}

impl Game for DupMatrix {
    type State = S;
    fn root(&self) -> S {
        S { chance_done: false, p0: None, p1: None }
    }
    fn is_terminal(&self, s: &S) -> bool {
        s.p0.is_some() && s.p1.is_some()
    }
    fn payoff(&self, s: &S, player: usize) -> f64 {
        const A: [[f64; 2]; 2] = [[3.0, -1.0], [-2.0, 1.0]];
        let v = A[s.p0.unwrap()][s.p1.unwrap()];
        if player == 0 { v } else { -v }
    }
    fn is_chance(&self, s: &S) -> bool {
        !s.chance_done
    }
    fn chance_outcomes(&self, s: &S) -> Vec<(S, f64)> {
        let p = 1.0 / self.dup as f64;
        (0..self.dup)
            .map(|_| (S { chance_done: true, ..s.clone() }, p))
            .collect()
    }
    fn player(&self, s: &S) -> usize {
        if s.p0.is_none() { 0 } else { 1 }
    }
    fn num_actions(&self, _s: &S) -> usize {
        2
    }
    fn next(&self, s: &S, a: usize) -> S {
        let mut ns = s.clone();
        if ns.p0.is_none() { ns.p0 = Some(a) } else { ns.p1 = Some(a) }
        ns
    }
    fn infoset_key(&self, s: &S) -> String {
        // Neither player sees the chance outcome or the other's move.
        if s.p0.is_none() { "P0".into() } else { "P1".into() }
    }
}

fn solved_strategy(dup: usize, variant: CfrVariant, iters: u32) -> (Vec<f64>, Vec<f64>) {
    let g = DupMatrix { dup };
    let mut cfr = ScalarCfr::new(&g, variant);
    cfr.run(iters);
    (cfr.average_strategy("P0", 2), cfr.average_strategy("P1", 2))
}

#[test]
fn dcfr_converges_to_known_matrix_equilibrium() {
    let (x, y) = solved_strategy(1, CfrVariant::dcfr_default(), 10_000);
    assert!((x[0] - 3.0 / 7.0).abs() < 0.02, "x0={} want 3/7", x[0]);
    assert!((y[0] - 2.0 / 7.0).abs() < 0.02, "y0={} want 2/7", y[0]);
}

#[test]
fn dcfr_is_invariant_to_chance_duplication() {
    let (x1, y1) = solved_strategy(1, CfrVariant::dcfr_default(), 2_000);
    let (x64, y64) = solved_strategy(64, CfrVariant::dcfr_default(), 2_000);
    // Intra-iteration strategy recomputation makes duplicates not bit-identical;
    // bounded drift is acceptable — the per-visit-DISCOUNT bug produced
    // order-of-magnitude divergence. Tolerance 0.02 distinguishes correct
    // semantics from the buggy per-visit case.
    assert!((x1[0] - x64[0]).abs() < 0.02, "x: {} vs {}", x1[0], x64[0]);
    assert!((y1[0] - y64[0]).abs() < 0.02, "y: {} vs {}", y1[0], y64[0]);
}

#[test]
fn cfr_plus_is_invariant_to_chance_duplication() {
    let (x1, _) = solved_strategy(1, CfrVariant::cfr_plus_default(), 2_000);
    let (x64, _) = solved_strategy(64, CfrVariant::cfr_plus_default(), 2_000);
    // CFR+ has no discounting so invariance is tighter; 0.02 is conservative.
    assert!((x1[0] - x64[0]).abs() < 0.02, "x: {} vs {}", x1[0], x64[0]);
}
