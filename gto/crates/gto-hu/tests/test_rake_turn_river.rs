//! Rake on the turn+river solver: forced checkdown hand-check + the
//! unraked-identity regression. Mirrors test_rake_river.rs.

use gto_hu::game::{RakeModel, BB};
use gto_hu::ranges::uniform_excluding;
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn check_only() -> StreetConfig {
    StreetConfig { bet_pcts: vec![], allow_allin_bet: false, raise: RaiseRule::None, max_raises: 0 }
}

fn c(rank: u8, suit: u8) -> u8 { rank * 4 + suit }

fn solve(cfg: TurnTreeConfig, rake: RakeModel, iters: u32) -> TurnRiverSolver {
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3)];
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &cfg);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut s = TurnRiverSolver::with_rake(
        tree, board, ranges, CfrVariant::cfr_plus_default(), ChanceMode::Enumerate, rake,
    );
    s.run(iters);
    s
}

#[test]
fn forced_checkdown_site_rake_sums_to_minus_one_bb() {
    let cfg = TurnTreeConfig { turn: check_only(), river: check_only() };
    let s = solve(cfg, RakeModel::site(), 5);
    let total = s.game_value(0) + s.game_value(1);
    assert!((total + 1.0).abs() < 1e-9, "value sum {total} != -1bb rake");
    let e = s.exploitability_bb();
    assert!(e.nashconv.abs() < 1e-9);
}

#[test]
fn unraked_identity_holds() {
    let s = solve(TurnTreeConfig::srp(), RakeModel::NONE, 50);
    let e = s.exploitability_bb();
    assert_eq!(e.nashconv, e.br_value[0] + e.br_value[1]);
}
