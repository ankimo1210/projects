//! Turn+river solver exports (CSV + minimal JSON, no external deps).
//!
//! `strategy_turn.csv` is per-combo (turn-street nodes only). The river
//! side would be ~6M rows per-combo, so `strategy_river_agg.csv` exports
//! range-aggregate frequencies per (node, river card) instead; per-combo
//! river strategies remain available via `TurnRiverSolver::average_strategy`.

use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use super::{card_str, TreeStats};
use crate::game::Street;
use crate::ranges::all_combos;
use crate::solver::{ExplReport, TurnRiverSolver};

#[derive(Debug, Clone)]
pub struct TurnSolverStats {
    pub iterations: u32,
    pub elapsed_secs: f64,
    /// "enumerate" or "sample(seed=N)".
    pub mode: String,
    pub expl: ExplReport,
    /// Avg-vs-avg game value to player 0 (SB/IP), bb/hand.
    pub game_value_bb: f64,
    pub root_strategy: Vec<(String, f64)>,
}

/// Per-combo average strategy for turn-street action nodes.
pub fn write_turn_strategy_csv(path: &Path, solver: &TurnRiverSolver) -> std::io::Result<()> {
    let combos = all_combos();
    let mut out = String::from("node_id,actor,combo,action,freq\n");
    for node_id in solver.action_node_ids() {
        if solver.tree.nodes[node_id].state.street != Street::Turn {
            continue;
        }
        let actor = solver.actor_at(node_id);
        let node = &solver.tree.nodes[node_id];
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            if solver.export_weight(actor as usize, None, c) == 0.0 {
                continue;
            }
            let strat = solver.average_strategy(node_id, None, c);
            for (a, (act, _)) in node.children.iter().enumerate() {
                if strat[a] > 0.001 {
                    let _ = writeln!(
                        out,
                        "{node_id},{actor},{}{},{},{:.4}",
                        card_str(ca),
                        card_str(cb),
                        act.label(),
                        strat[a]
                    );
                }
            }
        }
    }
    fs::write(path, out)
}

/// Range-aggregate river strategy per (node, river card).
pub fn write_river_aggregate_csv(path: &Path, solver: &TurnRiverSolver) -> std::io::Result<()> {
    let mut out = String::from("node_id,river,actor,action,freq\n");
    for node_id in solver.action_node_ids() {
        if solver.tree.nodes[node_id].state.street != Street::River {
            continue;
        }
        let actor = solver.actor_at(node_id);
        for (i, &card) in solver.rivers().iter().enumerate() {
            for (act, f) in solver.aggregate_strategy(node_id, Some(i)) {
                let _ = writeln!(out, "{node_id},{},{actor},{act},{f:.4}", card_str(card));
            }
        }
    }
    fs::write(path, out)
}

/// Minimal flat JSON summary (no external deps).
pub fn write_turn_summary_json(
    path: &Path,
    board: &[u8; 4],
    stats: &TurnSolverStats,
    ts: &TreeStats,
    table_bytes: usize,
) -> std::io::Result<()> {
    let board_s: String = board.iter().map(|&c| card_str(c)).collect();
    let root: String = stats
        .root_strategy
        .iter()
        .map(|(a, f)| format!("{{\"action\":\"{a}\",\"freq\":{f:.5}}}"))
        .collect::<Vec<_>>()
        .join(",");
    let json = format!(
        concat!(
            "{{\"solver\":\"gto-hu vector turn+river (abstract HU NLHE equilibrium solver)\",",
            "\"board\":\"{}\",\"mode\":\"{}\",\"iterations\":{},\"elapsed_secs\":{:.2},",
            "\"exploitability_bb\":{:.6},\"br_sb_bb\":{:.6},\"br_bb_bb\":{:.6},",
            "\"game_value_sb_bb\":{:.6},",
            "\"tree\":{{\"nodes\":{},\"action_nodes\":{},\"chance_nodes\":{},",
            "\"fold_terminals\":{},\"showdowns\":{},\"table_bytes\":{}}},",
            "\"turn_root_strategy\":[{}]}}\n"
        ),
        board_s,
        stats.mode,
        stats.iterations,
        stats.elapsed_secs,
        stats.expl.exploitability,
        stats.expl.br_value[0],
        stats.expl.br_value[1],
        stats.game_value_bb,
        ts.total_nodes,
        ts.action_nodes,
        ts.chance_nodes,
        ts.fold_terminals,
        ts.showdown_terminals,
        table_bytes,
        root,
    );
    fs::write(path, json)
}
