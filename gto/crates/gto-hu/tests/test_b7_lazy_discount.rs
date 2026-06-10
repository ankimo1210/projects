//! B7: under sampled chance the lazy DCFR discount must be cumulative over
//! skipped iterations, otherwise early iterations are over-weighted in the
//! average strategy versus enumerate mode.
//!
//! This test uses DCFR (where the strategy γ-discount and the regret
//! α/β-discount are both non-trivial functions of the iteration). The CFR+
//! default is vacuous for B7 (both discounts are 1.0) and its bit-identity
//! under the fix is pinned by `test_perf_baseline`.
//!
//! Metric: the per-(node, ctx, combo, action) L1 distance between the
//! sampled and the exact (enumerate) DCFR average strategy, AVERAGED over
//! many sampling seeds. Public-chance sampling adds zero-mean per-trajectory
//! variance that cancels under the seed-average, leaving the systematic B7
//! bias: under-discounting over-weights early, under-trained iterations, so
//! the seed-mean sampled average strategy sits further from the exact one.
//! Small explicit ranges keep every live infoset well-trained per iteration
//! so the residual under-training noise stays well below the B7 bias.

use gto_core::eval::parse_card;
use gto_hu::game::{Street, BB};
use gto_hu::ranges::{combo_index, Range, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn board() -> [u8; 4] {
    [c("2c"), c("7d"), c("9h"), c("Jh")]
}

fn small_ranges() -> [Range; 2] {
    let hands0 = [
        (c("Qc"), c("Tc")),
        (c("Ah"), c("Ad")),
        (c("6s"), c("5s")),
        (c("Kd"), c("Kh")),
    ];
    let hands1 = [
        (c("Kh"), c("Qh")),
        (c("8s"), c("8d")),
        (c("As"), c("Js")),
        (c("7c"), c("6c")),
    ];
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    [r0, r1]
}

fn cfg() -> TurnTreeConfig {
    TurnTreeConfig {
        turn: StreetConfig {
            bet_pcts: vec![50],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
        river: StreetConfig {
            bet_pcts: vec![100],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    }
}

fn solver(mode: ChanceMode) -> TurnRiverSolver {
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &cfg());
    TurnRiverSolver::new(tree, board(), small_ranges(), CfrVariant::dcfr_default(), mode)
}

/// Flattened per-(node, ctx, combo) average strategy over all live infosets.
fn avg_strategy_vector(s: &TurnRiverSolver) -> Vec<f64> {
    let mut out = Vec::new();
    for node_id in s.action_node_ids() {
        let actor = s.actor_at(node_id) as usize;
        let ctxs: Vec<Option<usize>> = if s.tree.nodes[node_id].state.street == Street::River {
            (0..s.rivers().len()).map(Some).collect()
        } else {
            vec![None]
        };
        for ctx in ctxs {
            for combo in 0..NUM_COMBOS {
                if s.export_weight(actor, ctx, combo) == 0.0 {
                    continue;
                }
                out.extend(s.average_strategy(node_id, ctx, combo));
            }
        }
    }
    out
}

#[test]
fn dcfr_sampled_average_strategy_tracks_enumerate() {
    let iters = 1500u32;
    let n_seeds = 32u64;

    let mut enumerate = solver(ChanceMode::Enumerate);
    enumerate.run(iters);
    let target = avg_strategy_vector(&enumerate);

    let mut mean = vec![0.0f64; target.len()];
    for k in 0..n_seeds {
        let mut s = solver(ChanceMode::Sample {
            seed: 0xB7_0000 ^ (k.wrapping_mul(0x9E37_79B9)),
        });
        s.run(iters);
        for (m, x) in mean.iter_mut().zip(&avg_strategy_vector(&s)) {
            *m += x / n_seeds as f64;
        }
    }
    let dist: f64 = mean
        .iter()
        .zip(&target)
        .map(|(m, t)| (m - t).abs())
        .sum::<f64>()
        / target.len() as f64;
    eprintln!("DCFR seed-mean sampled-vs-enumerate L1 = {dist:.6} (iters={iters}, seeds={n_seeds})");

    // Calibration (release, deterministic — fixed seeds; measured by
    // reverting ONLY the B7 hunks, since I1/I2/I5 are bit-identical and do
    // not move this number):
    //   pre-fix  (current-iter discount only): seed-mean L1 = 0.089708
    //   post-fix (cumulative lazy discount)  : seed-mean L1 = 0.058465
    // The cumulative lazy discount cuts the seed-mean distance from the exact
    // DCFR average strategy by ~35%. The bound below fails on the pre-fix
    // code (0.0897 > 0.072) and holds on the fixed code (0.0585 < 0.072).
    assert!(
        dist < 0.072,
        "DCFR seed-mean sampled average strategy too far from enumerate \
         (B7 under-discounting): L1 {dist:.6} (pre-fix 0.0897, post-fix 0.0585)"
    );
}
