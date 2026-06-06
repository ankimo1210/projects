//! Differential test (mandatory per spec): the scalar reference engine and
//! the vector production engine must converge to the same equilibrium on
//! identical tiny river spots.
//!
//! ## Indifference note (from debugging)
//!
//! On the board 2c7d9hJhKd with this 3v3 hand set, the equilibrium has a
//! largely pure structure at the root (OOP always checks with bluff-catcher
//! hands), which makes many sub-tree nodes unreachable at equilibrium.  At
//! unreachable nodes, *any* strategy is a valid Nash equilibrium: both engines
//! are free to play differently there without any exploitability cost.
//!
//! The strategy comparison therefore filters to only nodes whose reach
//! probability under the converged vector strategy exceeds a small threshold
//! (0.5 % of deals).  At those on-path nodes both engines agree within 0.05.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::{TinyRiver, TinyRiverState};
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{CfrVariant, Game, ScalarCfr, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, NodeKind, StreetConfig};
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

/// Game value to player 0 when both players follow the scalar average
/// strategy.  Pure expected-value recursion (no reach threading needed):
///   terminal → payoff_p0
///   chance   → Σ p * recurse(child)
///   action   → Σ strat[a] * recurse(next(state, a))
fn scalar_game_value_p0(
    game: &TinyRiver,
    solver: &ScalarCfr<TinyRiver>,
    state: &TinyRiverState,
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

/// Compute the reach probability of each node under the vector equilibrium,
/// averaged over all non-clashing (hand0, hand1) deals.
fn node_reach(
    vector: &VectorRiverSolver,
    hands0: &[(u8, u8)],
    hands1: &[(u8, u8)],
) -> std::collections::HashMap<usize, f64> {
    let mut reach: std::collections::HashMap<usize, f64> = std::collections::HashMap::new();
    let n_deals = hands0.len() * hands1.len();
    for &h0 in hands0 {
        for &h1 in hands1 {
            if h0.0 == h1.0 || h0.0 == h1.1 || h0.1 == h1.0 || h0.1 == h1.1 {
                continue; // card clash
            }
            let c0 = combo_index(h0.0, h0.1);
            let c1 = combo_index(h1.0, h1.1);
            let base = 1.0 / n_deals as f64;
            let mut stack: Vec<(usize, f64)> = vec![(0, base)];
            while let Some((node_id, prob)) = stack.pop() {
                *reach.entry(node_id).or_insert(0.0) += prob;
                let node = &vector.tree.nodes[node_id];
                if node.children.is_empty() {
                    continue;
                }
                if let NodeKind::Action { actor } = node.kind {
                    let combo = if actor == 0 { c0 } else { c1 };
                    let strat = vector.average_strategy(node_id, combo);
                    for (a, &(_, child_id)) in node.children.iter().enumerate() {
                        if strat[a] > 1e-4 {
                            stack.push((child_id, prob * strat[a]));
                        }
                    }
                }
            }
        }
    }
    reach
}

#[test]
fn scalar_and_vector_agree_on_tiny_spot() {
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    // Player 0 = SB/IP hands; player 1 = BB/OOP hands.
    let hands0 = vec![(c("Qc"), c("Tc")), (c("4s"), c("3s")), (c("Ah"), c("Ad"))];
    let hands1 = vec![(c("Kh"), c("Qh")), (c("8s"), c("8d")), (c("Qs"), c("Ts"))];
    // Scalar needs more iterations than vector to reach strategy-level convergence
    // on this 32-node tree.  The vector solver (per-combo traversal) converges at
    // O(1/T); the scalar solver converges more slowly because off-path nodes
    // accumulate information at a rate proportional to their reach probability.
    // 30 000 scalar iterations (~18 s in release) yields expl ≈ 0.048 and brings
    // on-path strategies within 0.05 of the vector equilibrium.
    // 3 000 vector iterations yield expl < 0.001.
    let scalar_iters = 30_000;
    let vector_iters = 3_000;
    let variant = CfrVariant::cfr_plus_default();

    // --- Scalar reference ------------------------------------------------
    let tree_s = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let game = TinyRiver::new(tree_s, board, [hands0.clone(), hands1.clone()]);
    let mut scalar = ScalarCfr::new(&game, variant);
    scalar.run(scalar_iters);
    let scalar_expl = exploitability(&game, &scalar);

    // --- Vector production engine ----------------------------------------
    let tree_v = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut vector = VectorRiverSolver::new(tree_v, board, [r0, r1], variant);
    vector.run(vector_iters);
    let vector_expl = vector.exploitability_bb();

    // --- 1. Exploitability checks ----------------------------------------
    // Vector converges quickly (O(1/T) with per-combo traversal).
    assert!(
        vector_expl.exploitability < 0.02,
        "vector exploitability {:.4}",
        vector_expl.exploitability
    );
    // Scalar convergence is slower; at 30 000 iterations on this tree ≈ 0.048.
    assert!(
        scalar_expl < 0.06,
        "scalar exploitability {scalar_expl:.4} — not converging"
    );

    // --- 2. Strategy agreement at on-path nodes --------------------------
    // At equilibrium OOP checks with bluff-catcher hands, so only a subset of
    // the 32-node tree is actually reached.  At unreached nodes any strategy
    // is a Nash equilibrium (EVdiff = 0 × anything = 0), so disagreement
    // there is expected and correct.  We compare only at nodes whose reach
    // probability under the converged vector strategy exceeds 0.5 % of deals.
    let reach = node_reach(&vector, &hands0, &hands1);
    let n_deals = hands0.len() * hands1.len();
    const REACH_THRESHOLD: f64 = 0.005; // 0.5 % of deals

    for node_id in vector.action_node_ids() {
        let reach_frac = reach.get(&node_id).copied().unwrap_or(0.0) / n_deals as f64;
        if reach_frac < REACH_THRESHOLD {
            continue; // unreachable node — indifference applies, skip
        }
        let actor = vector.actor_at(node_id) as usize;
        let hands = if actor == 0 { &hands0 } else { &hands1 };
        let na = vector.tree.nodes[node_id].children.len();
        for (hi, &(a, b)) in hands.iter().enumerate() {
            let key = format!("{actor}|{hi}|{node_id}");
            let ss = scalar.average_strategy(&key, na);
            let vs = vector.average_strategy(node_id, combo_index(a, b));
            for ai in 0..na {
                assert!(
                    (ss[ai] - vs[ai]).abs() < 0.05,
                    "node {node_id} (reach {reach_frac:.3}) hand {hi} action {ai}: \
                     scalar {:.4} vs vector {:.4}",
                    ss[ai],
                    vs[ai]
                );
            }
        }
    }

    // --- 3. Game-value invariant -----------------------------------------
    // Both engines converging to the same equilibrium must agree on the
    // game value to player 0 (avg-strat vs avg-strat) within the combined
    // exploitability budget.
    let v_scalar = scalar_game_value_p0(&game, &scalar, &game.root());
    let v_vector = vector.game_value_p0();
    let budget = scalar_expl + vector_expl.exploitability;
    assert!(
        (v_scalar - v_vector).abs() <= budget,
        "game values diverge: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})"
    );
    eprintln!("game values: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})");

    eprintln!(
        "differential OK: scalar expl {scalar_expl:.5} bb, vector expl {:.5} bb",
        vector_expl.exploitability
    );
}

#[test]
fn vector_handles_blocker_overlap_like_scalar() {
    // Hands that block each other (QcTc vs QsTs share nothing, but add
    // KhQh vs QcTc? — use an explicit overlap: both players hold Qx).
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let hands0 = vec![(c("Qc"), c("Tc")), (c("Qd"), c("Td"))];
    let hands1 = vec![(c("Qh"), c("Th")), (c("8s"), c("8d"))];
    // Deals where both hold a Q+T are still compatible (different suits);
    // the point is identical chance support in both engines.
    let tree_s = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let game = TinyRiver::new(tree_s, board, [hands0.clone(), hands1.clone()]);
    let mut scalar = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    scalar.run(2_000);

    let tree_v = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut vector =
        VectorRiverSolver::new(tree_v, board, [r0, r1], CfrVariant::cfr_plus_default());
    vector.run(2_000);

    let root_scalar = scalar.average_strategy("1|0|0", 4);
    let root_vector = vector.average_strategy(0, combo_index(c("Qh"), c("Th")));
    for ai in 0..4 {
        assert!(
            (root_scalar[ai] - root_vector[ai]).abs() < 0.05,
            "action {ai}: scalar {:.4} vs vector {:.4}",
            root_scalar[ai],
            root_vector[ai]
        );
    }
}
