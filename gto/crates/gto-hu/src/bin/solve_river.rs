//! solve-hu-river — exact-combo HU river solver (abstract action set).
//!
//! Example:
//!   solve-hu-river --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{tree_stats, write_strategy_csv, write_summary_json, SolverStats};
use gto_hu::solver::{CfrVariant, VectorRiverSolver};
use gto_hu::tree::{build_river_tree, StreetConfig};

fn usage() -> ! {
    eprintln!(
        "usage: solve-hu-river --board AhKd7s2c9h --pot <bb> --stack <bb> \
         [--iterations N=10000] [--variant cfr+|dcfr] [--out DIR]"
    );
    exit(2);
}

fn parse_board(s: &str) -> Result<[u8; 5], String> {
    if s.len() != 10 {
        return Err(format!("board must be 10 chars (5 cards), got '{s}'"));
    }
    let mut board = [0u8; 5];
    for i in 0..5 {
        let cs = &s[i * 2..i * 2 + 2];
        board[i] = parse_card(cs).ok_or_else(|| format!("bad card '{cs}'"))?;
    }
    let mut seen = [false; 52];
    for &card in &board {
        if seen[card as usize] {
            return Err(format!("duplicate card in board '{s}'"));
        }
        seen[card as usize] = true;
    }
    Ok(board)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut board: Option<[u8; 5]> = None;
    let mut pot_bb: Option<f64> = None;
    let mut stack_bb: Option<f64> = None;
    let mut iterations: u32 = 10_000;
    let mut variant = CfrVariant::cfr_plus_default();
    let mut out_dir: Option<PathBuf> = None;
    let mut board_raw = String::new();

    let mut i = 0;
    while i < args.len() {
        let need = |i: usize| args.get(i + 1).cloned().unwrap_or_else(|| usage());
        match args[i].as_str() {
            "--board" => {
                board_raw = need(i);
                board = Some(parse_board(&board_raw).unwrap_or_else(|e| {
                    eprintln!("error: {e}");
                    exit(2);
                }));
                i += 2;
            }
            "--pot" => {
                pot_bb = need(i).parse().ok();
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
            "--out" => {
                out_dir = Some(PathBuf::from(need(i)));
                i += 2;
            }
            _ => usage(),
        }
    }
    let (Some(board), Some(pot_bb), Some(stack_bb)) = (board, pot_bb, stack_bb) else {
        usage()
    };
    let pot = (pot_bb * BB as f64).round() as i64;
    let stack = (stack_bb * BB as f64).round() as i64;
    if pot <= 0 || pot % 2 != 0 || stack <= 0 {
        eprintln!("error: pot must be positive and split evenly; stack must be positive");
        exit(2);
    }

    let tree = build_river_tree(pot, stack, &StreetConfig::srp_river());
    let ts = tree_stats(&tree);
    eprintln!(
        "tree: {} nodes ({} action, {} fold, {} showdown), ~{:.1} MB tables",
        ts.total_nodes,
        ts.action_nodes,
        ts.fold_terminals,
        ts.showdown_terminals,
        ts.memory_estimate_bytes as f64 / 1e6
    );

    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut solver = VectorRiverSolver::new(tree, board, ranges, variant);

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
    let expl = solver.exploitability_bb();
    let elapsed = start.elapsed().as_secs_f64();

    let root = solver.aggregate_strategy(0);
    println!("\n== solve-hu-river (abstract HU NLHE equilibrium solver) ==");
    println!("board {board_raw}  pot {pot_bb}bb  stack {stack_bb}bb  iters {iterations}");
    println!(
        "exploitability: {:.4} bb/hand (BR sb {:.4}, BR bb {:.4})",
        expl.exploitability, expl.br_value[0], expl.br_value[1]
    );
    println!("OOP (BB) root strategy:");
    for (action, freq) in &root {
        println!("  {action:<14} {:>6.2}%", freq * 100.0);
    }

    let out = out_dir.unwrap_or_else(|| {
        PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into()))
            .join("projects/_data/gto/hu")
            .join(format!("river_{board_raw}"))
    });
    std::fs::create_dir_all(&out).expect("create out dir");
    let stats = SolverStats {
        iterations,
        elapsed_secs: elapsed,
        expl,
        root_strategy: root,
    };
    write_strategy_csv(&out.join("strategy.csv"), &solver).expect("write csv");
    write_summary_json(&out.join("summary.json"), &board, &stats, &ts).expect("write json");
    eprintln!("wrote {}", out.display());
}
