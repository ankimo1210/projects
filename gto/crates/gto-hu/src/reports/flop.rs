//! Flop solver exports (CSV + minimal JSON, no external deps).
//!
//! `strategy_flop.csv` is per-combo (flop-street nodes only).
//! `strategy_turn_agg.csv` exports range-aggregate frequencies per
//! (node, turn card); the per-(turn, river) river aggregate would be
//! ~2352 contexts per node, so river strategies stay available via
//! `FlopSolver::average_strategy` / `aggregate_strategy` only.

use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use super::{card_str, TreeStats};
use crate::game::Street;
use crate::ranges::all_combos;
use crate::solver::{ExplReport, FlopSolver};

#[derive(Debug, Clone)]
pub struct FlopSolverStats {
    pub iterations: u32,
    pub elapsed_secs: f64,
    /// "enumerate" or "sample(seed=N)".
    pub mode: String,
    pub expl: ExplReport,
    /// Avg-vs-avg game value to player 0 (SB/IP), bb/hand.
    pub game_value_bb: f64,
    pub root_strategy: Vec<(String, f64)>,
}

/// Per-combo average strategy for flop-street action nodes.
pub fn write_flop_strategy_csv(path: &Path, solver: &FlopSolver) -> std::io::Result<()> {
    let combos = all_combos();
    let mut out = String::from("node_id,actor,combo,action,freq\n");
    for node_id in solver.action_node_ids() {
        if solver.tree.nodes[node_id].state.street != Street::Flop {
            continue;
        }
        let actor = solver.actor_at(node_id);
        let node = &solver.tree.nodes[node_id];
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            if solver.export_weight(actor as usize, None, None, c) == 0.0 {
                continue;
            }
            let strat = solver.average_strategy(node_id, None, None, c);
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

/// Range-aggregate turn strategy per (node, turn card).
pub fn write_turn_aggregate_csv(path: &Path, solver: &FlopSolver) -> std::io::Result<()> {
    let mut out = String::from("node_id,turn,actor,action,freq\n");
    for node_id in solver.action_node_ids() {
        if solver.tree.nodes[node_id].state.street != Street::Turn {
            continue;
        }
        let actor = solver.actor_at(node_id);
        for (i, &card) in solver.turns().iter().enumerate() {
            for (act, f) in solver.aggregate_strategy(node_id, Some(i), None) {
                let _ = writeln!(out, "{node_id},{},{actor},{act},{f:.4}", card_str(card));
            }
        }
    }
    fs::write(path, out)
}

/// Minimal flat JSON summary (no external deps).
pub fn write_flop_summary_json(
    path: &Path,
    board: &[u8; 3],
    stats: &FlopSolverStats,
    ts: &TreeStats,
    table_bytes: usize,
    dense_bytes: usize,
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
            "{{\"solver\":\"gto-hu vector flop (abstract HU NLHE equilibrium solver)\",",
            "\"board\":\"{}\",\"mode\":\"{}\",\"iterations\":{},\"elapsed_secs\":{:.2},",
            "\"exploitability_bb\":{:.6},\"br_sb_bb\":{:.6},\"br_bb_bb\":{:.6},",
            "\"game_value_sb_bb\":{:.6},",
            "\"tree\":{{\"nodes\":{},\"action_nodes\":{},\"chance_nodes\":{},",
            "\"fold_terminals\":{},\"showdowns\":{},\"table_bytes\":{},",
            "\"dense_table_bytes\":{}}},",
            "\"flop_root_strategy\":[{}]}}\n"
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
        dense_bytes,
        root,
    );
    fs::write(path, json)
}
