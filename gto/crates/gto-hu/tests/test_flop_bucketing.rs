//! River strategy-space bucketing (bucketing design spec §6):
//! bucket-map invariants, budget-based differential vs the exact solver,
//! the abstraction-loss dial, and the bucketed dense-size formula.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{combo_index, Range, NUM_COMBOS};
use gto_hu::solver::{
    dense_table_bytes, dense_table_bytes_bucketed, CfrVariant, ChanceMode, FlopSolver,
    ShowdownTable,
};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig, RaiseRule, StreetConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

#[test]
fn bucket_map_is_monotone_tie_consistent_and_bounded() {
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let table = ShowdownTable::new(&board);
    let strengths = gto_core::eval::showdown_strengths(&board);
    for k in [4usize, 64, 128, 1326] {
        let buckets = table.strength_buckets(k);
        let mut ranked: Vec<usize> = (0..NUM_COMBOS).filter(|&i| strengths[i] > 0).collect();
        ranked.sort_by_key(|&i| strengths[i]);
        let mut prev_bucket = 0u16;
        let mut prev_strength = 0u16;
        for &i in &ranked {
            let b = buckets[i];
            assert!((b as usize) < k, "bucket {b} out of range for k={k}");
            assert!(b >= prev_bucket, "buckets must be monotone in strength");
            if strengths[i] == prev_strength {
                assert_eq!(b, prev_bucket, "equal strengths must share a bucket");
            }
            prev_bucket = b;
            prev_strength = strengths[i];
        }
        // Blocked combos (strength 0) sit at bucket 0 and are never used.
        let blocked = (0..NUM_COMBOS).find(|&i| strengths[i] == 0).unwrap();
        assert_eq!(buckets[blocked], 0);
    }
}

fn tiny_cfg() -> FlopTreeConfig {
    let simple = |pcts: Vec<u32>| StreetConfig {
        bet_pcts: pcts,
        allow_allin_bet: false,
        raise: RaiseRule::None,
        max_raises: 0,
    };
    // River decisions matter here: that is the bucketed street.
    FlopTreeConfig {
        flop: simple(vec![]),
        turn: simple(vec![]),
        river: simple(vec![100]),
    }
}

fn tiny_ranges() -> [Range; 2] {
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    r0.weights[combo_index(c("Qc"), c("Tc"))] = 1.0;
    r0.weights[combo_index(c("Ah"), c("Ad"))] = 1.0;
    r1.weights[combo_index(c("Kh"), c("Qh"))] = 1.0;
    r1.weights[combo_index(c("8s"), c("8d"))] = 1.0;
    [r0, r1]
}

fn build(buckets: usize) -> FlopSolver {
    let board = [c("2c"), c("7d"), c("9h")];
    let tree = build_flop_tree(20 * BB, 90 * BB, &tiny_cfg());
    FlopSolver::new_with_buckets(
        tree,
        board,
        tiny_ranges(),
        CfrVariant::cfr_plus_default(),
        ChanceMode::Enumerate,
        buckets,
    )
}

#[test]
fn bucketed_solver_matches_exact_within_expl_budget() {
    // K = 1326 exercises the REAL bucketed code path (maps, K-wide
    // slabs, row expansion — since the review fix, K > 0 never silently
    // falls back to exact). It is tier-injective: a live combo shares a
    // row only with combos of identical strength, and those contribute
    // zero weighted delta (out of range), so the bucketed run must land
    // on the exact solver's equilibrium up to strength-ties among live
    // hands. The absolute expl bound is the meaningful assertion — the
    // |Δvalue| ≤ joint-budget check holds for ANY two profiles of a
    // zero-sum game (review note) and is kept only as a sanity print.
    let mut exact = build(0);
    exact.run(60);
    let e_expl = exact.exploitability_bb();
    let e_val = exact.game_value_p0();

    let mut bucketed = build(1326);
    bucketed.run(60);
    let b_expl = bucketed.exploitability_bb();
    let b_val = bucketed.game_value_p0();

    assert!(e_expl.exploitability < 0.05, "exact {:.4}", e_expl.exploitability);
    assert!(
        b_expl.exploitability < 0.05,
        "tier-injective bucketing must converge like exact: {:.4}",
        b_expl.exploitability
    );
    assert!(
        (e_expl.exploitability - b_expl.exploitability).abs() < 0.02,
        "abstraction loss must be negligible at K=N: exact {:.4} vs bucketed {:.4}",
        e_expl.exploitability,
        b_expl.exploitability
    );
    assert!(
        (e_val - b_val).abs() < 0.05,
        "game values diverge: exact {e_val:.4} vs bucketed {b_val:.4}"
    );
    eprintln!(
        "bucketing differential OK: exact expl {:.5} val {e_val:.4} | K=1326 expl {:.5} val {b_val:.4}",
        e_expl.exploitability, b_expl.exploitability
    );
}

#[test]
fn bucketed_strategies_stay_normalized_and_uniform_when_untrained() {
    // Parent spec §10 "strategy sums to 1" on the K>0 path (review gap).
    let solver = build(64);
    let na = solver.tree.nodes[0].children.len();
    let s = solver.average_strategy(0, None, None, 0);
    assert_eq!(s.len(), na);
    for f in &s {
        assert!((f - 1.0 / na as f64).abs() < 1e-12, "untrained must be uniform");
    }
    let mut solver = solver;
    solver.run(3);
    // After a few iterations every exported distribution still sums to 1.
    for node_id in solver.action_node_ids().into_iter().take(6) {
        let (t, r) = match (
            solver.tree.nodes[node_id].state.street,
        ) {
            (gto_hu::game::Street::Flop,) => (None, None),
            (gto_hu::game::Street::Turn,) => (Some(0), None),
            (gto_hu::game::Street::River,) => (Some(0), Some(0)),
            _ => (None, None),
        };
        for combo in [0usize, 700, 1325] {
            let s = solver.average_strategy(node_id, t, r, combo);
            let total: f64 = s.iter().sum();
            assert!(
                (total - 1.0).abs() < 1e-9,
                "strategy must sum to 1 at node {node_id} combo {combo}: {total}"
            );
        }
    }
}

#[test]
fn coarser_buckets_cost_more_exploitability() {
    // Single seed/config: guards the dial's direction, not a theorem.
    let mut coarse = build(2);
    coarse.run(80);
    let coarse_expl = coarse.exploitability_bb().exploitability;

    let mut fine = build(256);
    fine.run(80);
    let fine_expl = fine.exploitability_bb().exploitability;

    eprintln!("expl: K=2 {coarse_expl:.4} vs K=256 {fine_expl:.4}");
    assert!(
        fine_expl < coarse_expl,
        "finer buckets must be less exploitable here: K=2 {coarse_expl:.4} vs K=256 {fine_expl:.4}"
    );
}

#[test]
fn bucketed_dense_size_shrinks_river_rows_only() {
    let tree = build_flop_tree(20 * BB, 90 * BB, &FlopTreeConfig::srp());
    let exact = dense_table_bytes(&tree);
    let k = 128usize;
    let bucketed = dense_table_bytes_bucketed(&tree, k);
    assert!(bucketed < exact);
    // Reconstruct from the formula: non-river share is unchanged.
    use gto_hu::game::Street;
    use gto_hu::tree::NodeKind;
    let mut non_river = 0usize;
    let mut river_exact = 0usize;
    for n in &tree.nodes {
        if let NodeKind::Action { .. } = n.kind {
            let cells = 2 * 8 * n.children.len();
            match n.state.street {
                Street::River => river_exact += cells * 49 * 48 * NUM_COMBOS,
                Street::Turn => non_river += cells * 49 * NUM_COMBOS,
                _ => non_river += cells * NUM_COMBOS,
            }
        }
    }
    assert_eq!(exact, non_river + river_exact);
    assert_eq!(
        bucketed,
        non_river + river_exact / NUM_COMBOS * k,
        "river rows must scale by K/N exactly"
    );
}
