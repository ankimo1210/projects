use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{all_combos, combo_index, uniform_excluding};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn board() -> [u8; 4] {
    [c("2c"), c("7d"), c("9h"), c("Jh")]
}

/// Small abstraction: keeps solver tables at a few MB for tests.
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

fn solver(mode: ChanceMode) -> TurnRiverSolver {
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &reduced_cfg());
    let b = board();
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    TurnRiverSolver::new(tree, b, ranges, CfrVariant::cfr_plus_default(), mode)
}

#[test]
fn rivers_exclude_board_unique_and_complete() {
    let s = solver(ChanceMode::Enumerate);
    let rivers = s.rivers();
    assert_eq!(rivers.len(), 48, "52 − 4 board cards");
    let b = board();
    for &r in rivers {
        assert!(!b.contains(&r), "river card duplicates the board");
    }
    let mut sorted = rivers.to_vec();
    sorted.sort_unstable();
    sorted.dedup();
    assert_eq!(sorted.len(), 48, "river cards must be unique");
}

#[test]
fn chance_weights_sum_to_one_per_deal() {
    // For any fixed (hero, villain) deal, exactly 44 of the 48 public cards
    // avoid all four hole cards; the enumerate weight is 1/44 each.
    let s = solver(ChanceMode::Enumerate);
    let combos = all_combos();
    let hero = combos[combo_index(c("Ah"), c("Kd"))];
    let vill = combos[combo_index(c("Qs"), c("Qc"))];
    let legal = s
        .rivers()
        .iter()
        .filter(|&&r| r != hero.0 && r != hero.1 && r != vill.0 && r != vill.1)
        .count();
    assert_eq!(legal, 44);
    assert!((legal as f64 * (1.0 / 44.0) - 1.0).abs() < 1e-12);
}

#[test]
fn river_card_blocked_combos_are_masked() {
    let mut s = solver(ChanceMode::Enumerate);
    s.run(5);
    let combos = all_combos();
    let card = s.rivers()[0];
    // A combo holding the dealt river card, otherwise legal on the turn.
    let partner = c("As");
    assert_ne!(card, partner);
    let blocked = combo_index(card, partner);
    assert_eq!(combos[blocked].0.min(combos[blocked].1), card.min(partner));

    // Visible on the turn, masked under that river card.
    assert!(s.export_weight(0, None, blocked) > 0.0);
    assert_eq!(s.export_weight(0, Some(0), blocked), 0.0);

    // Its reach under that river was zeroed, so strat_sum stayed 0 →
    // average strategy is uniform there.
    let river_node = s
        .action_node_ids()
        .into_iter()
        .find(|&id| s.tree.nodes[id].state.street == gto_hu::game::Street::River)
        .expect("river action node");
    let avg = s.average_strategy(river_node, Some(0), blocked);
    let na = avg.len();
    for v in &avg {
        assert!(
            (v - 1.0 / na as f64).abs() < 1e-12,
            "expected untouched uniform"
        );
    }
}
