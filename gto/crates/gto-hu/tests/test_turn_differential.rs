//! Differential test: the scalar reference engine (explicit deals, explicit
//! 44-card river chance) and the vector turn+river engine (range masks;
//! all 48 public river cards enumerated, weight 1/44 per surviving
//! non-blocked combo — the same per-deal distribution) must converge to
//! the same equilibrium on identical tiny spots. This pins the chance
//! weighting, the river-card masking, and the all-streets value
//! computation at once.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::{TinyTurnRiver, TinyTurnRiverState};
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{CfrVariant, ChanceMode, Game, ScalarCfr, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

/// Minimal abstraction keeps the scalar side tractable.
fn tiny_cfg() -> TurnTreeConfig {
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

/// Game value to player 0 when both follow the scalar average strategy.
fn scalar_game_value_p0(
    game: &TinyTurnRiver,
    solver: &ScalarCfr<TinyTurnRiver>,
    state: &TinyTurnRiverState,
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
fn scalar_and_vector_agree_on_tiny_turn_river_spot() {
    let board = [c("2c"), c("7d"), c("9h"), c("Jh")];
    // Player 0 = SB/IP; player 1 = BB/OOP. No card clashes between lists.
    let hands0 = vec![(c("Qc"), c("Tc")), (c("Ah"), c("Ad"))];
    let hands1 = vec![(c("Kh"), c("Qh")), (c("8s"), c("8d"))];
    // The scalar engine converges much slower per iteration (off-path
    // infosets learn at a rate proportional to their reach — cf. the river
    // differential): measured expl 0.128 @ 2k, 0.101 @ 3.5k, 0.082 @ 5k.
    // The vector engine updates every combo per iteration: expl 0.008 @ 600.
    let scalar_iters = 5_000;
    let vector_iters = 600;
    let variant = CfrVariant::cfr_plus_default();

    // --- Scalar reference ------------------------------------------------
    let tree_s = build_turn_river_tree(20 * BB, 90 * BB, &tiny_cfg());
    let game = TinyTurnRiver::new(tree_s, board, [hands0.clone(), hands1.clone()]);
    let mut scalar = ScalarCfr::new(&game, variant);
    scalar.run(scalar_iters);
    let scalar_expl = exploitability(&game, &scalar);

    // --- Vector engine, exact enumeration ---------------------------------
    let tree_v = build_turn_river_tree(20 * BB, 90 * BB, &tiny_cfg());
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut vector = TurnRiverSolver::new(tree_v, board, [r0, r1], variant, ChanceMode::Enumerate);
    vector.run(vector_iters);
    let vector_expl = vector.exploitability_bb();

    // --- 1. Both engines converge ----------------------------------------
    assert!(
        vector_expl.exploitability < 0.02,
        "vector exploitability {:.4}",
        vector_expl.exploitability
    );
    assert!(
        scalar_expl < 0.10,
        "scalar exploitability {scalar_expl:.4} — not converging"
    );

    // --- 2. Game-value invariant ------------------------------------------
    // Same equilibrium => game values agree within the exploitability budget.
    let v_scalar = scalar_game_value_p0(&game, &scalar, &game.root());
    let v_vector = vector.game_value_p0();
    let budget = scalar_expl + vector_expl.exploitability;
    eprintln!("game values: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})");
    assert!(
        (v_scalar - v_vector).abs() <= budget,
        "game values diverge: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})"
    );

    // --- 3. Turn-root strategy agreement (root is always on-path) ----------
    let na = vector.tree.nodes[0].children.len();
    for (hi, &(a, b)) in hands1.iter().enumerate() {
        let key = format!("1|{hi}|0|-");
        let ss = scalar.average_strategy(&key, na);
        let vs = vector.average_strategy(0, None, combo_index(a, b));
        for ai in 0..na {
            assert!(
                (ss[ai] - vs[ai]).abs() < 0.06,
                "root hand {hi} action {ai}: scalar {:.4} vs vector {:.4}",
                ss[ai],
                vs[ai]
            );
        }
    }

    eprintln!(
        "turn+river differential OK: scalar expl {scalar_expl:.5}, vector expl {:.5}",
        vector_expl.exploitability
    );
}
