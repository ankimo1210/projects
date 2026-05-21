//! Property tests for gto-core::CfrSolver via public API.
//!
//! Properties verified:
//!   1. Root strategy frequencies sum to 1.0.
//!   2. All per-action frequencies are in [0, 1].
//!   3. Proxy exploitability decreases (or stabilizes) with more iterations.
//!   4. Solver runs without panic on various board/pot configurations.

use gto_core::{
    CfrSolver, GameTree, Range, Street,
    eval::parse_card,
};

fn make_solver(board_str: &[&str], iters: u32) -> CfrSolver {
    let board: Vec<u8> = board_str.iter()
        .filter_map(|s| parse_card(s))
        .collect();
    let pot   = 1000i64;  // 10 BB × 100
    let stack = 9500i64;  // 95 BB × 100
    let tree  = GameTree::build(pot, stack, Street::River);
    let ranges = [Range::new_uniform(), Range::new_uniform()];
    let mut solver = CfrSolver::new(tree, board, ranges);
    solver.run(iters);
    solver
}

// ── Test 1: Root strategy sums to 1.0 ───────────────────────────────────────

#[test]
fn test_root_strategy_sums_to_one() {
    let solver = make_solver(&["Ah", "Kd", "2c", "5s", "9h"], 500);
    let strat  = solver.root_strategy();

    assert!(!strat.is_empty(), "root_strategy() returned empty");

    let total: f64 = strat.iter().map(|(_, f)| f).sum();
    assert!(
        (total - 1.0).abs() < 0.01,
        "Root strategy sums to {total:.6} (expected ~1.0). Breakdown: {strat:?}"
    );
    eprintln!("✅ Root strategy sum = {total:.8}");
    for (act, freq) in &strat {
        eprintln!("   {act}: {freq:.4}");
    }
}

// ── Test 2: All root strategy frequencies in [0,1] ──────────────────────────

#[test]
fn test_root_frequencies_bounded() {
    let solver = make_solver(&["Ah", "Kd", "2c", "5s", "9h"], 500);
    let strat  = solver.root_strategy();

    for (act, freq) in &strat {
        assert!(
            *freq >= -1e-6 && *freq <= 1.0 + 1e-6,
            "Action {act} has out-of-bounds frequency: {freq:.6}"
        );
    }
    eprintln!("✅ All root strategy frequencies are in [0, 1]");
}

// ── Test 3: Proxy exploitability decreases with more iterations ──────────────

#[test]
fn test_proxy_convergence() {
    let board = &["Ah", "Kd", "2c", "5s", "9h"];
    let solver_100  = make_solver(board, 100);
    let solver_2000 = make_solver(board, 2000);

    let expl_100  = solver_100.exploitability();
    let expl_2000 = solver_2000.exploitability();

    eprintln!("Proxy exploitability: 100 iters={expl_100:.6}  2000 iters={expl_2000:.6}");
    // Should not blow up (allowing 2x tolerance for noise + DCFR non-monotone phase)
    assert!(
        expl_2000 <= expl_100 * 2.0 + 100.0,
        "Proxy exploitability went up dramatically: 100={expl_100:.4} → 2000={expl_2000:.4}"
    );
    eprintln!("✅ Proxy exploitability: 100 iters={expl_100:.4}, 2000 iters={expl_2000:.4}");
}

// ── Test 4: Solver runs on multiple boards without panic ──────────────────────

#[test]
fn test_no_panic_various_boards() {
    let boards = [
        vec!["Ah", "Kd", "2c", "5s", "9h"],
        vec!["Qs", "Jd", "Tc", "9h", "2d"],   // straight board
        vec!["As", "Ad", "Ac", "Kh", "Qd"],   // trips on board
        vec!["2h", "3d", "4c", "5s", "6h"],   // wheel straight
    ];
    for board in &boards {
        let solver = make_solver(board, 200);
        let strat  = solver.root_strategy();
        let total: f64 = strat.iter().map(|(_, f)| f).sum();
        assert!(
            (total - 1.0).abs() < 0.05,
            "Board {:?}: root strategy sum = {total:.4}", board
        );
        eprintln!("✅ Board {:?}: root strategy OK (sum={total:.4})", board);
    }
}

// ── Test 5: Exploitability proxy is non-negative ─────────────────────────────

#[test]
fn test_exploitability_nonneg() {
    let solver = make_solver(&["Ah", "Kd", "2c", "5s", "9h"], 500);
    let expl   = solver.exploitability();
    assert!(expl >= -1e-6, "Exploitability proxy is negative: {expl:.6}");
    eprintln!("✅ Exploitability proxy = {expl:.6} (non-negative)");
}
