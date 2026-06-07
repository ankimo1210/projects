//! solve-hu-preflop — standalone HU preflop solver (Phase 5).
//!
//! Postflop play is replaced by the simplified all-in-equity value model
//! (seeded Monte-Carlo table): exploitability is exact WITHIN that model
//! and the output must not be quoted as a full-game equilibrium. The
//! full blueprint (Phase 6) connects real postflop subtrees.
//!
//! Example:
//!   solve-hu-preflop --stack 100 --iterations 800 --samples 200

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{
    write_preflop_class_csv, write_preflop_strategy_csv, write_preflop_summary_json,
    PreflopSolverStats,
};
use gto_hu::solver::{CfrVariant, EquityTable, PreflopSolver};
use gto_hu::tree::build_preflop_tree;

fn usage() -> ! {
    eprintln!(
        "usage: solve-hu-preflop --stack <bb> [--iterations N=800] \
         [--variant cfr+|dcfr] [--samples N=200] [--seed N=42] [--out DIR]"
    );
    exit(2);
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut stack_bb: Option<f64> = None;
    let mut iterations: u32 = 800;
    let mut variant = CfrVariant::cfr_plus_default();
    let mut samples: u32 = 200;
    let mut seed: u64 = 42;
    let mut out_dir: Option<PathBuf> = None;

    let mut i = 0;
    while i < args.len() {
        let need = |i: usize| args.get(i + 1).cloned().unwrap_or_else(|| usage());
        match args[i].as_str() {
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
            "--samples" => {
                samples = need(i).parse().unwrap_or_else(|_| usage());
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
            _ => usage(),
        }
    }
    let Some(stack_bb) = stack_bb else { usage() };
    let stack = (stack_bb * BB as f64).round() as i64;
    if stack <= BB {
        eprintln!("error: stack must exceed 1bb");
        exit(2);
    }

    let tree = build_preflop_tree(stack);
    eprintln!(
        "tree: {} nodes; building MC equity table (seed {seed}, {samples} samples/pair)…",
        tree.nodes.len()
    );
    let t0 = Instant::now();
    let eq = EquityTable::monte_carlo(seed, samples);
    eprintln!("equity table ready ({:.1}s)", t0.elapsed().as_secs_f64());

    let ranges = [uniform_excluding(&[]), uniform_excluding(&[])];
    let mut solver = PreflopSolver::new(tree, ranges, variant, eq);

    let start = Instant::now();
    let chunk = (iterations / 10).max(1);
    let mut done = 0;
    while done < iterations {
        let n = chunk.min(iterations - done);
        solver.run(n);
        done += n;
        eprintln!(
            "iter {done}/{iterations}  elapsed {:.1}s",
            start.elapsed().as_secs_f64()
        );
    }
    let elapsed = start.elapsed().as_secs_f64();
    let expl = solver.exploitability_bb();
    let game_value = solver.game_value_p0();

    let root = solver.aggregate_strategy(0);
    println!("\n== solve-hu-preflop (simplified all-in-equity model — not a full-game equilibrium) ==");
    println!(
        "stack {stack_bb}bb  iters {iterations}  model MC(seed={seed},samples={samples})"
    );
    println!(
        "exploitability (model): {:.4} bb/hand (BR sb {:.4}, BR bb {:.4})",
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
            .join(format!("preflop_{stack_bb}bb"))
    });
    std::fs::create_dir_all(&out).expect("create out dir");
    let stats = PreflopSolverStats {
        iterations,
        elapsed_secs: elapsed,
        equity_seed: seed,
        equity_samples: samples,
        expl,
        game_value_bb: game_value,
        root_strategy: root,
    };
    write_preflop_strategy_csv(&out.join("strategy_preflop.csv"), &solver)
        .expect("write strategy csv");
    write_preflop_class_csv(&out.join("strategy_root_classes.csv"), &solver)
        .expect("write class csv");
    write_preflop_summary_json(&out.join("summary.json"), stack_bb, &stats, &solver)
        .expect("write json");
    eprintln!("wrote {}", out.display());
}
