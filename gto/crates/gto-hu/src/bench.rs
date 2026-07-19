//! P0a benchmark harness: stable reference cases for solver audit runs.
//!
//! Audit spec: `docs/superpowers/specs/2026-07-19-gtowizard-parity-ios-design.md`
//! §5.0. Long-run checkpointing and JSON records are added by later P0a tasks.

use crate::game::BB;
use crate::ranges::{uniform_excluding, NUM_COMBOS};
use crate::solver::{
    Abstraction, BlueprintSolver, CfrVariant, ChanceMode, ExplReport, FlopSolver, TurnRiverSolver,
    VectorRiverSolver,
};
use crate::tree::{
    build_flop_tree, build_preflop_tree, build_river_tree, build_turn_river_tree, FlopTreeConfig,
    StreetConfig, TurnTreeConfig,
};
use gto_core::eval::parse_card;
use std::fmt::Write as _;
use std::time::Instant;

/// A common interface over the four production solver families measured by P0a.
pub enum CaseSolver {
    River(VectorRiverSolver),
    TurnRiver(TurnRiverSolver),
    Flop(Box<FlopSolver>),
    Blueprint(Box<BlueprintSolver>),
}

impl CaseSolver {
    pub fn run_chunk(&mut self, iterations: u32) {
        match self {
            CaseSolver::River(solver) => solver.run(iterations),
            CaseSolver::TurnRiver(solver) => solver.run(iterations),
            CaseSolver::Flop(solver) => solver.run(iterations),
            CaseSolver::Blueprint(solver) => solver.run(iterations),
        }
    }

    pub fn expl(&self) -> ExplReport {
        match self {
            CaseSolver::River(solver) => solver.exploitability_bb(),
            CaseSolver::TurnRiver(solver) => solver.exploitability_bb(),
            CaseSolver::Flop(solver) => solver.exploitability_bb(),
            CaseSolver::Blueprint(solver) => solver.exploitability_bb(),
        }
    }

    /// Bytes currently allocated for regret and average-strategy tables.
    pub fn table_bytes(&self) -> usize {
        match self {
            // VectorRiverSolver eagerly allocates two f64 tables for every
            // tree node. It does not expose table_bytes(), so reproduce that
            // exact allocation formula without expanding its public API.
            CaseSolver::River(solver) => {
                let one_table: usize = solver
                    .tree
                    .nodes
                    .iter()
                    .map(|node| {
                        node.children.len().max(1) * NUM_COMBOS * std::mem::size_of::<f64>()
                    })
                    .sum();
                2 * one_table
            }
            CaseSolver::TurnRiver(solver) => solver.table_bytes(),
            CaseSolver::Flop(solver) => solver.table_bytes(),
            CaseSolver::Blueprint(solver) => solver.table_bytes(),
        }
    }
}

/// A stable named benchmark fixture. The seed is ignored by deterministic
/// cases and recorded separately by the run harness.
pub struct BenchCase {
    pub name: &'static str,
    pub config: &'static str,
    pub build: fn(u64) -> CaseSolver,
}

fn card(value: &str) -> u8 {
    parse_card(value).expect("bench fixture contains a valid card")
}

const SRP_POT: i64 = 5 * BB;
const SRP_STACK: i64 = 97 * BB;
// 100bb stacks, open 2.5bb and 3bet to 9bb: 18bb pot, 89bb behind.
const THREE_BET_POT: i64 = 18 * BB;
const THREE_BET_STACK: i64 = 89 * BB;

const RIVER_CFG: &str =
    "board=2c7d9hJhKd pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp-river";
const TURN_ENUM_CFG: &str =
    "board=2c7d9hJh pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp mode=enumerate";
const TURN_SAMPLE_CFG: &str =
    "board=2c7d9hJh pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp mode=sample";
const FLOP_SRP_AHKD7S_K24_CFG: &str =
    "board=AhKd7s pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp mode=sample buckets_river=24 buckets_turn=16";
const FLOP_SRP_QSJH2C_K24_CFG: &str =
    "board=QsJh2c pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp mode=sample buckets_river=24 buckets_turn=16";
const FLOP_SRP_8D8H3S_K24_CFG: &str =
    "board=8d8h3s pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp mode=sample buckets_river=24 buckets_turn=16";
const FLOP_SRP_AHKD7S_K64_CFG: &str =
    "board=AhKd7s pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp mode=sample buckets_river=64 buckets_turn=16";
const FLOP_THREE_BET_CFG: &str =
    "board=AhKd7s pot=18bb stack=89bb ranges=uniform variant=cfr+ tree=3bet mode=sample buckets_river=24 buckets_turn=16";
const BLUEPRINT_SAMPLE_CFG: &str =
    "flops=AhKd7s,QsJh2c,8d8h3s weights=equal stack=100bb ranges=uniform variant=cfr+ mode=sample buckets_river=24 buckets_turn=16";
const BLUEPRINT_ENUM_CFG: &str =
    "flops=AhKd7s,QsJh2c,8d8h3s weights=equal stack=100bb ranges=uniform variant=cfr+ mode=enumerate buckets_river=24 buckets_turn=16";

fn abstraction_24_16() -> Abstraction {
    Abstraction {
        buckets_river: 24,
        buckets_turn: 16,
    }
}

fn river_case(_seed: u64) -> CaseSolver {
    let tree = build_river_tree(SRP_POT, SRP_STACK, &StreetConfig::srp_river());
    let board = [card("2c"), card("7d"), card("9h"), card("Jh"), card("Kd")];
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    CaseSolver::River(VectorRiverSolver::new(
        tree,
        board,
        ranges,
        CfrVariant::cfr_plus_default(),
    ))
}

fn turn_case(mode: ChanceMode) -> CaseSolver {
    let tree = build_turn_river_tree(SRP_POT, SRP_STACK, &TurnTreeConfig::srp());
    let board = [card("2c"), card("7d"), card("9h"), card("Jh")];
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    CaseSolver::TurnRiver(TurnRiverSolver::new(
        tree,
        board,
        ranges,
        CfrVariant::cfr_plus_default(),
        mode,
    ))
}

fn flop_case(
    board: [u8; 3],
    buckets_river: usize,
    pot: i64,
    stack: i64,
    config: FlopTreeConfig,
    seed: u64,
) -> CaseSolver {
    let tree = build_flop_tree(pot, stack, &config);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    CaseSolver::Flop(Box::new(FlopSolver::new_abstracted(
        tree,
        board,
        ranges,
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed },
        Abstraction {
            buckets_river,
            buckets_turn: 16,
        },
    )))
}

pub fn bp_flops() -> Vec<[u8; 3]> {
    vec![
        [card("Ah"), card("Kd"), card("7s")],
        [card("Qs"), card("Jh"), card("2c")],
        [card("8d"), card("8h"), card("3s")],
    ]
}

fn blueprint_case(sample: bool, seed: u64) -> CaseSolver {
    let tree = build_preflop_tree(100 * BB);
    let ranges = [uniform_excluding(&[]), uniform_excluding(&[])];
    let flops = bp_flops();
    let weights = vec![1.0; flops.len()];
    CaseSolver::Blueprint(Box::new(BlueprintSolver::new(
        tree,
        ranges,
        CfrVariant::cfr_plus_default(),
        flops,
        weights,
        abstraction_24_16(),
        sample,
        seed,
    )))
}

/// Reference cases used throughout the P0a audit. Names are an artifact
/// contract: reports and recovery directories key off them.
pub fn reference_cases() -> Vec<BenchCase> {
    vec![
        BenchCase {
            name: "river_srp100",
            config: RIVER_CFG,
            build: river_case,
        },
        BenchCase {
            name: "turn_srp100_enum",
            config: TURN_ENUM_CFG,
            build: |_| turn_case(ChanceMode::Enumerate),
        },
        BenchCase {
            name: "turn_srp100_sample",
            config: TURN_SAMPLE_CFG,
            build: |seed| turn_case(ChanceMode::Sample { seed }),
        },
        BenchCase {
            name: "flop_srp100_AhKd7s_k24",
            config: FLOP_SRP_AHKD7S_K24_CFG,
            build: |seed| {
                flop_case(
                    [card("Ah"), card("Kd"), card("7s")],
                    24,
                    SRP_POT,
                    SRP_STACK,
                    FlopTreeConfig::srp(),
                    seed,
                )
            },
        },
        BenchCase {
            name: "flop_srp100_QsJh2c_k24",
            config: FLOP_SRP_QSJH2C_K24_CFG,
            build: |seed| {
                flop_case(
                    [card("Qs"), card("Jh"), card("2c")],
                    24,
                    SRP_POT,
                    SRP_STACK,
                    FlopTreeConfig::srp(),
                    seed,
                )
            },
        },
        BenchCase {
            name: "flop_srp100_8d8h3s_k24",
            config: FLOP_SRP_8D8H3S_K24_CFG,
            build: |seed| {
                flop_case(
                    [card("8d"), card("8h"), card("3s")],
                    24,
                    SRP_POT,
                    SRP_STACK,
                    FlopTreeConfig::srp(),
                    seed,
                )
            },
        },
        BenchCase {
            name: "flop_srp100_AhKd7s_k64",
            config: FLOP_SRP_AHKD7S_K64_CFG,
            build: |seed| {
                flop_case(
                    [card("Ah"), card("Kd"), card("7s")],
                    64,
                    SRP_POT,
                    SRP_STACK,
                    FlopTreeConfig::srp(),
                    seed,
                )
            },
        },
        BenchCase {
            name: "flop_3bet100_AhKd7s_k24",
            config: FLOP_THREE_BET_CFG,
            build: |seed| {
                flop_case(
                    [card("Ah"), card("Kd"), card("7s")],
                    24,
                    THREE_BET_POT,
                    THREE_BET_STACK,
                    FlopTreeConfig::threebet(),
                    seed,
                )
            },
        },
        BenchCase {
            name: "bp3_sample",
            config: BLUEPRINT_SAMPLE_CFG,
            build: |seed| blueprint_case(true, seed),
        },
        BenchCase {
            name: "bp3_enum",
            config: BLUEPRINT_ENUM_CFG,
            build: |seed| blueprint_case(false, seed),
        },
    ]
}

#[derive(Debug, Clone, Copy)]
pub struct Checkpoint {
    pub iters: u32,
    /// Cumulative solve-only seconds at this checkpoint.
    pub solve_s: f64,
    /// Exact best-response evaluation time for this checkpoint.
    pub br_s: f64,
    pub expl: f64,
    pub br: [f64; 2],
}

#[derive(Debug, Clone, Copy)]
pub struct RunTiming {
    pub build_s: f64,
    pub solve_s: f64,
    pub checkpoint_br_s: f64,
    pub final_br_s: f64,
}

/// Ascending geometric cumulative iteration counts, deduplicated and ending
/// at `max_iters`. At most `points` values are returned.
pub fn geometric_schedule(max_iters: u32, points: usize) -> Vec<u32> {
    if max_iters == 0 || points == 0 {
        return Vec::new();
    }
    let mut schedule = Vec::with_capacity(points);
    let mut iterations = max_iters;
    for _ in 0..points {
        schedule.push(iterations);
        if iterations == 1 {
            break;
        }
        iterations = (iterations / 2).max(1);
    }
    schedule.dedup();
    schedule.reverse();
    schedule
}

/// Run to each cumulative checkpoint while keeping solve and exact-BR cost
/// separate. Construction time is owned by the caller, so `build_s` is zero.
pub fn run_with_checkpoints(
    solver: &mut CaseSolver,
    schedule: &[u32],
) -> (Vec<Checkpoint>, RunTiming) {
    assert!(
        schedule.windows(2).all(|window| window[0] < window[1]),
        "checkpoint schedule must be strictly ascending"
    );

    let mut checkpoints = Vec::with_capacity(schedule.len());
    let mut completed = 0u32;
    let mut solve_s = 0.0;
    let mut br_total_s = 0.0;
    for &target in schedule {
        assert!(target > 0, "checkpoint iterations must be positive");
        let solve_start = Instant::now();
        solver.run_chunk(target - completed);
        solve_s += solve_start.elapsed().as_secs_f64();
        completed = target;

        let br_start = Instant::now();
        let report = solver.expl();
        let br_s = br_start.elapsed().as_secs_f64();
        br_total_s += br_s;
        checkpoints.push(Checkpoint {
            iters: completed,
            solve_s,
            br_s,
            expl: report.exploitability,
            br: report.br_value,
        });
    }

    let final_br_s = checkpoints
        .last()
        .map(|checkpoint| checkpoint.br_s)
        .unwrap_or(0.0);
    (
        checkpoints,
        RunTiming {
            build_s: 0.0,
            solve_s,
            checkpoint_br_s: br_total_s - final_br_s,
            final_br_s,
        },
    )
}

/// Peak resident set (VmHWM) in MiB from `/proc/self/status` on Linux/WSL2.
pub fn peak_rss_mb() -> f64 {
    let status = std::fs::read_to_string("/proc/self/status").unwrap_or_default();
    status
        .lines()
        .find_map(|line| {
            line.strip_prefix("VmHWM:")?
                .split_whitespace()
                .next()?
                .parse::<f64>()
                .ok()
        })
        .unwrap_or(0.0)
        / 1024.0
}

/// Best-effort host identity for self-describing benchmark artifacts.
pub fn cpu_model() -> String {
    std::fs::read_to_string("/proc/cpuinfo")
        .unwrap_or_default()
        .lines()
        .find_map(|line| {
            let (key, value) = line.split_once(':')?;
            (key.trim() == "model name").then(|| value.trim().to_string())
        })
        .unwrap_or_default()
}

pub fn kernel_release() -> String {
    std::fs::read_to_string("/proc/sys/kernel/osrelease")
        .unwrap_or_default()
        .trim()
        .to_string()
}

/// Self-describing P0a run artifact. The schema intentionally stays
/// dependency-free so the solver harness adds no production crate.
pub struct RunRecord {
    pub schema_version: u32,
    pub case: String,
    pub config: String,
    pub label: String,
    pub git_commit: String,
    pub dirty: bool,
    pub seed: u64,
    pub iterations: u32,
    pub points: usize,
    pub threads: usize,
    pub build_profile: &'static str,
    pub cpu: String,
    pub kernel: String,
    pub cmdline: String,
    pub table_bytes: usize,
    pub peak_rss_mb: f64,
    pub resume_count: u32,
    pub timing: RunTiming,
    pub checkpoints: Vec<Checkpoint>,
}

fn escape_json(value: &str) -> String {
    let mut escaped = String::with_capacity(value.len());
    for character in value.chars() {
        match character {
            '"' => escaped.push_str("\\\""),
            '\\' => escaped.push_str("\\\\"),
            '\u{08}' => escaped.push_str("\\b"),
            '\u{0c}' => escaped.push_str("\\f"),
            '\n' => escaped.push_str("\\n"),
            '\r' => escaped.push_str("\\r"),
            '\t' => escaped.push_str("\\t"),
            control if control <= '\u{1f}' => {
                write!(escaped, "\\u{:04x}", control as u32).expect("write to String");
            }
            other => escaped.push(other),
        }
    }
    escaped
}

impl RunRecord {
    pub fn to_json(&self) -> String {
        let checkpoints: Vec<String> = self
            .checkpoints
            .iter()
            .map(|checkpoint| {
                format!(
                    "    {{\"iters\": {}, \"solve_s\": {:.3}, \"br_s\": {:.3}, \
                     \"expl\": {:.6}, \"br0\": {:.6}, \"br1\": {:.6}}}",
                    checkpoint.iters,
                    checkpoint.solve_s,
                    checkpoint.br_s,
                    checkpoint.expl,
                    checkpoint.br[0],
                    checkpoint.br[1]
                )
            })
            .collect();
        format!(
            concat!(
                "{{\n",
                "  \"schema_version\": {},\n",
                "  \"case\": \"{}\",\n  \"config\": \"{}\",\n  \"label\": \"{}\",\n",
                "  \"git_commit\": \"{}\",\n  \"dirty\": {},\n  \"seed\": {},\n",
                "  \"iterations\": {},\n  \"points\": {},\n  \"threads\": {},\n",
                "  \"build_profile\": \"{}\",\n  \"cpu\": \"{}\",\n  \"kernel\": \"{}\",\n",
                "  \"cmdline\": \"{}\",\n",
                "  \"table_bytes\": {},\n  \"peak_rss_mb\": {:.1},\n  \"resume_count\": {},\n",
                "  \"timing\": {{\"build_s\": {:.3}, \"solve_s\": {:.3}, ",
                "\"checkpoint_br_s\": {:.3}, \"final_br_s\": {:.3}}},\n",
                "  \"checkpoints\": [\n{}\n  ]\n}}\n",
            ),
            self.schema_version,
            escape_json(&self.case),
            escape_json(&self.config),
            escape_json(&self.label),
            escape_json(&self.git_commit),
            self.dirty,
            self.seed,
            self.iterations,
            self.points,
            self.threads,
            escape_json(self.build_profile),
            escape_json(&self.cpu),
            escape_json(&self.kernel),
            escape_json(&self.cmdline),
            self.table_bytes,
            self.peak_rss_mb,
            self.resume_count,
            self.timing.build_s,
            self.timing.solve_s,
            self.timing.checkpoint_br_s,
            self.timing.final_br_s,
            checkpoints.join(",\n")
        )
    }
}
