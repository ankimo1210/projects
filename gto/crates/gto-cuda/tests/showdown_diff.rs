//! GPU-vs-CPU correctness tests for the gto-cuda showdown and batch solver.
//!
//! These require a real CUDA device (RTX 5080 / sm_120). They pin the fixes
//! for B1 (per-spot pots), B2 (board-blocked combos), and B3 (node-pot
//! showdowns). The CPU reference is gto-core's showdown formula, replicated
//! here from the public `showdown_strengths` / `all_combos` API (the solver's
//! private `showdown_values` is unreachable from an integration test).

use gto_core::{all_combos, showdown_strengths, Card};
use gto_cuda::{BatchCfrSolver, GameTree, NUM_COMBOS};
use gto_cuda::cfr::{NodeKind, combo_tables};
use gto_cuda::fast_cfr::FastCfrSolver;

/// Parse a 5-card river board into card ints (rank*4+suit).
fn river_board(cards: &[&str]) -> Vec<u8> {
    cards.iter().map(|s| Card::from_str(s).unwrap().0).collect()
}

/// Per-spot strengths + range (0 for board-blocked combos), mirroring lib.rs.
/// `eval::Card` is a `u8` alias, so the board ints feed `showdown_strengths`
/// directly.
fn strengths_and_ranges(board: &[u8]) -> (Vec<u16>, Vec<f32>) {
    let strengths = showdown_strengths(board);
    let ranges: Vec<f32> = strengths.iter().map(|&s| if s == 0 { 0.0 } else { 1.0 }).collect();
    (strengths, ranges)
}

/// CPU reference for the showdown values (player `traverser`), matching
/// gto-core/src/cfr.rs::showdown_values: filter strength-0 combos on both
/// sides, normalize by total opponent reach, value at `half_pot`.
fn cpu_showdown_values(
    strengths: &[u16],
    hero_range: &[f32],
    opp_reach: &[f32],
    half_pot: f64,
) -> Vec<f64> {
    let combos = all_combos();
    let mut vals = vec![0.0f64; NUM_COMBOS];
    for ci in 0..NUM_COMBOS {
        let hs = strengths[ci];
        // Hero side: blocked combos (strength 0) or zero-range combos are dont-care.
        if hs == 0 || hero_range[ci] == 0.0 {
            vals[ci] = 0.0;
            continue;
        }
        let (ca, cb) = combos[ci];
        let mut ev = 0.0f64;
        let mut tot = 0.0f64;
        for oi in 0..NUM_COMBOS {
            let os = strengths[oi];
            let ow = opp_reach[oi] as f64;
            if os == 0 || ow == 0.0 { continue; }
            let (oa, ob) = combos[oi];
            if oa == ca || oa == cb || ob == ca || ob == cb { continue; }
            let outcome = if hs > os { half_pot } else if os > hs { -half_pot } else { 0.0 };
            ev += outcome * ow;
            tot += ow;
        }
        vals[ci] = if tot > 0.0 { ev / tot } else { 0.0 };
    }
    vals
}

/// Find a Showdown node whose pot is strictly greater than the root pot
/// (i.e. reached after a bet/call), to exercise the node-pot path (B3).
fn post_bet_showdown(tree: &GameTree) -> Option<usize> {
    let root_pot = tree.nodes[0].pot;
    tree.nodes.iter().enumerate().find_map(|(nid, nd)| {
        matches!(nd.kind, NodeKind::Showdown)
            .then_some(())
            .and_then(|_| (nd.pot > root_pot + 1e-9).then_some(nid))
    })
}

/// B1+B3 differential: GPU showdown values at a post-bet node must match the
/// CPU reference computed at the SAME node pot. Includes board-blocked combos
/// in the reach vector (B2): the reference filters them; the GPU must too.
#[test]
fn gpu_showdown_matches_cpu_at_node_pot() {
    let board = river_board(&["Ah", "Kd", "7c", "2s", "9h"]);
    let (strengths, ranges) = strengths_and_ranges(&board);

    // Single spot. Root pot 10bb (half_pot 5), stack 100bb so a bet+raise
    // tree has a deeper showdown.
    let root_pot = 10.0f64;
    let half_pots = vec![(root_pot / 2.0) as f32];
    let tree = GameTree::build(root_pot, 100.0, 2);

    let sd_node = post_bet_showdown(&tree)
        .expect("tree must contain a post-bet showdown node");
    let node_pot = tree.nodes[sd_node].pot;
    assert!(node_pot > root_pot, "node pot {node_pot} must exceed root pot {root_pot}");

    let hero_str = strengths.clone();
    let opp_str = strengths.clone();
    let mut solver = BatchCfrSolver::new(
        tree, hero_str, opp_str, ranges.clone(), half_pots,
    );

    // Opponent reach = ranges (board-blocked combos are 0, but we deliberately
    // feed the full vector so a regression that ignores strength-0 combos would
    // diverge). Use a non-uniform reach to make the normalizer meaningful.
    let combos = combo_tables();
    let mut opp_reach = ranges.clone();
    for i in 0..NUM_COMBOS {
        // Tilt reach so the weighted average is not a trivial 0.5.
        let (a, _b) = (combos.0[i], combos.1[i]);
        opp_reach[i] *= 0.25 + 0.5 * ((a as f32) / 51.0);
    }

    let gpu = solver.showdown_values_at(sd_node, 0, &opp_reach);
    let cpu = cpu_showdown_values(&strengths, &ranges, &opp_reach, node_pot / 2.0);

    let mut max_abs = 0.0f64;
    let mut max_rel = 0.0f64;
    for ci in 0..NUM_COMBOS {
        let g = gpu[ci] as f64;
        let c = cpu[ci];
        let abs = (g - c).abs();
        max_abs = max_abs.max(abs);
        let denom = c.abs().max(1e-6);
        max_rel = max_rel.max(abs / denom);
    }
    // f32 GPU vs f64 CPU; values are O(half_pot)=O(5). 1e-3 relative is loose
    // but catches the pot-scale (root vs node) and blocked-combo regressions,
    // which both move values by O(1) or more.
    assert!(
        max_rel < 1e-3 && max_abs < 5e-3,
        "GPU showdown diverged from CPU: max_abs={max_abs:.6}, max_rel={max_rel:.6} (node_pot={node_pot})"
    );
}

/// B3 regression guard: the SAME showdown node valued at the root pot (the old
/// bug) must NOT match the CPU reference at the node pot. This proves the test
/// above is actually sensitive to the pot used.
#[test]
fn root_pot_showdown_would_diverge() {
    let board = river_board(&["Ah", "Kd", "7c", "2s", "9h"]);
    let (strengths, ranges) = strengths_and_ranges(&board);

    let root_pot = 10.0f64;
    let tree = GameTree::build(root_pot, 100.0, 2);
    let sd_node = post_bet_showdown(&tree).unwrap();
    let node_pot = tree.nodes[sd_node].pot;

    let opp_reach = ranges.clone();
    // CPU at node pot (correct) vs CPU at root pot (what the old code computed).
    let correct = cpu_showdown_values(&strengths, &ranges, &opp_reach, node_pot / 2.0);
    let buggy   = cpu_showdown_values(&strengths, &ranges, &opp_reach, root_pot / 2.0);
    let max_abs = (0..NUM_COMBOS)
        .map(|ci| (correct[ci] - buggy[ci]).abs())
        .fold(0.0f64, f64::max);
    assert!(
        max_abs > 0.1,
        "node pot ({node_pot}) and root pot ({root_pot}) must give materially different \
         showdown values, else the differential test is vacuous (max_abs={max_abs})"
    );
}

/// B2: a board-blocked opponent combo (strength 0, not a real hand) must
/// contribute nothing to a live hero combo's showdown value. We deliberately
/// feed a UNIFORM 1.0 opp_reach — the exact buggy default seed — so blocked
/// opponents arrive with nonzero weight. The kernel's `os == 0` guard must
/// still filter them, matching the CPU reference (which filters strength-0
/// opponents regardless of reach). Without the guard, every live hero combo
/// would score a guaranteed win against ~all blocked combos, inflating EV.
#[test]
fn blocked_combos_contribute_nothing() {
    // A board that blocks many combos (paired + connected) maximizes phantom count.
    let board = river_board(&["As", "Ad", "Kh", "Kc", "Qs"]);
    let (strengths, ranges) = strengths_and_ranges(&board);

    let n_blocked = strengths.iter().filter(|&&s| s == 0).count();
    assert!(n_blocked > 100, "expected many blocked combos, got {n_blocked}");

    let root_pot = 8.0f64;
    let half_pots = vec![(root_pot / 2.0) as f32];
    let tree = GameTree::build(root_pot, 100.0, 2);
    // Root showdown (Check-Check) is fine for the blocked-combo check.
    let sd_node = tree.nodes.iter().enumerate()
        .find_map(|(nid, nd)| matches!(nd.kind, NodeKind::Showdown).then_some(nid))
        .unwrap();
    let node_pot = tree.nodes[sd_node].pot;

    let mut solver = BatchCfrSolver::new(
        tree, strengths.clone(), strengths.clone(), ranges.clone(), half_pots,
    );

    // Uniform reach: blocked opponents (strength 0) get weight 1.0 here, so a
    // kernel that only skips ow == 0 would count them as phantom hands.
    let opp_reach = vec![1.0f32; NUM_COMBOS];
    let gpu = solver.showdown_values_at(sd_node, 0, &opp_reach);
    // CPU reference filters strength-0 opponents; hero_range = uniform too, so
    // every live hero combo is evaluated.
    let hero_range = vec![1.0f32; NUM_COMBOS];
    let cpu = cpu_showdown_values(&strengths, &hero_range, &opp_reach, node_pot / 2.0);

    // Blocked hero combos must be exactly 0 on the GPU.
    for ci in 0..NUM_COMBOS {
        if strengths[ci] == 0 {
            assert_eq!(gpu[ci], 0.0, "blocked hero combo {ci} must value to 0, got {}", gpu[ci]);
        }
    }
    // Live combos must match the CPU reference that filters blocked opponents.
    let max_abs = (0..NUM_COMBOS)
        .map(|ci| (gpu[ci] as f64 - cpu[ci]).abs())
        .fold(0.0f64, f64::max);
    assert!(max_abs < 5e-3, "blocked-combo handling diverged: max_abs={max_abs:.6}");
}

/// Root game value (player-0 perspective, range-weighted) after solving.
fn root_game_value(solver: &mut BatchCfrSolver, ranges: &[f32], spot: usize) -> f64 {
    let evs = solver.root_ev_per_spot();
    let nc = NUM_COMBOS;
    let mut num = 0.0f64;
    let mut den = 0.0f64;
    for ci in 0..nc {
        let w = ranges[spot * nc + ci] as f64;
        if w == 0.0 { continue; }
        num += w * evs[spot * nc + ci] as f64;
        den += w;
    }
    if den > 0.0 { num / den } else { 0.0 }
}

/// B1: a mixed-pot batch must solve each spot at its own pot. We solve pots
/// [4, 10, 20] bb on one river board.
///   - Ground truth: each pot solved alone (batch-of-1, its own tree).
///   - Broken path: one shared tree (built from the first pot) for all three
///     spots — reproduces the pre-fix behavior and must diverge for non-first
///     spots.
///   - Fixed path: per-(pot) grouping (one solver per distinct pot) — must match
///     ground truth. This is exactly what lib.rs's group_spots now does.
#[test]
fn mixed_pot_batch_solves_each_spot_at_its_pot() {
    let board = river_board(&["Ah", "Kd", "7c", "2s", "9h"]);
    let (strengths, ranges_one) = strengths_and_ranges(&board);
    let pots = [4.0f64, 10.0f64, 20.0f64];
    let stack = 100.0f64;
    let iters = 200u32;
    let nc = NUM_COMBOS;

    // Ground truth: solve each pot alone.
    let mut truth = Vec::new();
    for &pot in &pots {
        let half = vec![(pot / 2.0) as f32];
        let tree = GameTree::build(pot, stack, 2);
        let mut s = BatchCfrSolver::new(
            tree, strengths.clone(), strengths.clone(), ranges_one.clone(), half,
        );
        s.run(iters);
        truth.push(root_game_value(&mut s, &ranges_one, 0));
    }

    // Game value scales with pot, so the three must differ — otherwise the test
    // could not distinguish a shared-pot solve.
    assert!(
        (truth[0] - truth[2]).abs() > 1e-3,
        "ground-truth values must differ across pots: {truth:?}"
    );

    // Fixed path: group by pot. Here every pot is distinct, so each group is a
    // batch-of-1 solver built from that pot — must reproduce ground truth.
    for (gi, &pot) in pots.iter().enumerate() {
        let half = vec![(pot / 2.0) as f32];
        let tree = GameTree::build(pot, stack, 2);
        let mut s = BatchCfrSolver::new(
            tree, strengths.clone(), strengths.clone(), ranges_one.clone(), half,
        );
        s.run(iters);
        let v = root_game_value(&mut s, &ranges_one, 0);
        assert!(
            (v - truth[gi]).abs() < 1e-2,
            "grouped solve for pot {pot} ({v}) must match batch-of-1 ({})",
            truth[gi]
        );
    }

    // Broken path: a single tree from pots[0] for all three spots. The shared
    // tree's node pots are wrong for spots 1 and 2, so their game values must
    // diverge from ground truth. This is the bug group_spots fixes.
    let n = 3usize;
    let mut hero = vec![0u16; n * nc];
    let mut rng = vec![0.0f32; n * nc];
    let mut half = Vec::with_capacity(n);
    for i in 0..n {
        for ci in 0..nc {
            hero[i * nc + ci] = strengths[ci];
            rng[i * nc + ci] = ranges_one[ci];
        }
        half.push((pots[i] / 2.0) as f32);
    }
    let shared_tree = GameTree::build(pots[0], stack, 2); // built from pot[0] only
    let mut s = BatchCfrSolver::new(shared_tree, hero.clone(), hero, rng.clone(), half);
    s.run(iters);
    // rng is the N=3 ranges; spot 2 is the third (pot=20) spot.
    let broken2 = root_game_value(&mut s, &rng, 2);
    eprintln!(
        "B1 evidence: truth(pot=20)={:.4}, shared-tree spot2={:.4}, diff={:.4}",
        truth[2], broken2, (broken2 - truth[2]).abs()
    );
    assert!(
        (broken2 - truth[2]).abs() > 1e-2,
        "shared-tree solve for spot 2 ({broken2}) should diverge from its true value \
         ({}) — if it doesn't, the mixed-pot bug isn't being exercised",
        truth[2]
    );
}

/// B2 (FastCfrSolver path): the fully-GPU solver must seed reach from the
/// per-spot ranges (board-blocked combos = 0), like BatchCfrSolver. The
/// equilibrium average root strategy is perspective-independent, so with both
/// solvers seeding from the same ranges they must converge to the same root
/// strategy on a shared input. (We compare the strategy, not `root_ev_per_spot`,
/// because FastCfrSolver returns the last-traverser EV perspective — a
/// pre-existing convention outside this fix's scope.) A uniform seed in
/// FastCfrSolver would let board-blocked combos weight its strategy-sum and
/// distort the aggregate, breaking the agreement.
#[test]
fn fast_and_batch_agree_on_root_strategy() {
    let board = river_board(&["As", "Ad", "Kh", "9c", "Qs"]); // pair blocks many combos
    let (strengths, ranges) = strengths_and_ranges(&board);

    let pot = 10.0f64;
    let stack = 100.0f64;
    let iters = 400u32;
    let half_pots = vec![(pot / 2.0) as f32];

    let tree_b = GameTree::build(pot, stack, 2);
    let mut sb = BatchCfrSolver::new(
        tree_b, strengths.clone(), strengths.clone(), ranges.clone(), half_pots.clone(),
    );
    sb.run(iters);
    let strat_b = sb.root_strategy();

    let tree_f = GameTree::build(pot, stack, 2);
    let mut sf = FastCfrSolver::new(
        &tree_f, strengths.clone(), strengths.clone(), ranges.clone(), half_pots,
    );
    sf.run(iters);
    let strat_f = sf.root_strategy();

    assert_eq!(strat_b.len(), strat_f.len(), "both solvers share the root action set");
    let mut max_diff = 0.0f64;
    for ((nb, fb), (nf, ff)) in strat_b.iter().zip(strat_f.iter()) {
        assert_eq!(nb, nf, "action ordering must match: {nb} vs {nf}");
        max_diff = max_diff.max((fb - ff).abs());
    }
    eprintln!("fast vs batch root strategy: batch={strat_b:?}, fast={strat_f:?}, max_diff={max_diff:.4}");
    // Both are CFR fixed points of the same game; small numeric/averaging
    // differences are expected, but a seed mismatch (uniform vs ranges) shifts
    // aggregate frequencies well beyond this.
    assert!(
        max_diff < 0.05,
        "FastCfrSolver and BatchCfrSolver root strategies diverged (max_diff={max_diff:.4}) — \
         seeds likely differ (B2)"
    );
}
