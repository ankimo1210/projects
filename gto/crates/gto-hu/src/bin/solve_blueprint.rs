//! solve-hu-blueprint — Phase 6: the composed HU game over an M-flop
//! board abstraction (design: 2026-06-08-blueprint-design.md v2).
//!
//! Output discipline: results are a CFR profile with EXACT exploitability
//! on the M-flop abstract game — never an equilibrium claim, and never
//! full-NLHE exploitability (the flop sample is the dominant unmodeled
//! abstraction).
//!
//! Example (overnight-scale run):
//!   solve-hu-blueprint --flops AhKd7s,QsJh2c,8d8h3s --stack 100 \
//!     --iterations 1500 --buckets-river 16 --buckets-turn 32 \
//!     --max-table-gb 20

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use gto_core::eval::parse_card;
use gto_hu::game::{PotType, BB};
use gto_hu::ranges::{all_combos, Range};
use gto_hu::reports::class_label;
use gto_hu::solver::{
    dense_table_bytes_abstracted, Abstraction, BlueprintSolver, CfrVariant,
};
use gto_hu::tree::{build_flop_tree, build_preflop_tree, FlopTreeConfig, NodeKind};

fn usage() -> ! {
    eprintln!(
        "usage: solve-hu-blueprint --flops B1,B2,... --stack <bb> \
         [--weights w1,w2,...] [--iterations N=1500] [--variant cfr+|dcfr] \
         [--buckets-river K=16] [--buckets-turn K=32] \
         [--mode sample|enumerate] [--seed N=42] [--out DIR] [--max-table-gb G=20]"
    );
    exit(2);
}

fn parse_flop(s: &str) -> [u8; 3] {
    if s.len() != 6 {
        eprintln!("error: flop must be 6 chars (3 cards), got '{s}'");
        exit(2);
    }
    let mut f = [0u8; 3];
    for i in 0..3 {
        f[i] = parse_card(&s[i * 2..i * 2 + 2]).unwrap_or_else(|| {
            eprintln!("error: bad card in '{s}'");
            exit(2);
        });
    }
    f
}

fn config_for(pot_type: PotType) -> FlopTreeConfig {
    match pot_type {
        PotType::Limped | PotType::Srp => FlopTreeConfig::srp(),
        PotType::ThreeBet => FlopTreeConfig::threebet(),
        PotType::FourBet => FlopTreeConfig::fourbet(),
        PotType::AllInPreflop => unreachable!(),
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut flops: Vec<[u8; 3]> = Vec::new();
    let mut flops_raw = String::new();
    let mut weights: Vec<f64> = Vec::new();
    let mut stack_bb: Option<f64> = None;
    let mut iterations: u32 = 1_500;
    let mut variant = CfrVariant::cfr_plus_default();
    let mut abs = Abstraction {
        buckets_river: 16,
        buckets_turn: 32,
    };
    let mut sample = true;
    let mut seed: u64 = 42;
    let mut out_dir: Option<PathBuf> = None;
    let mut max_table_gb: f64 = 20.0;

    let mut i = 0;
    while i < args.len() {
        let need = |i: usize| args.get(i + 1).cloned().unwrap_or_else(|| usage());
        match args[i].as_str() {
            "--flops" => {
                flops_raw = need(i);
                flops = flops_raw.split(',').map(parse_flop).collect();
                i += 2;
            }
            "--weights" => {
                weights = need(i)
                    .split(',')
                    .map(|w| w.parse().unwrap_or_else(|_| usage()))
                    .collect();
                i += 2;
            }
            "--stack" => {
                stack_bb = need(i).parse().ok();
                i += 2;
            }
            "--iterations" => {
                iterations = need(i).parse().unwrap_or_else(|_| usage());
                i += 2;
            }
            "--variant" => {
                variant = match need(i).as_str() {
                    "cfr+" => CfrVariant::cfr_plus_default(),
                    "dcfr" => CfrVariant::dcfr_default(),
                    v => {
                        eprintln!("unknown variant '{v}'");
                        exit(2);
                    }
                };
                i += 2;
            }
            "--buckets-river" => {
                abs.buckets_river = need(i).parse().unwrap_or_else(|_| usage());
                i += 2;
            }
            "--buckets-turn" => {
                abs.buckets_turn = need(i).parse().unwrap_or_else(|_| usage());
                i += 2;
            }
            "--mode" => {
                sample = match need(i).as_str() {
                    "sample" => true,
                    "enumerate" => false,
                    m => {
                        eprintln!("unknown mode '{m}'");
                        exit(2);
                    }
                };
                i += 2;
            }
            "--seed" => {
                seed = need(i).parse().unwrap_or_else(|_| usage());
                i += 2;
            }
            "--out" => {
                out_dir = Some(PathBuf::from(need(i)));
                i += 2;
            }
            "--max-table-gb" => {
                max_table_gb = need(i).parse().unwrap_or_else(|_| usage());
                i += 2;
            }
            _ => usage(),
        }
    }
    if flops.is_empty() {
        usage();
    }
    let Some(stack_bb) = stack_bb else { usage() };
    let m = flops.len();
    if weights.is_empty() {
        weights = vec![1.0 / m as f64; m];
    }
    if weights.len() != m {
        eprintln!("error: {} weights for {m} flops", weights.len());
        exit(2);
    }
    let stack = (stack_bb * BB as f64).round() as i64;

    // Memory gate BEFORE any allocation (per-leaf dense × M).
    let preflop_tree = build_preflop_tree(stack);
    let mut total_dense = 0usize;
    eprintln!("per-leaf dense tables (× {m} flops, K_r={}, K_t={}):", abs.buckets_river, abs.buckets_turn);
    for node in &preflop_tree.nodes {
        if let NodeKind::NextStreet { pot_type } = node.kind {
            if pot_type == PotType::AllInPreflop {
                continue;
            }
            let sub = build_flop_tree(node.state.pot(), node.state.stacks[0], &config_for(pot_type));
            let dense = dense_table_bytes_abstracted(&sub, abs);
            eprintln!(
                "  {:?} pot {:.1}bb stack {:.1}bb: {:.2} GB × {m}",
                pot_type,
                node.state.pot() as f64 / 100.0,
                node.state.stacks[0] as f64 / 100.0,
                dense as f64 / 1e9
            );
            total_dense += dense * m;
        }
    }
    eprintln!("total dense tables: {:.2} GB", total_dense as f64 / 1e9);
    if total_dense as f64 > max_table_gb * 1e9 {
        eprintln!(
            "error: {:.2} GB exceeds --max-table-gb {max_table_gb}. Lower \
             --buckets-river/--buckets-turn, reduce M, or raise the gate.",
            total_dense as f64 / 1e9
        );
        exit(1);
    }

    eprintln!("building exact all-in equity tables for {m} flops…");
    let t0 = Instant::now();
    let ranges = [Range::new_uniform(), Range::new_uniform()];
    let mut solver = BlueprintSolver::new(
        preflop_tree,
        ranges,
        variant,
        flops.clone(),
        weights.clone(),
        abs,
        sample,
        seed,
    );
    eprintln!("setup done ({:.1}s)", t0.elapsed().as_secs_f64());

    let start = Instant::now();
    let chunk = (iterations / 20).max(1);
    let mut done = 0;
    while done < iterations {
        let n = chunk.min(iterations - done);
        solver.run(n);
        done += n;
        eprintln!(
            "iter {done}/{iterations}  elapsed {:.1}s  tables {:.2} GB",
            start.elapsed().as_secs_f64(),
            solver.table_bytes() as f64 / 1e9
        );
    }
    let elapsed = start.elapsed().as_secs_f64();
    eprintln!("computing exact best response on the M-flop game…");
    let expl = solver.exploitability_bb();
    let game_value = solver.game_value_p0();

    let root = solver.aggregate_strategy(0);
    println!("\n== solve-hu-blueprint ==");
    println!(
        "CFR profile with EXACT exploitability on the {m}-flop abstract game \
         (flops: {flops_raw}; weights {:?}) — NOT full-NLHE exploitability",
        weights
    );
    println!(
        "stack {stack_bb}bb  iters {iterations}  K_r={} K_t={}  mode {}",
        abs.buckets_river,
        abs.buckets_turn,
        if sample { "sample" } else { "enumerate" }
    );
    println!(
        "exploitability (M-flop game): {:.4} bb/hand (BR sb {:.4}, BR bb {:.4})",
        expl.exploitability, expl.br_value[0], expl.br_value[1]
    );
    println!("game value (SB, avg vs avg): {game_value:.4} bb/hand");
    println!("SB root strategy:");
    for (action, freq) in &root {
        println!("  {action:<14} {:>6.2}%", freq * 100.0);
    }

    let out = out_dir.unwrap_or_else(|| {
        PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into()))
            .join("projects/_data/gto/hu")
            .join(format!("blueprint_{stack_bb}bb_m{m}"))
    });
    std::fs::create_dir_all(&out).expect("create out dir");

    // Preflop strategy CSV (per combo per action node).
    let combos = all_combos();
    let mut csv = String::from("node_id,actor,combo,class,action,freq\n");
    for (node_id, node) in solver.preflop_tree.nodes.iter().enumerate() {
        let NodeKind::Action { actor } = node.kind else {
            continue;
        };
        for (ci, &(ca, cb)) in combos.iter().enumerate() {
            let strat = solver.average_strategy(node_id, ci);
            for (a, (act, _)) in node.children.iter().enumerate() {
                if strat[a] > 0.001 {
                    use std::fmt::Write as _;
                    let _ = writeln!(
                        csv,
                        "{node_id},{actor},{},{},{},{:.4}",
                        format_args!("{}{}", card_str(ca), card_str(cb)),
                        class_label(ca, cb),
                        act.label(),
                        strat[a]
                    );
                }
            }
        }
    }
    std::fs::write(out.join("strategy_preflop.csv"), csv).expect("write csv");

    let root_json: String = root
        .iter()
        .map(|(a, f)| format!("{{\"action\":\"{a}\",\"freq\":{f:.5}}}"))
        .collect::<Vec<_>>()
        .join(",");
    let weights_json: String = weights
        .iter()
        .map(|w| format!("{w:.6}"))
        .collect::<Vec<_>>()
        .join(",");
    let json = format!(
        concat!(
            "{{\"solver\":\"gto-hu blueprint — CFR profile with exact exploitability ",
            "on the M-flop abstract game (NOT full-NLHE)\",",
            "\"flops\":\"{}\",\"weights\":[{}],\"stack_bb\":{},",
            "\"buckets_river\":{},\"buckets_turn\":{},\"iterations\":{},",
            "\"elapsed_secs\":{:.2},\"exploitability_mflop_bb\":{:.6},",
            "\"br_sb_bb\":{:.6},\"br_bb_bb\":{:.6},\"game_value_sb_bb\":{:.6},",
            "\"sb_root_strategy\":[{}]}}\n"
        ),
        flops_raw,
        weights_json,
        stack_bb,
        abs.buckets_river,
        abs.buckets_turn,
        iterations,
        elapsed,
        expl.exploitability,
        expl.br_value[0],
        expl.br_value[1],
        game_value,
        root_json,
    );
    std::fs::write(out.join("summary.json"), json).expect("write json");
    eprintln!("wrote {}", out.display());
}

fn card_str(c: u8) -> String {
    const RANKS: [char; 13] = [
        '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A',
    ];
    const SUITS: [char; 4] = ['c', 'd', 'h', 's'];
    format!("{}{}", RANKS[(c / 4) as usize], SUITS[(c % 4) as usize])
}
