//! Preflop solver exports (CSV + minimal JSON, no external deps).
//!
//! The summary records the simplified value model (seeded MC all-in
//! equity) so exported numbers can never be mistaken for full-game
//! equilibria (spec §13 Phase 5).

use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use super::card_str;
use crate::ranges::all_combos;
use crate::solver::{ExplReport, PreflopSolver};
use crate::tree::NodeKind;

#[derive(Debug, Clone)]
pub struct PreflopSolverStats {
    pub iterations: u32,
    pub elapsed_secs: f64,
    pub equity_seed: u64,
    pub equity_samples: u32,
    pub expl: ExplReport,
    /// Avg-vs-avg game value to player 0 (SB), bb/hand, within the model.
    pub game_value_bb: f64,
    pub root_strategy: Vec<(String, f64)>,
}

/// 169-grid label for a combo: "AA", "AKs", "AKo", …
pub fn class_label(a: u8, b: u8) -> String {
    const RANKS: [char; 13] = [
        '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A',
    ];
    let (ra, sa) = ((a / 4) as usize, a % 4);
    let (rb, sb) = ((b / 4) as usize, b % 4);
    let (hi, lo) = if ra >= rb { (ra, rb) } else { (rb, ra) };
    if hi == lo {
        format!("{}{}", RANKS[hi], RANKS[lo])
    } else if sa == sb {
        format!("{}{}s", RANKS[hi], RANKS[lo])
    } else {
        format!("{}{}o", RANKS[hi], RANKS[lo])
    }
}

/// One CSV row per (node, combo, action) with avg frequency > 0.001.
pub fn write_preflop_strategy_csv(path: &Path, solver: &PreflopSolver) -> std::io::Result<()> {
    let combos = all_combos();
    let mut out = String::from("node_id,actor,combo,class,action,freq\n");
    for node_id in solver.action_node_ids() {
        let actor = solver.actor_at(node_id);
        let node = &solver.tree.nodes[node_id];
        for (ci, &(ca, cb)) in combos.iter().enumerate() {
            if solver.ranges[actor as usize].weights[ci] == 0.0 {
                continue;
            }
            let strat = solver.average_strategy(node_id, ci);
            for (a, (act, _)) in node.children.iter().enumerate() {
                if strat[a] > 0.001 {
                    let _ = writeln!(
                        out,
                        "{node_id},{actor},{}{},{},{},{:.4}",
                        card_str(ca),
                        card_str(cb),
                        class_label(ca, cb),
                        act.label(),
                        strat[a]
                    );
                }
            }
        }
    }
    fs::write(path, out)
}

/// Root strategy aggregated to the 169 hand classes (range-weighted).
pub fn write_preflop_class_csv(path: &Path, solver: &PreflopSolver) -> std::io::Result<()> {
    use std::collections::BTreeMap;
    let combos = all_combos();
    let node = &solver.tree.nodes[0];
    let na = node.children.len();
    let actor = solver.actor_at(0) as usize;
    // class → (Σ w·freq per action, Σ w)
    let mut agg: BTreeMap<String, (Vec<f64>, f64)> = BTreeMap::new();
    for (ci, &(ca, cb)) in combos.iter().enumerate() {
        let w = solver.ranges[actor].weights[ci];
        if w == 0.0 {
            continue;
        }
        let strat = solver.average_strategy(0, ci);
        let entry = agg
            .entry(class_label(ca, cb))
            .or_insert_with(|| (vec![0.0; na], 0.0));
        for a in 0..na {
            entry.0[a] += w * strat[a];
        }
        entry.1 += w;
    }
    let mut out = String::from("class,action,freq\n");
    for (class, (sums, total)) in agg {
        for (a, (act, _)) in node.children.iter().enumerate() {
            let _ = writeln!(out, "{class},{},{:.4}", act.label(), sums[a] / total);
        }
    }
    fs::write(path, out)
}

/// Minimal flat JSON summary (no external deps).
pub fn write_preflop_summary_json(
    path: &Path,
    stack_bb: f64,
    stats: &PreflopSolverStats,
    solver: &PreflopSolver,
) -> std::io::Result<()> {
    let mut action_nodes = 0;
    let mut fold_terminals = 0;
    let mut street_ends = 0;
    for n in &solver.tree.nodes {
        match n.kind {
            NodeKind::Action { .. } => action_nodes += 1,
            NodeKind::FoldTerminal { .. } => fold_terminals += 1,
            NodeKind::NextStreet { .. } => street_ends += 1,
            _ => {}
        }
    }
    let root: String = stats
        .root_strategy
        .iter()
        .map(|(a, f)| format!("{{\"action\":\"{a}\",\"freq\":{f:.5}}}"))
        .collect::<Vec<_>>()
        .join(",");
    let json = format!(
        concat!(
            "{{\"solver\":\"gto-hu preflop (abstract HU NLHE, simplified value model)\",",
            "\"model\":\"allin-equity MC(seed={},samples={}) — NOT a full-game equilibrium\",",
            "\"stack_bb\":{},\"iterations\":{},\"elapsed_secs\":{:.2},",
            "\"exploitability_model_bb\":{:.6},\"br_sb_bb\":{:.6},\"br_bb_bb\":{:.6},",
            "\"game_value_sb_bb\":{:.6},",
            "\"tree\":{{\"nodes\":{},\"action_nodes\":{},\"fold_terminals\":{},",
            "\"street_end_leaves\":{}}},",
            "\"sb_root_strategy\":[{}]}}\n"
        ),
        stats.equity_seed,
        stats.equity_samples,
        stack_bb,
        stats.iterations,
        stats.elapsed_secs,
        stats.expl.exploitability,
        stats.expl.br_value[0],
        stats.expl.br_value[1],
        stats.game_value_bb,
        solver.tree.nodes.len(),
        action_nodes,
        fold_terminals,
        street_ends,
        root,
    );
    fs::write(path, json)
}
