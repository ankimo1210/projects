//! Tree/solver statistics and strategy export (CSV + minimal JSON).

use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use crate::ranges::{all_combos, NUM_COMBOS};
use crate::solver::{ExplReport, VectorRiverSolver};
use crate::tree::{NodeKind, Tree};

#[derive(Debug, Clone, Copy)]
pub struct TreeStats {
    pub total_nodes: usize,
    pub action_nodes: usize,
    pub chance_nodes: usize,
    pub fold_terminals: usize,
    pub showdown_terminals: usize,
    /// Structural estimate: regrets + strategy sums, 8 bytes each, per
    /// (node, action, combo). For chance trees this ignores the per-river-
    /// card multiplicity — use the turn solver's table accounting instead.
    pub memory_estimate_bytes: usize,
}

pub fn tree_stats(tree: &Tree) -> TreeStats {
    let mut s = TreeStats {
        total_nodes: tree.nodes.len(),
        action_nodes: 0,
        chance_nodes: 0,
        fold_terminals: 0,
        showdown_terminals: 0,
        memory_estimate_bytes: 0,
    };
    for n in &tree.nodes {
        match n.kind {
            NodeKind::Action { .. } => {
                s.action_nodes += 1;
                s.memory_estimate_bytes += 2 * 8 * n.children.len() * NUM_COMBOS;
            }
            NodeKind::FoldTerminal { .. } => s.fold_terminals += 1,
            NodeKind::Showdown => s.showdown_terminals += 1,
            NodeKind::Chance { .. } => s.chance_nodes += 1,
        }
    }
    s
}

#[derive(Debug, Clone)]
pub struct SolverStats {
    pub iterations: u32,
    pub elapsed_secs: f64,
    pub expl: ExplReport,
    pub root_strategy: Vec<(String, f64)>,
}

fn card_str(c: u8) -> String {
    let ranks = [
        '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A',
    ];
    let suits = ['c', 'd', 'h', 's'];
    format!("{}{}", ranks[(c / 4) as usize], suits[(c % 4) as usize])
}

/// One CSV row per (node, combo, action) with avg frequency > 0.001.
pub fn write_strategy_csv(path: &Path, solver: &VectorRiverSolver) -> std::io::Result<()> {
    let combos = all_combos();
    let mut out = String::from("node_id,actor,combo,action,freq\n");
    for node_id in solver.action_node_ids() {
        let actor = solver.actor_at(node_id);
        let node = &solver.tree.nodes[node_id];
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            if solver.ranges[actor as usize].weights[c] == 0.0 {
                continue;
            }
            let strat = solver.average_strategy(node_id, c);
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

/// Minimal flat JSON summary (no external deps).
pub fn write_summary_json(
    path: &Path,
    board: &[u8; 5],
    stats: &SolverStats,
    ts: &TreeStats,
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
            "{{\"solver\":\"gto-hu vector river (abstract HU NLHE equilibrium solver)\",",
            "\"board\":\"{}\",\"iterations\":{},\"elapsed_secs\":{:.2},",
            "\"exploitability_bb\":{:.6},\"br_sb_bb\":{:.6},\"br_bb_bb\":{:.6},",
            "\"tree\":{{\"nodes\":{},\"action_nodes\":{},\"fold_terminals\":{},",
            "\"showdowns\":{},\"memory_bytes\":{}}},\"root_strategy\":[{}]}}\n"
        ),
        board_s,
        stats.iterations,
        stats.elapsed_secs,
        stats.expl.exploitability,
        stats.expl.br_value[0],
        stats.expl.br_value[1],
        ts.total_nodes,
        ts.action_nodes,
        ts.fold_terminals,
        ts.showdown_terminals,
        ts.memory_estimate_bytes,
        root,
    );
    fs::write(path, json)
}
