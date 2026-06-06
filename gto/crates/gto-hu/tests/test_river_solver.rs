use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{combo_index, uniform_excluding, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, StreetConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn board() -> [u8; 5] {
    [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")]
}

fn uniform_solver(variant: CfrVariant) -> VectorRiverSolver {
    let tree = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let b = board();
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    VectorRiverSolver::new(tree, b, ranges, variant)
}

#[test]
fn strategies_sum_to_one_for_active_combos() {
    let mut s = uniform_solver(CfrVariant::cfr_plus_default());
    s.run(50);
    for node_id in s.action_node_ids() {
        for combo in 0..NUM_COMBOS {
            if s.ranges[s.actor_at(node_id) as usize].weights[combo] == 0.0 {
                continue;
            }
            let strat = s.average_strategy(node_id, combo);
            let sum: f64 = strat.iter().sum();
            assert!(
                (sum - 1.0).abs() < 1e-9,
                "node {node_id} combo {combo}: strategy sums to {sum}"
            );
        }
    }
}

#[test]
fn exploitability_decreases_with_iterations() {
    let mut s = uniform_solver(CfrVariant::cfr_plus_default());
    s.run(20);
    let e1 = s.exploitability_bb();
    s.run(480);
    let e2 = s.exploitability_bb();
    eprintln!(
        "exploitability: {:.4} bb → {:.4} bb",
        e1.exploitability, e2.exploitability
    );
    assert!(e1.exploitability >= -1e-9 && e2.exploitability >= -1e-9);
    assert!(
        e2.exploitability < e1.exploitability,
        "exploitability must fall: {:.4} → {:.4}",
        e1.exploitability,
        e2.exploitability
    );
    assert!(
        e2.exploitability < 0.30,
        "after 500 iters: {:.4} bb",
        e2.exploitability
    );
}

#[test]
fn nuts_never_folds_to_a_bet() {
    // QT (nut straight) facing the root 15bb bet must never fold.
    let mut s = uniform_solver(CfrVariant::cfr_plus_default());
    s.run(300);
    let qt = combo_index(c("Qc"), c("Tc"));
    // Root child 1 = bet 15bb → IP response node.
    let resp = s.tree.nodes[0].children[1].1;
    let strat = s.average_strategy(resp, qt);
    eprintln!("QT fold freq vs bet = {}", strat[0]);
    assert!(
        strat[0] < 0.01,
        "QT fold freq vs bet = {} (must be ~0)",
        strat[0]
    );
}

#[test]
fn blocked_combos_keep_zero_reach() {
    let s = uniform_solver(CfrVariant::cfr_plus_default());
    let kd_combo = combo_index(c("Kd"), c("Ks"));
    assert_eq!(s.ranges[0].weights[kd_combo], 0.0);
    assert_eq!(s.ranges[1].weights[kd_combo], 0.0);
}
