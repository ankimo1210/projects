//! Bit-identity baseline harness for the hu-perf changes (I1/I2/I5/I6).
//!
//! These changes are pure recompute-elimination: under CFR+ they must leave
//! exploitability and the converged average strategy BIT-IDENTICAL. Each test
//! below pins one solver configuration by asserting its exploitability against
//! a hard-coded literal (the pre-change value) and an integer "strategy
//! checksum" derived from the converged average strategy. A perf change that
//! is not bit-identical changes one of these and fails the test.
//!
//! The literals were captured from the pre-change code (commit before the
//! hu-perf edits) with `cargo test -p gto-hu --test test_perf_baseline
//! -- --nocapture`; the printed `EXACT` lines are the source of the
//! constants. Re-running after the perf edits must reproduce them exactly.

use gto_core::eval::parse_card;
use gto_hu::game::{Street, BB};
use gto_hu::ranges::{combo_index, uniform_excluding, Range, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, ChanceMode, FlopSolver, TurnRiverSolver, VectorRiverSolver};
use gto_hu::tree::{
    build_flop_tree, build_river_tree, build_turn_river_tree, FlopTreeConfig, RaiseRule,
    StreetConfig, TurnTreeConfig,
};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

/// Mix one f64 into a running 64-bit checksum (order-sensitive, exact:
/// uses the raw bit pattern so any change to any value is detected).
fn mix(acc: &mut u64, x: f64) {
    let bits = x.to_bits();
    *acc = acc.rotate_left(7) ^ bits.wrapping_mul(0x9E37_79B9_7F4A_7C15);
}

// ---- (a) VectorRiverSolver -------------------------------------------------

fn river_solver() -> VectorRiverSolver {
    let tree = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    VectorRiverSolver::new(tree, board, ranges, CfrVariant::cfr_plus_default())
}

fn river_checksum(s: &VectorRiverSolver) -> u64 {
    let mut acc = 0u64;
    for node_id in s.action_node_ids() {
        let actor = s.actor_at(node_id) as usize;
        for combo in 0..NUM_COMBOS {
            if s.ranges[actor].weights[combo] == 0.0 {
                continue;
            }
            for p in s.average_strategy(node_id, combo) {
                mix(&mut acc, p);
            }
        }
    }
    acc
}

#[test]
fn baseline_vector_river_cfr_plus_is_bit_identical() {
    let mut s = river_solver();
    s.run(200);
    let e = s.exploitability_bb().exploitability;
    let chk = river_checksum(&s);
    eprintln!("EXACT vector_river expl_bits={:#018x} checksum={:#018x}", e.to_bits(), chk);
    assert_eq!(e.to_bits(), 0x3fa574e9adcbd4e0, "vector river exploitability changed");
    assert_eq!(chk, 0xdad67033d6220a75, "vector river strategy checksum changed");
}

// ---- (b) TurnRiverSolver, enumerate ---------------------------------------

fn turn_cfg() -> TurnTreeConfig {
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

fn turn_board() -> [u8; 4] {
    [c("2c"), c("7d"), c("9h"), c("Jh")]
}

fn turn_solver(mode: ChanceMode) -> TurnRiverSolver {
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &turn_cfg());
    let b = turn_board();
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    TurnRiverSolver::new(tree, b, ranges, CfrVariant::cfr_plus_default(), mode)
}

fn turn_checksum(s: &TurnRiverSolver) -> u64 {
    let mut acc = 0u64;
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
                for p in s.average_strategy(node_id, ctx, combo) {
                    mix(&mut acc, p);
                }
            }
        }
    }
    acc
}

#[test]
fn baseline_turn_river_enumerate_cfr_plus_is_bit_identical() {
    let mut s = turn_solver(ChanceMode::Enumerate);
    s.run(40);
    let e = s.exploitability_bb().exploitability;
    let chk = turn_checksum(&s);
    eprintln!("EXACT turn_enum expl_bits={:#018x} checksum={:#018x}", e.to_bits(), chk);
    assert_eq!(e.to_bits(), 0x3fc6011161b816ae, "turn enumerate exploitability changed");
    assert_eq!(chk, 0x84eff9cbd94be77e, "turn enumerate strategy checksum changed");
}

// ---- (c) TurnRiverSolver, sampled -----------------------------------------

#[test]
fn baseline_turn_river_sampled_cfr_plus_is_bit_identical() {
    let mut s = turn_solver(ChanceMode::Sample { seed: 0xABCD_1234 });
    s.run(400);
    let e = s.exploitability_bb().exploitability;
    let chk = turn_checksum(&s);
    eprintln!("EXACT turn_sampled expl_bits={:#018x} checksum={:#018x}", e.to_bits(), chk);
    assert_eq!(e.to_bits(), 0x3ffeb2d493a341e0, "turn sampled exploitability changed");
    assert_eq!(chk, 0x2df956db29f93235, "turn sampled strategy checksum changed");
}

// ---- (d) FlopSolver, sampled ----------------------------------------------

fn flop_cfg() -> FlopTreeConfig {
    let simple = |pcts: Vec<u32>, raise: RaiseRule, mr: u8| StreetConfig {
        bet_pcts: pcts,
        allow_allin_bet: false,
        raise,
        max_raises: mr,
    };
    FlopTreeConfig {
        flop: simple(vec![50], RaiseRule::JamOnly, 1),
        turn: simple(vec![50], RaiseRule::None, 0),
        river: simple(vec![], RaiseRule::None, 0),
    }
}

fn flop_ranges() -> [Range; 2] {
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

fn flop_solver(mode: ChanceMode) -> FlopSolver {
    let tree = build_flop_tree(20 * BB, 90 * BB, &flop_cfg());
    let board = [c("2c"), c("7d"), c("9h")];
    FlopSolver::new(tree, board, flop_ranges(), CfrVariant::cfr_plus_default(), mode)
}

fn flop_checksum(s: &FlopSolver) -> u64 {
    let mut acc = 0u64;
    for node_id in s.action_node_ids() {
        let actor = s.actor_at(node_id) as usize;
        let street = s.tree.nodes[node_id].state.street;
        // Enumerate the contexts the node can be reached in.
        let ctxs: Vec<(Option<usize>, Option<usize>)> = match street {
            Street::Flop => vec![(None, None)],
            Street::Turn => (0..s.turns().len()).map(|t| (Some(t), None)).collect(),
            Street::River => {
                let mut v = Vec::new();
                for t in 0..s.turns().len() {
                    for r in 0..s.rivers(t).len() {
                        v.push((Some(t), Some(r)));
                    }
                }
                v
            }
            Street::Preflop => unreachable!(),
        };
        for (t, r) in ctxs {
            for combo in 0..NUM_COMBOS {
                if s.export_weight(actor, t, r, combo) == 0.0 {
                    continue;
                }
                for p in s.average_strategy(node_id, t, r, combo) {
                    mix(&mut acc, p);
                }
            }
        }
    }
    acc
}

#[test]
fn baseline_flop_sampled_cfr_plus_is_bit_identical() {
    let mut s = flop_solver(ChanceMode::Sample { seed: 0x55AA_0F0F });
    s.run(300);
    let e = s.exploitability_bb().exploitability;
    let chk = flop_checksum(&s);
    eprintln!("EXACT flop_sampled expl_bits={:#018x} checksum={:#018x}", e.to_bits(), chk);
    assert_eq!(e.to_bits(), 0x3ffb4ac39befb55e, "flop sampled exploitability changed");
    assert_eq!(chk, 0x32fdc9fbb7a89327, "flop sampled strategy checksum changed");
}
