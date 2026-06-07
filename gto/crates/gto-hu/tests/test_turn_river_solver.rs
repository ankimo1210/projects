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
