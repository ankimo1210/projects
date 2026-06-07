//! Preflop solver behaviour with the real Monte-Carlo equity model:
//! table sanity, convergence within the model, and qualitative poker
//! anchors that hold under ANY sane equity table (AA never folds).

use gto_core::eval::parse_card;
use gto_hu::game::{Action, BB};
use gto_hu::ranges::{combo_index, uniform_excluding, NUM_COMBOS};
use gto_hu::solver::{pair_equity_mc, CfrVariant, EquityTable, PreflopSolver};
use gto_hu::tree::{build_preflop_tree, Tree};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

#[test]
fn mc_pair_equity_matches_known_matchups() {
    // AA vs KK ≈ 0.817 preflop; 20k samples → SE ≈ 0.003.
    let aa = (c("Ah"), c("Ad"));
    let kk = (c("Kh"), c("Kd"));
    let e = pair_equity_mc(aa, kk, 1, 20_000);
    assert!((0.79..=0.84).contains(&e), "AA vs KK equity {e:.4}");
    // AKs vs QQ ≈ 0.46 ("coin flip", suited side).
    let aks = (c("As"), c("Ks"));
    let qq = (c("Qh"), c("Qd"));
    let e2 = pair_equity_mc(aks, qq, 2, 20_000);
    assert!((0.42..=0.50).contains(&e2), "AKs vs QQ equity {e2:.4}");
}

#[test]
fn mc_table_is_zero_sum_mirrored() {
    // Tiny sample count: we only check structure, not accuracy.
    let t = EquityTable::monte_carlo(7, 10);
    let aa = combo_index(c("Ah"), c("Ad"));
    let kk = combo_index(c("Kh"), c("Kd"));
    let e = t.eq(aa, kk);
    assert!((t.eq(kk, aa) + e - 1.0).abs() < 1e-6, "mirror broken");
    assert!(e > 0.6, "AA must beat KK even at 10 samples: {e:.3}");
}

fn child_by<F: Fn(&Action) -> bool>(t: &Tree, node: usize, pred: F) -> usize {
    t.nodes[node]
        .children
        .iter()
        .find(|(a, _)| pred(a))
        .map(|&(_, id)| id)
        .expect("child not found")
}

#[test]
fn solver_converges_and_aa_plays_like_aa() {
    let tree = build_preflop_tree(100 * BB);
    let ranges = [uniform_excluding(&[]), uniform_excluding(&[])];
    let eq = EquityTable::monte_carlo(42, 50);
    let mut solver = PreflopSolver::new(tree, ranges, CfrVariant::cfr_plus_default(), eq);
    solver.run(60);
    let early = solver.exploitability_bb().exploitability;
    solver.run(240);
    let late = solver.exploitability_bb().exploitability;
    eprintln!("preflop expl: 60 iters {early:.4} → 300 iters {late:.4}");
    assert!(late < early, "exploitability must decrease");
    assert!(late < 0.05, "not converged within the model: {late:.4}");

    // Anchors valid under any sane equity table.
    let na_root = solver.tree.nodes[0].children.len();
    for aa in [
        combo_index(c("Ah"), c("Ad")),
        combo_index(c("As"), c("Ac")),
    ] {
        let s = solver.average_strategy(0, aa);
        assert!(
            s[0] < 0.02,
            "AA must not open-fold (fold freq {:.4})",
            s[0]
        );
        assert_eq!(s.len(), na_root);
    }
    // BB with AA facing the open-3bet-4bet jam line: calling is near-pure.
    let t = &solver.tree;
    let open = child_by(t, 0, |a| matches!(a, Action::Raise { to } if *to == 250));
    let threebet = child_by(t, open, |a| matches!(a, Action::Raise { to } if *to == 900));
    let fourbet = child_by(t, threebet, |a| matches!(a, Action::Raise { to } if *to == 2200));
    let jam = child_by(t, fourbet, |a| matches!(a, Action::AllIn { .. }));
    let aa = combo_index(c("Ah"), c("Ad"));
    let s = solver.average_strategy(jam, aa);
    // children: [fold, call]
    assert!(
        s[1] > 0.95,
        "AA must call the 4bet-jam (call freq {:.4})",
        s[1]
    );

    // Aggregate root strategy is a distribution.
    let agg = solver.aggregate_strategy(0);
    let total: f64 = agg.iter().map(|(_, f)| f).sum();
    assert!((total - 1.0).abs() < 1e-6);
    assert_eq!(agg.len(), na_root);
    let _ = NUM_COMBOS;
}
