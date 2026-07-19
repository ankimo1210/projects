//! `solver-bench` — P0a audit driver for named reference cases.

use std::process::exit;
use std::time::Instant;

use gto_hu::bench::{
    cpu_model, geometric_schedule, kernel_release, peak_rss_mb, reference_cases,
    run_with_checkpoints, RunRecord,
};

fn usage() -> ! {
    eprintln!(
        "usage: solver-bench --case NAME --iterations N [--points K=10] \
         [--threads T=0] [--seed S=42] [--label STR] \
         [--git-commit SHA] [--dirty 0|1] [--out FILE] | --list"
    );
    exit(2);
}

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let args = &argv[1..];
    let mut case_name = String::new();
    let mut iterations = 0u32;
    let mut points = 10usize;
    let mut threads = 0usize;
    let mut seed = 42u64;
    let mut label = String::new();
    let mut git_commit = String::new();
    let mut dirty = false;
    let mut out = None;

    let mut index = 0;
    while index < args.len() {
        let need = |index: usize| args.get(index + 1).cloned().unwrap_or_else(|| usage());
        match args[index].as_str() {
            "--list" => {
                for case in reference_cases() {
                    println!("{}", case.name);
                }
                return;
            }
            "--case" => {
                case_name = need(index);
                index += 2;
            }
            "--iterations" => {
                iterations = need(index).parse().unwrap_or_else(|_| usage());
                index += 2;
            }
            "--points" => {
                points = need(index).parse().unwrap_or_else(|_| usage());
                index += 2;
            }
            "--threads" => {
                threads = need(index).parse().unwrap_or_else(|_| usage());
                index += 2;
            }
            "--seed" => {
                seed = need(index).parse().unwrap_or_else(|_| usage());
                index += 2;
            }
            "--label" => {
                label = need(index);
                index += 2;
            }
            "--git-commit" => {
                git_commit = need(index);
                index += 2;
            }
            "--dirty" => {
                dirty = match need(index).as_str() {
                    "0" => false,
                    "1" => true,
                    _ => usage(),
                };
                index += 2;
            }
            "--out" => {
                out = Some(need(index));
                index += 2;
            }
            _ => usage(),
        }
    }

    if case_name.is_empty() || iterations == 0 || points == 0 {
        usage();
    }
    if threads > 0 {
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build_global()
            .expect("rayon pool already initialized");
    }

    let case = reference_cases()
        .into_iter()
        .find(|case| case.name == case_name)
        .unwrap_or_else(|| {
            eprintln!("unknown case '{case_name}' (use --list)");
            exit(2);
        });

    eprintln!("building {case_name} (seed {seed}) …");
    let build_start = Instant::now();
    let mut solver = (case.build)(seed);
    let build_s = build_start.elapsed().as_secs_f64();
    eprintln!(
        "built in {build_s:.1}s, table_bytes = {}",
        solver.table_bytes()
    );

    let schedule = geometric_schedule(iterations, points);
    let (checkpoints, mut timing) = run_with_checkpoints(&mut solver, &schedule);
    timing.build_s = build_s;
    for checkpoint in &checkpoints {
        eprintln!(
            "iters {:>7}  solve {:>9.1}s  br {:>7.1}s  expl {:.4} bb  \
             (br0 {:.4} / br1 {:.4})",
            checkpoint.iters,
            checkpoint.solve_s,
            checkpoint.br_s,
            checkpoint.expl,
            checkpoint.br[0],
            checkpoint.br[1]
        );
    }

    let record = RunRecord {
        schema_version: 1,
        case: case_name,
        config: case.config.to_string(),
        label,
        git_commit,
        dirty,
        seed,
        iterations,
        points,
        threads: if threads == 0 {
            rayon::current_num_threads()
        } else {
            threads
        },
        build_profile: if cfg!(debug_assertions) {
            "debug"
        } else {
            "release"
        },
        cpu: cpu_model(),
        kernel: kernel_release(),
        cmdline: argv.join(" "),
        table_bytes: solver.table_bytes(),
        peak_rss_mb: peak_rss_mb(),
        resume_count: 0,
        timing,
        checkpoints,
    };
    let json = record.to_json();

    match out {
        Some(path) => {
            if let Some(parent) = std::path::Path::new(&path).parent() {
                if !parent.as_os_str().is_empty() {
                    std::fs::create_dir_all(parent).expect("create output directory");
                }
            }
            std::fs::write(&path, json).expect("write RunRecord JSON");
            eprintln!("wrote {path}");
        }
        None => print!("{json}"),
    }
}
