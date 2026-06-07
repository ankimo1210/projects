//! solve-hu-flop — exact-combo HU flop+turn+river solver (abstract action
//! set, turn and river dealt as nested public chance nodes).
//!
//! Example:
//!   solve-hu-flop --board AhKd7s --pot 20 --stack 90 --iterations 10000
//!
//! Default training mode is public chance sampling (seeded, reproducible):
//! the turn card is sampled, the river is always enumerated — double
//! sampling would spread river updates over 49×48 contexts and stall.
//! Pass `--mode enumerate` for exact-but-slow training. The reported
//! exploitability is always exact (both chance stages enumerated in the
//! best response).
//!
//! Memory: exact-combo tables grow with 49 turn × 48 river contexts per
//! river action node. The dense table size is printed up front and the
//! solver refuses to start above `--max-table-gb` (default 8) — full
//! 100bb SRP trees need card bucketing (design spec §8, Phase 6) and are
//! rejected here rather than silently swapping the machine to death.

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{
    tree_stats, write_flop_strategy_csv, write_flop_summary_json, write_turn_aggregate_csv,
    FlopSolverStats,
};
use gto_hu::solver::{dense_table_bytes, CfrVariant, ChanceMode, FlopSolver};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig};

fn usage() -> ! {
    eprintln!(
        "usage: solve-hu-flop --board AhKd7s --pot <bb> --stack <bb> \
         [--iterations N=10000] [--variant cfr+|dcfr] [--pot-type srp|3bp] \
         [--mode sample|enumerate] [--seed N=42] [--out DIR] [--max-table-gb G=8]"
    );
    exit(2);
}

fn parse_board(s: &str) -> Result<[u8; 3], String> {
    if s.len() != 6 {
        return Err(format!("board must be 6 chars (3 cards), got '{s}'"));
    }
    let mut board = [0u8; 3];
    for i in 0..3 {
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
    let mut board: Option<[u8; 3]> = None;
    let mut pot_bb: Option<f64> = None;
    let mut stack_bb: Option<f64> = None;
    let mut iterations: u32 = 10_000;
    let mut variant = CfrVariant::cfr_plus_default();
    let mut pot_type = "srp".to_string();
    let mut sample = true;
    let mut seed: u64 = 42;
    let mut out_dir: Option<PathBuf> = None;
    let mut max_table_gb: f64 = 8.0;
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
            "--pot-type" => {
                pot_type = need(i);
                if pot_type != "srp" && pot_type != "3bp" {
                    eprintln!("unknown pot type '{pot_type}' (srp|3bp)");
                    exit(2);
                }
                i += 2;
            }
            "--mode" => {
                sample = match need(i).as_str() {
                    "sample" => true,
                    "enumerate" => false,
                    m => {
                        eprintln!("unknown mode '{m}' (sample|enumerate)");
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
    let (Some(board), Some(pot_bb), Some(stack_bb)) = (board, pot_bb, stack_bb) else {
        usage()
    };
    let pot = (pot_bb * BB as f64).round() as i64;
    let stack = (stack_bb * BB as f64).round() as i64;
    if pot <= 0 || pot % 2 != 0 || stack <= 0 {
        eprintln!("error: pot must be positive and split evenly; stack must be positive");
        exit(2);
    }

    let cfg = match pot_type.as_str() {
        "srp" => FlopTreeConfig::srp(),
        "3bp" => FlopTreeConfig::threebet(),
        _ => unreachable!(),
    };
    let mode = if sample {
        ChanceMode::Sample { seed }
    } else {
        ChanceMode::Enumerate
    };
    let mode_label = if sample {
        format!("sample(seed={seed})")
    } else {
        "enumerate".to_string()
    };

    let tree = build_flop_tree(pot, stack, &cfg);
    let ts = tree_stats(&tree);
    let dense = dense_table_bytes(&tree);
    eprintln!(
        "tree: {} nodes ({} action, {} chance, {} fold, {} showdown), dense tables {:.2} GB",
        ts.total_nodes,
        ts.action_nodes,
        ts.chance_nodes,
        ts.fold_terminals,
        ts.showdown_terminals,
        dense as f64 / 1e9,
    );
    if dense as f64 > max_table_gb * 1e9 {
        eprintln!(
            "error: dense tables {:.2} GB exceed --max-table-gb {max_table_gb}.\n\
             Exact-combo flop solving at this size needs card bucketing \
             (design spec §8, Phase 6). Reduce the tree (--pot-type 3bp, \
             smaller stack) or raise --max-table-gb if you actually have \
             the RAM (sampled mode allocates lazily but converges dense).",
            dense as f64 / 1e9
        );
        exit(1);
    }

    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let setup_start = Instant::now();
    let mut solver = FlopSolver::new(tree, board, ranges, variant, mode);
    eprintln!(
        "showdown tables ready ({:.1}s setup)",
        setup_start.elapsed().as_secs_f64()
    );

    let start = Instant::now();
    let chunk = (iterations / 10).max(1);
    let mut done = 0;
    while done < iterations {
        let n = chunk.min(iterations - done);
        solver.run(n);
        done += n;
        eprintln!(
            "iter {done}/{iterations}  elapsed {:.1}s  tables {:.2} GB",
            start.elapsed().as_secs_f64(),
            solver.table_bytes() as f64 / 1e9,
        );
    }
    let elapsed = start.elapsed().as_secs_f64();
    eprintln!("computing exact best response (49 turns × 48 rivers enumerated)…");
    let expl = solver.exploitability_bb();
    let game_value = solver.game_value_p0();

    let root = solver.aggregate_strategy(0, None, None);
    println!("\n== solve-hu-flop (abstract HU NLHE equilibrium solver) ==");
    println!(
        "board {board_raw}  pot {pot_bb}bb  stack {stack_bb}bb  pot-type {pot_type}  \
         iters {iterations}  mode {mode_label}"
    );
    println!(
        "exploitability: {:.4} bb/hand (BR sb {:.4}, BR bb {:.4})",
        expl.exploitability, expl.br_value[0], expl.br_value[1]
    );
    println!("game value (SB/IP, avg vs avg): {game_value:.4} bb/hand");
    println!("OOP (BB) flop root strategy:");
    for (action, freq) in &root {
        println!("  {action:<14} {:>6.2}%", freq * 100.0);
    }

    let out = out_dir.unwrap_or_else(|| {
        PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into()))
            .join("projects/_data/gto/hu")
            .join(format!("flop_{board_raw}_{pot_type}"))
    });
    std::fs::create_dir_all(&out).expect("create out dir");
    let stats = FlopSolverStats {
        iterations,
        elapsed_secs: elapsed,
        mode: mode_label,
        expl,
        game_value_bb: game_value,
        root_strategy: root,
    };
    write_flop_strategy_csv(&out.join("strategy_flop.csv"), &solver).expect("write flop csv");
    write_turn_aggregate_csv(&out.join("strategy_turn_agg.csv"), &solver).expect("write turn csv");
    write_flop_summary_json(
        &out.join("summary.json"),
        &board,
        &stats,
        &ts,
        solver.table_bytes(),
        dense,
    )
    .expect("write json");
    eprintln!("wrote {}", out.display());
}
