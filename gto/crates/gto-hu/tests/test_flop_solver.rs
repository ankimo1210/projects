//! Flop solver behaviour on a real board with a small but non-trivial
//! abstraction: convergence (exact exploitability decreases), showdown
//! table sharing across mirrored (turn, river) contexts, and export
//! weights masking combos that hold context cards.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{CfrVariant, ChanceMode, FlopSolver};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig, RaiseRule, StreetConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn small_cfg() -> FlopTreeConfig {
    let simple = |pcts: Vec<u32>, raise: RaiseRule, mr: u8| StreetConfig {
        bet_pcts: pcts,
        allow_allin_bet: false,
        raise,
        max_raises: mr,
    };
    // River is check-only here to keep the sampled-convergence test under
    // a minute; river-decision training is covered by
    // `river_decisions_converge_under_enumeration` below.
    FlopTreeConfig {
        flop: simple(vec![50], RaiseRule::JamOnly, 1),
        turn: simple(vec![50], RaiseRule::None, 0),
        river: simple(vec![], RaiseRule::None, 0),
    }
}

fn small_ranges() -> [Range; 2] {
    // A handful of combos each, enough for mixed strategies.
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

#[test]
fn exploitability_decreases_with_sampled_training() {
    // Sampled mode = turn sampled, river enumerated; exploitability is
    // always exact (both stages enumerated in the best response).
    let board = [c("2c"), c("7d"), c("9h")];
    let tree = build_flop_tree(20 * BB, 90 * BB, &small_cfg());
    let mut solver = FlopSolver::new(
        tree,
        board,
        small_ranges(),
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed: 11 },
    );
    solver.run(200);
    let early = solver.exploitability_bb().exploitability;
    solver.run(3_800);
    let late = solver.exploitability_bb().exploitability;
    eprintln!("expl: 200 iters {early:.4} → 4k iters {late:.4}");
    assert!(
        late < early * 0.5,
        "exploitability must drop substantially: {early:.4} → {late:.4}"
    );
    // Measured trajectory on this config/seed: 2.48 bb @ 200 → 0.27 bb @ 4k
    // (each turn context gets ~80 sampled visits at 4k). The bound guards
    // regressions, not final convergence — longer runs keep improving.
    assert!(late < 0.35, "not converging: {late:.4}");
}

#[test]
fn river_decisions_converge_under_enumeration() {
    // Flop and turn are check-only so every iteration trains the river
    // slabs through BOTH enumerated chance stages.
    let simple = |pcts: Vec<u32>| StreetConfig {
        bet_pcts: pcts,
        allow_allin_bet: false,
        raise: RaiseRule::None,
        max_raises: 0,
    };
    let cfg = FlopTreeConfig {
        flop: simple(vec![]),
        turn: simple(vec![]),
        river: simple(vec![100]),
    };
    let board = [c("2c"), c("7d"), c("9h")];
    let tree = build_flop_tree(20 * BB, 90 * BB, &cfg);
    // Two combos per side keep the enumerated iterations affordable.
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    r0.weights[combo_index(c("Qc"), c("Tc"))] = 1.0;
    r0.weights[combo_index(c("Ah"), c("Ad"))] = 1.0;
    r1.weights[combo_index(c("Kh"), c("Qh"))] = 1.0;
    r1.weights[combo_index(c("8s"), c("8d"))] = 1.0;
    let mut solver = FlopSolver::new(
        tree,
        board,
        [r0, r1],
        CfrVariant::cfr_plus_default(),
        ChanceMode::Enumerate,
    );
    solver.run(60);
    let expl = solver.exploitability_bb().exploitability;
    eprintln!("river-decision expl after 60 enumerated iters: {expl:.4}");
    assert!(expl < 0.05, "river decisions not converging: {expl:.4}");
}

#[test]
fn export_weight_masks_turn_and_river_blockers() {
    let board = [c("2c"), c("7d"), c("9h")];
    let tree = build_flop_tree(20 * BB, 90 * BB, &small_cfg());
    let solver = FlopSolver::new(
        tree,
        board,
        small_ranges(),
        CfrVariant::cfr_plus_default(),
        ChanceMode::Enumerate,
    );
    let combo = combo_index(c("Kh"), c("Qh"));
    // Find the turn ctx whose card is Kh: combo must be masked there.
    let t_kh = solver.turns().iter().position(|&t| t == c("Kh")).unwrap();
    assert_eq!(solver.export_weight(1, Some(t_kh), None, combo), 0.0);
    // On a neutral turn the combo keeps its weight…
    let t_3c = solver.turns().iter().position(|&t| t == c("3c")).unwrap();
    assert_eq!(solver.export_weight(1, Some(t_3c), None, combo), 1.0);
    // …but is masked again when the river is Qh.
    let r_qh = solver
        .rivers(t_3c)
        .iter()
        .position(|&r| r == c("Qh"))
        .unwrap();
    assert_eq!(solver.export_weight(1, Some(t_3c), Some(r_qh), combo), 0.0);
}

#[test]
fn average_strategy_is_uniform_on_unvisited_contexts() {
    let board = [c("2c"), c("7d"), c("9h")];
    let tree = build_flop_tree(20 * BB, 90 * BB, &small_cfg());
    let solver = FlopSolver::new(
        tree,
        board,
        small_ranges(),
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed: 3 },
    );
    // Untrained: every strategy must be a valid uniform distribution.
    let root_na = solver.tree.nodes[0].children.len();
    let s = solver.average_strategy(0, None, None, 0);
    assert_eq!(s.len(), root_na);
    for f in &s {
        assert!((f - 1.0 / root_na as f64).abs() < 1e-12);
    }
}
