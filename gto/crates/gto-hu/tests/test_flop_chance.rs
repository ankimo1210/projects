//! Chance machinery of the flop solver: seeded determinism, lazy table
//! allocation bounds, and sampled-training convergence to the same
//! equilibrium as exact enumeration (game values within the joint
//! exploitability budget — exploitability itself is always exact).

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{dense_table_bytes, CfrVariant, ChanceMode, FlopSolver};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig, RaiseRule, StreetConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn tiny_cfg() -> FlopTreeConfig {
    let simple = |pcts: Vec<u32>| StreetConfig {
        bet_pcts: pcts,
        allow_allin_bet: false,
        raise: RaiseRule::None,
        max_raises: 0,
    };
    FlopTreeConfig {
        flop: simple(vec![50]),
        turn: simple(vec![]),
        river: simple(vec![]),
    }
}

fn tiny_ranges() -> [Range; 2] {
    let hands0 = [(c("Qc"), c("Tc")), (c("Ah"), c("Ad"))];
    let hands1 = [(c("Kh"), c("Qh")), (c("8s"), c("8d"))];
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

fn board() -> [u8; 3] {
    [c("2c"), c("7d"), c("9h")]
}

fn build_solver(mode: ChanceMode) -> FlopSolver {
    let tree = build_flop_tree(20 * BB, 90 * BB, &tiny_cfg());
    FlopSolver::new(
        tree,
        board(),
        tiny_ranges(),
        CfrVariant::cfr_plus_default(),
        mode,
    )
}

#[test]
fn same_seed_is_deterministic() {
    let mut a = build_solver(ChanceMode::Sample { seed: 7 });
    let mut b = build_solver(ChanceMode::Sample { seed: 7 });
    a.run(200);
    b.run(200);
    let (ea, eb) = (a.exploitability_bb(), b.exploitability_bb());
    assert_eq!(ea.exploitability, eb.exploitability);
    assert_eq!(a.game_value_p0(), b.game_value_p0());
}

#[test]
fn lazy_tables_grow_only_when_visited_and_stay_under_dense() {
    let solver = build_solver(ChanceMode::Sample { seed: 1 });
    let dense = dense_table_bytes(&solver.tree);
    assert!(dense > 0);
    assert_eq!(solver.table_bytes(), 0, "no slabs before training");

    let mut solver = solver;
    solver.run(3);
    let after_few = solver.table_bytes();
    assert!(after_few > 0, "training must allocate visited slabs");
    assert!(
        after_few < dense,
        "3 sampled iterations cannot have visited every (turn, river) context: {after_few} vs dense {dense}"
    );
}

#[test]
fn enumerate_fills_exactly_the_dense_tables() {
    let mut solver = build_solver(ChanceMode::Enumerate);
    let dense = dense_table_bytes(&solver.tree);
    solver.run(1);
    assert_eq!(
        solver.table_bytes(),
        dense,
        "one enumerated iteration visits every context"
    );
}

#[test]
fn sampled_training_matches_enumerated_equilibrium() {
    let mut enumerated = build_solver(ChanceMode::Enumerate);
    enumerated.run(40);
    let e_expl = enumerated.exploitability_bb();
    let e_val = enumerated.game_value_p0();

    let mut sampled = build_solver(ChanceMode::Sample { seed: 42 });
    sampled.run(2_000);
    let s_expl = sampled.exploitability_bb();
    let s_val = sampled.game_value_p0();

    assert!(
        e_expl.exploitability < 0.15,
        "enumerated expl {:.4}",
        e_expl.exploitability
    );
    assert!(
        s_expl.exploitability < 0.15,
        "sampled expl {:.4} — public chance sampling not converging",
        s_expl.exploitability
    );
    // Two ε-equilibria of the same game: values within the joint budget.
    let budget = e_expl.exploitability + s_expl.exploitability;
    assert!(
        (e_val - s_val).abs() <= budget,
        "game values diverge: enumerated {e_val:.4} vs sampled {s_val:.4} (budget {budget:.4})"
    );
    eprintln!(
        "chance OK: enum expl {:.5} val {e_val:.4} | sampled expl {:.5} val {s_val:.4}",
        e_expl.exploitability, s_expl.exploitability
    );
}
