//! Differential test: the scalar reference engine (explicit deals,
//! explicit 45-card turn and 44-card river chance) and the vector flop
//! engine (range masks; 49 public turns enumerated at weight 1/45, then
//! 48 public rivers at 1/44 — the same per-deal distribution) must
//! converge to the same equilibrium on identical tiny spots. This pins
//! the two-stage chance weighting, the (turn, river) context indexing,
//! and the all-streets value computation at once.
//!
//! The game-value invariant is exploitability-budgeted, so it stays valid
//! even at partial convergence: two ε-equilibria of the same zero-sum
//! game have avg-vs-avg values within ε₁+ε₂ of each other.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::{TinyFlopTurnRiver, TinyFlopTurnRiverState};
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{CfrVariant, ChanceMode, FlopSolver, Game, ScalarCfr};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig, RaiseRule, StreetConfig};
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

/// Minimal abstraction keeps both engines tractable: the flop is the
/// only decision street (turn/river decisions are already pinned by the
/// turn+river differential); the two chance stages stay fully exercised.
/// Even so, every enumerated vector iteration touches all
/// 3 × 45 × 44 (line, turn, river) contexts at O(1326) each.
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

/// Game value to player 0 when both follow the scalar average strategy.
fn scalar_game_value_p0(
    game: &TinyFlopTurnRiver,
    solver: &ScalarCfr<TinyFlopTurnRiver>,
    state: &TinyFlopTurnRiverState,
) -> f64 {
    if game.is_terminal(state) {
        return game.payoff(state, 0);
    }
    if game.is_chance(state) {
        return game
            .chance_outcomes(state)
            .iter()
            .map(|(child, prob)| prob * scalar_game_value_p0(game, solver, child))
            .sum();
    }
    let na = game.num_actions(state);
    let key = game.infoset_key(state);
    let strat = solver.average_strategy(&key, na);
    (0..na)
        .map(|a| strat[a] * scalar_game_value_p0(game, solver, &game.next(state, a)))
        .sum()
}

#[test]
fn scalar_and_vector_agree_on_tiny_flop_spot() {
    let board = [c("2c"), c("7d"), c("9h")];
    // Player 0 = SB/IP; player 1 = BB/OOP. No card clashes between lists.
    let hands0 = vec![(c("Qc"), c("Tc")), (c("Ah"), c("Ad"))];
    let hands1 = vec![(c("Kh"), c("Qh")), (c("8s"), c("8d"))];
    // The game-value check is exploitability-budgeted, so partial
    // convergence keeps the test valid — these counts trade precision
    // for suite wall-time (~1.5 min release; the scalar engine's
    // string-keyed HashMap traversal dominates).
    let scalar_iters = 30;
    let vector_iters = 30;
    let variant = CfrVariant::cfr_plus_default();

    // --- Scalar reference ------------------------------------------------
    let tree_s = build_flop_tree(20 * BB, 90 * BB, &tiny_cfg());
    let game = TinyFlopTurnRiver::new(tree_s, board, [hands0.clone(), hands1.clone()]);
    let mut scalar = ScalarCfr::new(&game, variant);
    scalar.run(scalar_iters);
    let scalar_expl = exploitability(&game, &scalar);

    // --- Vector engine, exact enumeration ---------------------------------
    let tree_v = build_flop_tree(20 * BB, 90 * BB, &tiny_cfg());
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut vector = FlopSolver::new(tree_v, board, [r0, r1], variant, ChanceMode::Enumerate);
    vector.run(vector_iters);
    let vector_expl = vector.exploitability_bb();

    // --- 1. Both engines converge ----------------------------------------
    assert!(
        vector_expl.exploitability < 0.15,
        "vector exploitability {:.4}",
        vector_expl.exploitability
    );
    assert!(
        scalar_expl < 0.60,
        "scalar exploitability {scalar_expl:.4} — not converging"
    );

    // --- 2. Game-value invariant ------------------------------------------
    let v_scalar = scalar_game_value_p0(&game, &scalar, &game.root());
    let v_vector = vector.game_value_p0();
    let budget = scalar_expl + vector_expl.exploitability;
    eprintln!("game values: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})");
    assert!(
        (v_scalar - v_vector).abs() <= budget,
        "game values diverge: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})"
    );

    eprintln!(
        "flop differential OK: scalar expl {scalar_expl:.5}, vector expl {:.5}",
        vector_expl.exploitability
    );
}
