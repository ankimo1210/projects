//! `solver-bench` — P0a audit driver for named reference cases.

use std::io;
use std::path::{Path, PathBuf};
use std::process::exit;
use std::time::Instant;

use gto_hu::bench::{
    bench_run_fingerprint, cpu_model, geometric_schedule, kernel_release, peak_rss_mb,
    reference_cases, BenchRunState, CaseSolver, Checkpoint, RunRecord,
};
use gto_hu::checkpoint::{self, current_build_id, CheckpointInfo, CheckpointTrigger};

fn usage() -> ! {
    eprintln!(
        "usage: solver-bench --case NAME --iterations N [--points K=10] \
         [--threads T=0] [--seed S=42] [--label STR] \
         [--git-commit SHA] [--dirty 0|1] [--out FILE] \
         [--checkpoint-dir PATH] [--checkpoint-every-minutes N=30] \
         [--checkpoint-every-iters N] [--resume auto|PATH] \
         [--keep-checkpoints N=2] | --list"
    );
    exit(2);
}

fn fail(message: impl std::fmt::Display) -> ! {
    eprintln!("error: {message}");
    exit(1);
}

fn prepare_resume(
    solver: &CaseSolver,
    path: &Path,
    build_id: &str,
    run_fingerprint: u64,
) -> io::Result<(CheckpointInfo, BenchRunState)> {
    let info = solver.validate_checkpoint(path, build_id)?;
    let sidecar_path = path.with_extension("bench");
    let bytes = std::fs::read(&sidecar_path).map_err(|error| {
        io::Error::new(
            error.kind(),
            format!("read {}: {error}", sidecar_path.display()),
        )
    })?;
    let (state, snapshot_checksum) = BenchRunState::from_sidecar(&bytes)?;
    if state.run_fingerprint != run_fingerprint {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "benchmark run fingerprint mismatch: expected {run_fingerprint:016x}, got {:016x}",
                state.run_fingerprint
            ),
        ));
    }
    if state.iteration != info.iteration {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "sidecar iteration {} does not match snapshot iteration {}",
                state.iteration, info.iteration
            ),
        ));
    }
    if snapshot_checksum != info.checksum {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "sidecar snapshot checksum {snapshot_checksum:016x} does not match checkpoint {:016x}",
                info.checksum
            ),
        ));
    }
    Ok((info, state))
}

fn restore_prepared(
    solver: &mut CaseSolver,
    info: &CheckpointInfo,
    build_id: &str,
    mut state: BenchRunState,
    build_s: f64,
) -> io::Result<BenchRunState> {
    let restored = solver.restore_checkpoint(&info.path, build_id)?;
    if restored.iteration != state.iteration || restored.checksum != info.checksum {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "checkpoint changed between resume validation and restore",
        ));
    }
    state.begin_resume(restored.iteration, build_s);
    Ok(state)
}

fn resume_auto(
    solver: &mut CaseSolver,
    dir: &Path,
    build_id: &str,
    run_fingerprint: u64,
    build_s: f64,
) -> io::Result<Option<(BenchRunState, CheckpointInfo)>> {
    let candidates = match checkpoint::recovery_candidates(dir) {
        Ok(candidates) => candidates,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error),
    };
    let mut errors = Vec::new();
    for path in candidates {
        match prepare_resume(solver, &path, build_id, run_fingerprint) {
            Ok((info, state)) => {
                eprintln!(
                    "resuming {} at iteration {} ({:.2} MiB, validation {:.2}s)",
                    info.path.display(),
                    info.iteration,
                    info.bytes as f64 / (1024.0 * 1024.0),
                    info.io_s
                );
                let state = restore_prepared(solver, &info, build_id, state, build_s)?;
                return Ok(Some((state, info)));
            }
            Err(error) => errors.push(format!("{}: {error}", path.display())),
        }
    }
    Err(io::Error::new(
        io::ErrorKind::InvalidData,
        format!("no valid benchmark checkpoint pair: {}", errors.join("; ")),
    ))
}

fn save_progress(
    solver: &CaseSolver,
    state: &mut BenchRunState,
    dir: &Path,
    build_id: &str,
    keep: usize,
) -> io::Result<CheckpointInfo> {
    // Commit the large solver snapshot first. If the process dies before the
    // paired sidecar is committed, auto-resume rejects this generation and
    // falls back to the retained prior pair.
    let info = solver.save_checkpoint(dir, build_id, keep, None)?;
    state.add_checkpoint_io(info.io_s);
    let sidecar = state.to_sidecar(info.checksum);
    checkpoint::replace_companion(&info.path, &sidecar)?;
    eprintln!(
        "checkpoint {}: iter {}, {:.2} MiB, write {:.2}s",
        info.path.display(),
        info.iteration,
        info.bytes as f64 / (1024.0 * 1024.0),
        info.io_s
    );
    Ok(info)
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
    let mut out: Option<PathBuf> = None;
    let mut checkpoint_dir: Option<PathBuf> = None;
    let mut checkpoint_every_minutes = 30u64;
    let mut checkpoint_every_iters: Option<u32> = None;
    let mut checkpoint_interval_requested = false;
    let mut resume: Option<String> = None;
    let mut keep_checkpoints = 2usize;

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
            "--case" => case_name = need(index),
            "--iterations" => iterations = need(index).parse().unwrap_or_else(|_| usage()),
            "--points" => points = need(index).parse().unwrap_or_else(|_| usage()),
            "--threads" => threads = need(index).parse().unwrap_or_else(|_| usage()),
            "--seed" => seed = need(index).parse().unwrap_or_else(|_| usage()),
            "--label" => label = need(index),
            "--git-commit" => git_commit = need(index),
            "--dirty" => {
                dirty = match need(index).as_str() {
                    "0" => false,
                    "1" => true,
                    _ => usage(),
                }
            }
            "--out" => out = Some(PathBuf::from(need(index))),
            "--checkpoint-dir" => checkpoint_dir = Some(PathBuf::from(need(index))),
            "--checkpoint-every-minutes" => {
                checkpoint_every_minutes = need(index).parse().unwrap_or_else(|_| usage());
                checkpoint_interval_requested = true;
            }
            "--checkpoint-every-iters" => {
                checkpoint_every_iters = Some(need(index).parse().unwrap_or_else(|_| usage()));
                checkpoint_interval_requested = true;
            }
            "--resume" => resume = Some(need(index)),
            "--keep-checkpoints" => {
                keep_checkpoints = need(index).parse().unwrap_or_else(|_| usage())
            }
            _ => usage(),
        }
        index += 2;
    }

    if case_name.is_empty() || iterations == 0 || points == 0 || keep_checkpoints < 2 {
        usage();
    }
    if checkpoint_interval_requested && checkpoint_dir.is_none() && resume.is_none() {
        fail("checkpoint intervals require --checkpoint-dir");
    }
    if resume.as_deref() == Some("auto") && checkpoint_dir.is_none() {
        fail("--resume auto requires --checkpoint-dir");
    }
    if let Some(path) = resume.as_deref().filter(|value| *value != "auto") {
        if checkpoint_dir.is_none() {
            checkpoint_dir = Some(
                Path::new(path)
                    .parent()
                    .filter(|parent| !parent.as_os_str().is_empty())
                    .unwrap_or_else(|| Path::new("."))
                    .to_path_buf(),
            );
        }
    }
    if resume.is_none() {
        if let Some(dir) = checkpoint_dir.as_deref() {
            match checkpoint::recovery_candidates(dir) {
                Ok(_) => fail(format!(
                    "checkpoint generations already exist in {}; use --resume auto or a new directory",
                    dir.display()
                )),
                Err(error) if error.kind() == io::ErrorKind::NotFound => {}
                Err(error) => fail(error),
            }
        }
    }

    if threads > 0 {
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build_global()
            .expect("rayon pool already initialized");
    }
    let effective_threads = if threads == 0 {
        rayon::current_num_threads()
    } else {
        threads
    };

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
    if checkpoint_dir.is_some() && !solver.checkpoint_supported() {
        fail("durable checkpoints are currently supported only for flop/blueprint cases");
    }

    if git_commit.is_empty() {
        git_commit = current_build_id();
    }
    let checkpoint_build_id = format!("{git_commit};dirty={}", u8::from(dirty));
    let run_fingerprint = bench_run_fingerprint(
        &case_name,
        case.config,
        &label,
        seed,
        iterations,
        points,
        effective_threads,
    );

    let (mut state, mut active_checkpoint) = match resume.as_deref() {
        None => (BenchRunState::new(run_fingerprint, build_s), None),
        Some("auto") => resume_auto(
            &mut solver,
            checkpoint_dir.as_deref().unwrap(),
            &checkpoint_build_id,
            run_fingerprint,
            build_s,
        )
        .unwrap_or_else(|error| fail(error))
        .map(|(state, info)| (state, Some(info)))
        .unwrap_or_else(|| {
            eprintln!("no prior checkpoint found; starting a new run");
            (BenchRunState::new(run_fingerprint, build_s), None)
        }),
        Some(path) => {
            let path = Path::new(path);
            let (info, state) =
                prepare_resume(&solver, path, &checkpoint_build_id, run_fingerprint)
                    .unwrap_or_else(|error| fail(error));
            let state = restore_prepared(&mut solver, &info, &checkpoint_build_id, state, build_s)
                .unwrap_or_else(|error| fail(error));
            (state, Some(info))
        }
    };

    if state.iteration > iterations {
        fail(format!(
            "checkpoint iteration {} exceeds requested total {iterations}",
            state.iteration
        ));
    }
    let schedule = geometric_schedule(iterations, points);
    if state
        .checkpoints
        .iter()
        .any(|checkpoint| !schedule.contains(&checkpoint.iters))
    {
        fail("sidecar analytical checkpoints do not match the requested schedule");
    }

    let mut trigger = CheckpointTrigger::new(
        checkpoint_every_minutes,
        checkpoint_every_iters,
        state.iteration,
    );
    for &target in &schedule {
        if target < state.iteration {
            if !state
                .checkpoints
                .iter()
                .any(|checkpoint| checkpoint.iters == target)
            {
                fail(format!(
                    "sidecar is missing analytical checkpoint at iteration {target}"
                ));
            }
            continue;
        }
        if target == state.iteration
            && state
                .checkpoints
                .iter()
                .any(|checkpoint| checkpoint.iters == target)
        {
            continue;
        }

        if checkpoint_dir.is_some() && state.iteration < target {
            while state.iteration < target {
                let solve_start = Instant::now();
                solver.run_chunk(1);
                let next_iteration = state.iteration + 1;
                state.add_solve(next_iteration, solve_start.elapsed().as_secs_f64());
                if trigger.due(state.iteration) {
                    let info = save_progress(
                        &solver,
                        &mut state,
                        checkpoint_dir.as_deref().unwrap(),
                        &checkpoint_build_id,
                        keep_checkpoints,
                    )
                    .unwrap_or_else(|error| fail(error));
                    trigger.mark_saved(info.iteration);
                    active_checkpoint = Some(info);
                }
            }
        } else if state.iteration < target {
            let chunk = target - state.iteration;
            let solve_start = Instant::now();
            solver.run_chunk(chunk);
            state.add_solve(target, solve_start.elapsed().as_secs_f64());
        }

        let br_start = Instant::now();
        let report = solver.expl();
        let checkpoint = Checkpoint {
            iters: target,
            solve_s: state.solve_s,
            br_s: br_start.elapsed().as_secs_f64(),
            expl: report.exploitability,
            br: report.br_value,
        };
        state.add_checkpoint(checkpoint);
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

        if let Some(dir) = checkpoint_dir.as_deref() {
            if active_checkpoint.as_ref().map(|info| info.iteration) != Some(target) {
                let info = save_progress(
                    &solver,
                    &mut state,
                    dir,
                    &checkpoint_build_id,
                    keep_checkpoints,
                )
                .unwrap_or_else(|error| fail(error));
                trigger.mark_saved(info.iteration);
                active_checkpoint = Some(info);
            } else {
                // The solver generation already exists, but the just-computed
                // analytical BR must replace its sidecar atomically.
                let info = active_checkpoint.as_ref().unwrap();
                checkpoint::replace_companion(&info.path, &state.to_sidecar(info.checksum))
                    .unwrap_or_else(|error| fail(error));
            }
        }
    }

    if checkpoint_dir.is_some() {
        let info = active_checkpoint
            .as_ref()
            .unwrap_or_else(|| fail("checkpoint-enabled run has no committed generation"));
        checkpoint::replace_companion(&info.path, &state.to_sidecar(info.checksum))
            .unwrap_or_else(|error| fail(error));
    }

    let timing = state.timing();
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
        threads: effective_threads,
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
        state_checksum: solver.state_checksum(),
        resume_count: state.resume_count,
        timing,
        checkpoints: state.checkpoints,
        segments: state.segments,
    };
    let json = record.to_json();

    match out {
        Some(path) => {
            if let Some(parent) = path
                .parent()
                .filter(|parent| !parent.as_os_str().is_empty())
            {
                std::fs::create_dir_all(parent).expect("create output directory");
            }
            std::fs::write(&path, json).expect("write RunRecord JSON");
            eprintln!("wrote {}", path.display());
        }
        None => print!("{json}"),
    }
}
