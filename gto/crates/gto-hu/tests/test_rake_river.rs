//! Rake validation on degenerate river trees where equilibria are
//! hand-computable (mode-matrix spec section 4.2; replaces the spec's
//! "Kuhn+rake" idea — Kuhn runs on ScalarCfr, which has no rake).

use gto_hu::game::{RakeModel, BB};
use gto_hu::ranges::uniform_excluding;
use gto_hu::solver::{CfrVariant, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, StreetConfig};

/// Check-only config: no bets exist, so every line is check/check ->
/// showdown and all values are direct showdown payoffs.
fn check_only() -> StreetConfig {
    StreetConfig {
        bet_pcts: vec![],
        allow_allin_bet: false,
        raise: gto_hu::tree::RaiseRule::None,
        max_raises: 0,
    }
}

fn solve(board: [u8; 5], cfg: &StreetConfig, rake: RakeModel, iters: u32) -> VectorRiverSolver {
    let tree = build_river_tree(20 * BB, 90 * BB, cfg);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut s = VectorRiverSolver::with_rake(tree, board, ranges, CfrVariant::cfr_plus_default(), rake);
    s.run(iters);
    s
}

// Board card helper: rank 0=2..12=A, suit 0=c.. (card = rank*4+suit).
fn c(rank: u8, suit: u8) -> u8 { rank * 4 + suit }

#[test]
fn forced_checkdown_site_rake_values_are_exact() {
    // Mixed board, 20bb pot, site rake = min(5%*20bb, 3bb) = 1bb.
    // Forced checkdown: winner nets 10-1=9bb, loser -10bb, chop -0.5bb.
    // Aggregated over uniform vs uniform the totals must satisfy
    // gv0 + gv1 = -E[rake] with E[rake] = 1bb * P(non-chop) + 1bb * P(chop)
    // = exactly -1bb (every pot pays 1bb rake regardless of outcome).
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3), c(12, 0)];
    let s = solve(board, &check_only(), RakeModel::site(), 10);
    let gv = [s.game_value(0), s.game_value(1)];
    assert!((gv[0] + gv[1] + 1.0).abs() < 1e-9, "value sum {} != -1bb rake", gv[0] + gv[1]);
    // No decisions exist -> BR == avg value -> NashConv == 0.
    let e = s.exploitability_bb();
    assert!(e.nashconv.abs() < 1e-9, "nashconv {} != 0", e.nashconv);
    assert!(e.exploitability.abs() < 1e-9);
}

#[test]
fn forced_checkdown_board_plays_chop_tax_is_half_rake_each() {
    // Broadway board AKQJT rainbow: every combo plays the board straight ->
    // every showdown chops -> each player nets exactly -rake/2 = -0.5bb.
    let board = [c(12, 0), c(11, 1), c(10, 2), c(9, 3), c(8, 0)];
    let s = solve(board, &check_only(), RakeModel::site(), 10);
    assert!((s.game_value(0) + 0.5).abs() < 1e-9, "gv0 {}", s.game_value(0));
    assert!((s.game_value(1) + 0.5).abs() < 1e-9, "gv1 {}", s.game_value(1));
}

#[test]
fn unraked_report_matches_legacy_formula_exactly() {
    // rake=0 path: nashconv must equal br0+br1 EXACTLY (same arithmetic
    // as the pre-rake (br0+br1)/2 formula).
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3), c(12, 0)];
    let s = solve(board, &StreetConfig::srp_river(), RakeModel::NONE, 200);
    let e = s.exploitability_bb();
    assert_eq!(e.nashconv, e.br_value[0] + e.br_value[1]);
    assert_eq!(e.exploitability, (e.br_value[0] + e.br_value[1]) / 2.0);
}

#[test]
fn raked_equilibrium_differs_and_values_sum_negative() {
    let board = [c(0, 0), c(3, 1), c(7, 2), c(9, 3), c(12, 0)];
    let unraked = solve(board, &StreetConfig::srp_river(), RakeModel::NONE, 2000);
    let raked = solve(board, &StreetConfig::srp_river(), RakeModel::site(), 2000);
    // The raked game leaks value: total <= 0 strictly, bounded by the cap.
    let total = raked.game_value(0) + raked.game_value(1);
    assert!(total < 0.0, "raked total value {total} must be negative");
    assert!(total > -3.0, "cannot exceed the 3bb cap");
    // And the strategies must actually move at the root.
    let a = unraked.aggregate_strategy(0);
    let b = raked.aggregate_strategy(0);
    let max_diff = a.iter().zip(b.iter()).map(|((_, x), (_, y))| (x - y).abs()).fold(0.0, f64::max);
    assert!(max_diff > 0.005, "rake changed nothing at the root (max diff {max_diff})");
}
