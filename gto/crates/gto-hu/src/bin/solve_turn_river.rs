//! solve-hu-turn-river — exact-combo HU turn+river solver (abstract action
//! set, river dealt as a public chance node).
//!
//! Example:
//!   solve-hu-turn-river --board AhKd7s2c --pot 20 --stack 90 --iterations 10000
//!
//! Default training mode is public chance sampling (seeded, reproducible);
//! pass `--mode enumerate` for exact-but-slow training. The reported
//! exploitability is always exact (enumerated best response).

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{
    tree_stats, write_river_aggregate_csv, write_turn_strategy_csv, write_turn_summary_json,
    TurnSolverStats,
};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, TurnTreeConfig};

fn usage() -> ! {
    eprintln!(
        "usage: solve-hu-turn-river --board AhKd7s2c --pot <bb> --stack <bb> \
         [--iterations N=10000] [--variant cfr+|dcfr] \
         [--mode sample|enumerate] [--seed N=42] [--out DIR]"
    );
    exit(2);
}

fn parse_board(s: &str) -> Result<[u8; 4], String> {
    if s.len() != 8 {
        return Err(format!("board must be 8 chars (4 cards), got '{s}'"));
    }
    let mut board = [0u8; 4];
    for i in 0..4 {
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
    let mut board: Option<[u8; 4]> = None;
    let mut pot_bb: Option<f64> = None;
    let mut stack_bb: Option<f64> = None;
    let mut iterations: u32 = 10_000;
    let mut variant = CfrVariant::cfr_plus_default();
    let mut sample = true;
    let mut seed: u64 = 42;
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

    let tree = build_turn_river_tree(pot, stack, &TurnTreeConfig::srp());
    let ts = tree_stats(&tree);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let solver_start = Instant::now();
    let mut solver = TurnRiverSolver::new(tree, board, ranges, variant, mode);
    eprintln!(
        "tree: {} nodes ({} action, {} chance, {} fold, {} showdown), {:.1} MB tables ({:.1}s setup)",
        ts.total_nodes,
        ts.action_nodes,
        ts.chance_nodes,
        ts.fold_terminals,
        ts.showdown_terminals,
        solver.table_bytes() as f64 / 1e6,
        solver_start.elapsed().as_secs_f64()
    );

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
    eprintln!("computing exact best response…");
    let expl = solver.exploitability_bb();
    let game_value = solver.game_value_p0();

    let root = solver.aggregate_strategy(0, None);
    println!("\n== solve-hu-turn-river (abstract HU NLHE equilibrium solver) ==");
    println!(
        "board {board_raw}  pot {pot_bb}bb  stack {stack_bb}bb  iters {iterations}  mode {mode_label}"
    );
    println!(
        "exploitability: {:.4} bb/hand (BR sb {:.4}, BR bb {:.4})",
        expl.exploitability, expl.br_value[0], expl.br_value[1]
    );
    println!("game value (SB/IP, avg vs avg): {game_value:.4} bb/hand");
    println!("OOP (BB) turn root strategy:");
    for (action, freq) in &root {
        println!("  {action:<14} {:>6.2}%", freq * 100.0);
    }

    let out = out_dir.unwrap_or_else(|| {
        PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into()))
            .join("projects/_data/gto/hu")
            .join(format!("turnriver_{board_raw}"))
    });
    std::fs::create_dir_all(&out).expect("create out dir");
    let stats = TurnSolverStats {
        iterations,
        elapsed_secs: elapsed,
        mode: mode_label,
        expl,
        game_value_bb: game_value,
        root_strategy: root,
    };
    write_turn_strategy_csv(&out.join("strategy_turn.csv"), &solver).expect("write turn csv");
    write_river_aggregate_csv(&out.join("strategy_river_agg.csv"), &solver)
        .expect("write river csv");
    write_turn_summary_json(&out.join("summary.json"), &board, &stats, &ts, solver.table_bytes())
        .expect("write json");
    eprintln!("wrote {}", out.display());
}
