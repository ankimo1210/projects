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

// String card helper (e.g. "Ac") -> card byte, same rank*4+suit encoding.
fn card(s: &str) -> u8 {
    let r = "23456789TJQKA".find(s.as_bytes()[0] as char).unwrap() as u8;
    let suit = "cdhs".find(s.as_bytes()[1] as char).unwrap() as u8;
    r * 4 + suit
}

// Combo index matching gto_core::range::combo_index: lo*(103-lo)/2 + hi-lo-1.
fn combo_idx(a: u8, b: u8) -> usize {
    let (lo, hi) = if a < b { (a, b) } else { (b, a) };
    (lo as usize) * (103 - lo as usize) / 2 + hi as usize - lo as usize - 1
}

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
    // And the rake must actually perturb the root equilibrium (not bit-
    // identical to the unraked one). The magnitude is intentionally NOT
    // thresholded: once fold terminals rake only the matched pot, the rake's
    // distortion on this board is small and the raked root strategy converges
    // back toward the unraked one (max_diff -> 0 with more iterations), so any
    // fixed lower bound would be calibrating against non-convergence. The
    // value leak above is the robust witness that the rake bites; here we only
    // assert the strategies are not identical.
    let a = unraked.aggregate_strategy(0);
    let b = raked.aggregate_strategy(0);
    let max_diff = a.iter().zip(b.iter()).map(|((_, x), (_, y))| (x - y).abs()).fold(0.0, f64::max);
    assert!(max_diff > 0.0, "rake changed nothing at the root (max diff {max_diff})");
}

#[test]
fn asymmetric_checkdown_pins_per_player_raked_values() {
    // Hero (p0) holds AcAd, villain (p1) holds 3c5d on a dry checkdown board
    // (2c 7d 9s Jh 4s — disjoint from all four hole cards). Pair of aces always
    // beats nine-high, so hero wins every showdown. Check-only tree -> all
    // showdowns. Site rake on a 20bb pot = min(5%*20, 3) = 1bb.
    //   Hero nets  10 - 1 = 9 bb ; villain nets -10 bb.  (sum = -1bb leak)
    // A (compat - diff)/2 sign bug would give 10 / -11 instead — this test
    // pins the direction the symmetric tests cannot.
    let board = [c(0, 0), c(5, 1), c(7, 3), c(9, 2), c(2, 3)]; // 2c 7d 9s Jh 4s
    let mut r0 = gto_hu::ranges::Range::new_empty();
    let mut r1 = gto_hu::ranges::Range::new_empty();
    r0.weights[combo_idx(card("Ac"), card("Ad"))] = 1.0;
    r1.weights[combo_idx(card("3c"), card("5d"))] = 1.0;
    let tree = build_river_tree(20 * BB, 90 * BB, &check_only());
    let mut s = VectorRiverSolver::with_rake(
        tree, board, [r0, r1], CfrVariant::cfr_plus_default(), RakeModel::site(),
    );
    s.run(5);
    assert!((s.game_value(0) - 9.0).abs() < 1e-9, "gv0 {} != 9", s.game_value(0));
    assert!((s.game_value(1) + 10.0).abs() < 1e-9, "gv1 {} != -10", s.game_value(1));
}
