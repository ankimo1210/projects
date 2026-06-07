use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{
    tree_stats, write_river_aggregate_csv, write_turn_strategy_csv, write_turn_summary_json,
    TurnSolverStats,
};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

#[test]
fn turn_reports_written_with_finite_exploitability() {
    let cfg = TurnTreeConfig {
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
    };
    let board = [c("2c"), c("7d"), c("9h"), c("Jh")];
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &cfg);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut s = TurnRiverSolver::new(
        tree,
        board,
        ranges,
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed: 1 },
    );
    s.run(50);

    let dir = std::env::temp_dir().join(format!("gto_hu_turn_reports_{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();

    let expl = s.exploitability_bb();
    let stats = TurnSolverStats {
        iterations: 50,
        elapsed_secs: 0.0,
        mode: "sample".into(),
        expl,
        game_value_bb: s.game_value_p0(),
        root_strategy: s.aggregate_strategy(0, None),
    };
    let ts = tree_stats(&s.tree);
    write_turn_summary_json(
        &dir.join("summary.json"),
        &board,
        &stats,
        &ts,
        s.table_bytes(),
    )
    .unwrap();
    write_turn_strategy_csv(&dir.join("strategy_turn.csv"), &s).unwrap();
    write_river_aggregate_csv(&dir.join("strategy_river_agg.csv"), &s).unwrap();

    // Deliverable: summary JSON with a finite exploitability in bb/hand.
    let json = std::fs::read_to_string(dir.join("summary.json")).unwrap();
    let expl_field = json
        .split("\"exploitability_bb\":")
        .nth(1)
        .expect("exploitability_bb field present")
        .split(',')
        .next()
        .unwrap()
        .trim()
        .parse::<f64>()
        .unwrap();
    assert!(expl_field.is_finite() && expl_field >= -1e-9);
    assert!(json.contains("\"chance_nodes\":"));
    assert!(json.contains("\"game_value_sb_bb\":"));
    assert!(json.contains("\"mode\":\"sample\""));

    let csv = std::fs::read_to_string(dir.join("strategy_turn.csv")).unwrap();
    assert!(csv.starts_with("node_id,actor,combo,action,freq"));
    assert!(csv.lines().count() > 1, "turn strategy CSV has rows");

    let rcsv = std::fs::read_to_string(dir.join("strategy_river_agg.csv")).unwrap();
    assert!(rcsv.starts_with("node_id,river,actor,action,freq"));
    assert!(rcsv.lines().count() > 1, "river aggregate CSV has rows");

    std::fs::remove_dir_all(&dir).ok();
}
