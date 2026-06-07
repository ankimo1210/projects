//! Differential test: the scalar reference engine (explicit deals) and
//! the vector preflop engine (range masks, O(N²) equity terminals) must
//! converge to the same equilibrium of the same simplified game — both
//! sides share one deterministic toy equity table, so any disagreement
//! is a solver bug, not model noise.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::{TinyPreflop, TinyPreflopState};
use gto_hu::ranges::{combo_index, Range, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, EquityTable, Game, PreflopSolver, ScalarCfr};
use gto_hu::tree::build_preflop_tree;
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

/// Deterministic toy equity in [0.25, 0.75] (zero-sum mirrored by
/// `from_fn`). Both engines build identical tables from this.
fn toy_eq() -> EquityTable {
    EquityTable::from_fn(|a, b| {
        // One SplitMix64 mixing step over the pair id.
        let mut z = ((a * NUM_COMBOS + b) as u64).wrapping_add(0x9E37_79B9_7F4A_7C15);
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^= z >> 31;
        0.25 + 0.5 * ((z % 1000) as f32 / 1000.0)
    })
}

/// Game value to player 0 when both follow the scalar average strategy.
fn scalar_game_value_p0(
    game: &TinyPreflop,
    solver: &ScalarCfr<TinyPreflop>,
    state: &TinyPreflopState,
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
fn scalar_and_vector_agree_on_tiny_preflop_spot() {
    // Player 0 = SB; player 1 = BB. No card clashes between the lists.
    let hands0 = vec![(c("Qc"), c("Tc")), (c("Ah"), c("Ad")), (c("6s"), c("5s"))];
    let hands1 = vec![(c("Kh"), c("Qh")), (c("8s"), c("8d")), (c("2c"), c("2d"))];
    let variant = CfrVariant::cfr_plus_default();

    // --- Scalar reference ------------------------------------------------
    let game = TinyPreflop::new(
        build_preflop_tree(100 * BB),
        [hands0.clone(), hands1.clone()],
        toy_eq(),
    );
    let mut scalar = ScalarCfr::new(&game, variant);
    scalar.run(3_000);
    let scalar_expl = exploitability(&game, &scalar);

    // --- Vector engine ----------------------------------------------------
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut vector = PreflopSolver::new(build_preflop_tree(100 * BB), [r0, r1], variant, toy_eq());
    vector.run(1_500);
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
    let v_scalar = scalar_game_value_p0(&game, &scalar, &game.root());
    let v_vector = vector.game_value_p0();
    let budget = scalar_expl + vector_expl.exploitability;
    eprintln!("game values: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})");
    assert!(
        (v_scalar - v_vector).abs() <= budget,
        "game values diverge: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})"
    );

    // --- 3. SB root strategy agreement -------------------------------------
    let na = vector.tree.nodes[0].children.len();
    for (hi, &(a, b)) in hands0.iter().enumerate() {
        let key = format!("0|{hi}|0");
        let ss = scalar.average_strategy(&key, na);
        let vs = vector.average_strategy(0, combo_index(a, b));
        for ai in 0..na {
            assert!(
                (ss[ai] - vs[ai]).abs() < 0.08,
                "root hand {hi} action {ai}: scalar {:.4} vs vector {:.4}",
                ss[ai],
                vs[ai]
            );
        }
    }

    eprintln!(
        "preflop differential OK: scalar expl {scalar_expl:.5}, vector expl {:.5}",
        vector_expl.exploitability
    );
}
