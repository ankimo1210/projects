use gto_core::eval::parse_card;
use gto_hu::game::{Street, BB};
use gto_hu::ranges::{uniform_excluding, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn board() -> [u8; 4] {
    [c("2c"), c("7d"), c("9h"), c("Jh")]
}

fn reduced_cfg() -> TurnTreeConfig {
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

fn solver(cfg: &TurnTreeConfig, mode: ChanceMode) -> TurnRiverSolver {
    let tree = build_turn_river_tree(20 * BB, 90 * BB, cfg);
    let b = board();
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    TurnRiverSolver::new(tree, b, ranges, CfrVariant::cfr_plus_default(), mode)
}

#[test]
fn strategies_sum_to_one_for_unblocked_combos() {
    let mut s = solver(&reduced_cfg(), ChanceMode::Enumerate);
    s.run(10);
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
                let strat = s.average_strategy(node_id, ctx, combo);
                let sum: f64 = strat.iter().sum();
                assert!(
                    (sum - 1.0).abs() < 1e-9,
                    "node {node_id} ctx {ctx:?} combo {combo}: sums to {sum}"
                );
            }
        }
    }
}

#[test]
fn exploitability_is_finite_and_decreases() {
    let mut s = solver(&reduced_cfg(), ChanceMode::Enumerate);
    s.run(10);
    let e1 = s.exploitability_bb();
    s.run(90);
    let e2 = s.exploitability_bb();
    eprintln!(
        "turn+river exploitability: {:.4} bb → {:.4} bb",
        e1.exploitability, e2.exploitability
    );
    assert!(e1.exploitability.is_finite() && e2.exploitability.is_finite());
    assert!(e1.exploitability >= -1e-9 && e2.exploitability >= -1e-9);
    assert!(
        e2.exploitability < e1.exploitability,
        "exploitability must fall: {:.4} → {:.4}",
        e1.exploitability,
        e2.exploitability
    );
}

#[test]
fn quads_never_fold_to_turn_jam() {
    use gto_hu::game::Action;
    use gto_hu::ranges::combo_index;
    // Board 7c7d2h2s: pocket 7h7s is quads and unbeatable on ANY river
    // (no 3-flush possible → no straight flush; 2222 is the only other
    // quads and loses). Folding to the turn jam is strictly dominated.
    let jam_cfg = TurnTreeConfig {
        turn: StreetConfig {
            bet_pcts: vec![50],
            allow_allin_bet: false,
            raise: RaiseRule::ToFactorOrJam(3.0),
            max_raises: 2,
        },
        river: StreetConfig {
            bet_pcts: vec![75],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    };
    let b = [c("7c"), c("7d"), c("2h"), c("2s")];
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &jam_cfg);
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    let mut s = TurnRiverSolver::new(
        tree,
        b,
        ranges,
        CfrVariant::cfr_plus_default(),
        ChanceMode::Enumerate,
    );
    // Path: OOP b50 → IP raise 3x → OOP jam → IP (hero) faces the jam.
    let bet = s.tree.nodes[0]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::Bet { .. }))
        .map(|&(_, id)| id)
        .unwrap();
    let raise = s.tree.nodes[bet]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::Raise { .. }))
        .map(|&(_, id)| id)
        .unwrap();
    let jam = s.tree.nodes[raise]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::AllIn { .. }))
        .map(|&(_, id)| id)
        .unwrap();
    s.run(150);
    let quads = combo_index(c("7h"), c("7s"));
    // strat layout follows children order; facing a bet, legal_actions
    // pushes Fold first → strat[0] is the fold frequency.
    let strat = s.average_strategy(jam, None, quads);
    eprintln!("quads fold freq vs turn jam = {}", strat[0]);
    assert!(strat[0] < 0.02, "quads folded to jam: {}", strat[0]);
}

#[test]
fn sampled_mode_is_deterministic_per_seed() {
    let run = |seed: u64| {
        let mut s = solver(&reduced_cfg(), ChanceMode::Sample { seed });
        s.run(200);
        let e = s.exploitability_bb().exploitability;
        let root: Vec<f64> = s
            .aggregate_strategy(0, None)
            .into_iter()
            .map(|(_, f)| f)
            .collect();
        (e, root)
    };
    let (e1, r1) = run(7);
    let (e2, r2) = run(7);
    let (e3, r3) = run(8);
    // Same seed ⇒ bit-identical training run.
    assert_eq!(e1, e2, "same seed must reproduce exploitability exactly");
    assert_eq!(r1, r2, "same seed must reproduce the root strategy exactly");
    // Different seed ⇒ different sampled card sequence ⇒ different tables.
    assert!(
        e1 != e3 || r1 != r3,
        "seed appears to be ignored (identical run for different seeds)"
    );
}

#[test]
fn sampled_mode_converges_toward_equilibrium() {
    let mut s = solver(&reduced_cfg(), ChanceMode::Sample { seed: 42 });
    s.run(50_000);
    let e = s.exploitability_bb();
    eprintln!("sampled 50000 iters: expl {:.4} bb", e.exploitability);
    assert!(e.exploitability.is_finite());
    assert!(e.exploitability >= -1e-9);
    assert!(
        e.exploitability < 0.15,
        "sampled training failed to converge: {:.4} bb",
        e.exploitability
    );
}
