//! Smoke tests for the flop report writers: files exist, headers match,
//! frequencies parse and lie in [0, 1].

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{combo_index, Range};
use gto_hu::reports::{
    tree_stats, write_flop_strategy_csv, write_flop_summary_json, write_turn_aggregate_csv,
    FlopSolverStats,
};
use gto_hu::solver::{dense_table_bytes, CfrVariant, ChanceMode, FlopSolver};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig, RaiseRule, StreetConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn build_trained() -> FlopSolver {
    let simple = |pcts: Vec<u32>| StreetConfig {
        bet_pcts: pcts,
        allow_allin_bet: false,
        raise: RaiseRule::None,
        max_raises: 0,
    };
    let cfg = FlopTreeConfig {
        flop: simple(vec![50]),
        turn: simple(vec![50]),
        river: simple(vec![]),
    };
    let board = [c("2c"), c("7d"), c("9h")];
    let tree = build_flop_tree(20 * BB, 90 * BB, &cfg);
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &[(c("Qc"), c("Tc")), (c("Ah"), c("Ad"))] {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &[(c("Kh"), c("Qh")), (c("8s"), c("8d"))] {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut solver = FlopSolver::new(
        tree,
        board,
        [r0, r1],
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed: 5 },
    );
    solver.run(2_000);
    solver
}

#[test]
fn writers_produce_wellformed_files() {
    let solver = build_trained();
    let dir = std::env::temp_dir().join("gto_hu_test_flop_reports");
    std::fs::create_dir_all(&dir).unwrap();

    let flop_csv = dir.join("strategy_flop.csv");
    write_flop_strategy_csv(&flop_csv, &solver).unwrap();
    let body = std::fs::read_to_string(&flop_csv).unwrap();
    let mut lines = body.lines();
    assert_eq!(lines.next().unwrap(), "node_id,actor,combo,action,freq");
    let mut rows = 0;
    for line in lines {
        let cols: Vec<&str> = line.split(',').collect();
        assert_eq!(cols.len(), 5, "bad row: {line}");
        let f: f64 = cols[4].parse().unwrap();
        assert!((0.0..=1.0).contains(&f));
        rows += 1;
    }
    assert!(rows > 0, "flop strategy csv must not be empty");

    let turn_csv = dir.join("strategy_turn_agg.csv");
    write_turn_aggregate_csv(&turn_csv, &solver).unwrap();
    let body = std::fs::read_to_string(&turn_csv).unwrap();
    assert!(body.starts_with("node_id,turn,actor,action,freq\n"));
    // 49 turn cards × ≥1 action rows per turn node.
    assert!(body.lines().count() > 49);

    let json_path = dir.join("summary.json");
    let ts = tree_stats(&solver.tree);
    let stats = FlopSolverStats {
        iterations: 50,
        elapsed_secs: 0.1,
        mode: "enumerate".into(),
        expl: solver.exploitability_bb(),
        game_value_bb: solver.game_value_p0(),
        root_strategy: solver.aggregate_strategy(0, None, None),
    };
    write_flop_summary_json(
        &json_path,
        &solver.flop_board,
        &stats,
        &ts,
        solver.table_bytes(),
        dense_table_bytes(&solver.tree),
    )
    .unwrap();
    let json = std::fs::read_to_string(&json_path).unwrap();
    assert!(json.contains("\"board\":\"2c7d9h\""));
    assert!(json.contains("dense_table_bytes"));
    assert!(json.contains("flop_root_strategy"));

    std::fs::remove_dir_all(&dir).ok();
}
