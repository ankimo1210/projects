//! P0a benchmark harness: stable reference cases for solver audit runs.
//!
//! Audit spec: `docs/superpowers/specs/2026-07-19-gtowizard-parity-ios-design.md`
//! §5.0. Long-run checkpointing and JSON records are added by later P0a tasks.

use crate::checkpoint::{CheckpointInfo, StableHasher};
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
use std::io;
use std::path::Path;
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

    pub fn checkpoint_supported(&self) -> bool {
        matches!(self, Self::Flop(_) | Self::Blueprint(_))
    }

    pub fn iteration(&self) -> Option<u32> {
        match self {
            Self::Flop(solver) => Some(solver.iteration()),
            Self::Blueprint(solver) => Some(solver.iteration()),
            Self::River(_) | Self::TurnRiver(_) => None,
        }
    }

    pub fn state_checksum(&self) -> Option<u64> {
        match self {
            Self::Flop(solver) => Some(solver.state_checksum()),
            Self::Blueprint(solver) => Some(solver.state_checksum()),
            Self::River(_) | Self::TurnRiver(_) => None,
        }
    }

    fn checkpoint_unsupported() -> io::Error {
        io::Error::new(
            io::ErrorKind::Unsupported,
            "durable checkpoints are supported only for flop and blueprint cases",
        )
    }

    pub fn save_checkpoint(
        &self,
        dir: &Path,
        build_id: &str,
        keep: usize,
        companion: Option<&[u8]>,
    ) -> io::Result<CheckpointInfo> {
        match self {
            Self::Flop(solver) => {
                solver.save_checkpoint_with_companion(dir, build_id, keep, companion)
            }
            Self::Blueprint(solver) => {
                solver.save_checkpoint_with_companion(dir, build_id, keep, companion)
            }
            Self::River(_) | Self::TurnRiver(_) => Err(Self::checkpoint_unsupported()),
        }
    }

    pub fn validate_checkpoint(&self, path: &Path, build_id: &str) -> io::Result<CheckpointInfo> {
        match self {
            Self::Flop(solver) => solver.validate_checkpoint(path, build_id),
            Self::Blueprint(solver) => solver.validate_checkpoint(path, build_id),
            Self::River(_) | Self::TurnRiver(_) => Err(Self::checkpoint_unsupported()),
        }
    }

    pub fn restore_checkpoint(
        &mut self,
        path: &Path,
        build_id: &str,
    ) -> io::Result<CheckpointInfo> {
        match self {
            Self::Flop(solver) => solver.restore_checkpoint(path, build_id),
            Self::Blueprint(solver) => solver.restore_checkpoint(path, build_id),
            Self::River(_) | Self::TurnRiver(_) => Err(Self::checkpoint_unsupported()),
        }
    }

    pub fn resume_latest(&mut self, dir: &Path, build_id: &str) -> io::Result<CheckpointInfo> {
        match self {
            Self::Flop(solver) => solver.resume_latest(dir, build_id),
            Self::Blueprint(solver) => solver.resume_latest(dir, build_id),
            Self::River(_) | Self::TurnRiver(_) => Err(Self::checkpoint_unsupported()),
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
    pub checkpoint_s: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct RunSegment {
    pub start_iters: u32,
    pub end_iters: u32,
    pub build_s: f64,
    pub solve_s: f64,
    pub br_s: f64,
    pub checkpoint_s: f64,
}

#[derive(Debug, Clone)]
pub struct BenchRunState {
    pub run_fingerprint: u64,
    pub iteration: u32,
    pub resume_count: u32,
    pub build_s: f64,
    pub solve_s: f64,
    pub br_s: f64,
    pub checkpoint_s: f64,
    pub checkpoints: Vec<Checkpoint>,
    pub segments: Vec<RunSegment>,
}

impl BenchRunState {
    pub fn new(run_fingerprint: u64, build_s: f64) -> Self {
        Self {
            run_fingerprint,
            iteration: 0,
            resume_count: 0,
            build_s,
            solve_s: 0.0,
            br_s: 0.0,
            checkpoint_s: 0.0,
            checkpoints: Vec::new(),
            segments: vec![RunSegment {
                start_iters: 0,
                end_iters: 0,
                build_s,
                solve_s: 0.0,
                br_s: 0.0,
                checkpoint_s: 0.0,
            }],
        }
    }

    pub fn begin_resume(&mut self, iteration: u32, build_s: f64) {
        self.iteration = iteration;
        self.resume_count += 1;
        self.build_s += build_s;
        self.segments.push(RunSegment {
            start_iters: iteration,
            end_iters: iteration,
            build_s,
            solve_s: 0.0,
            br_s: 0.0,
            checkpoint_s: 0.0,
        });
    }

    pub fn add_solve(&mut self, iteration: u32, seconds: f64) {
        self.iteration = iteration;
        self.solve_s += seconds;
        let segment = self.segments.last_mut().expect("run has a process segment");
        segment.end_iters = iteration;
        segment.solve_s += seconds;
    }

    pub fn add_checkpoint(&mut self, checkpoint: Checkpoint) {
        self.br_s += checkpoint.br_s;
        self.segments
            .last_mut()
            .expect("run has a process segment")
            .br_s += checkpoint.br_s;
        self.checkpoints.push(checkpoint);
    }

    pub fn add_checkpoint_io(&mut self, seconds: f64) {
        self.checkpoint_s += seconds;
        self.segments
            .last_mut()
            .expect("run has a process segment")
            .checkpoint_s += seconds;
    }

    pub fn timing(&self) -> RunTiming {
        let final_br_s = self
            .checkpoints
            .last()
            .filter(|checkpoint| checkpoint.iters == self.iteration)
            .map_or(0.0, |checkpoint| checkpoint.br_s);
        RunTiming {
            build_s: self.build_s,
            solve_s: self.solve_s,
            checkpoint_br_s: self.br_s - final_br_s,
            final_br_s,
            checkpoint_s: self.checkpoint_s,
        }
    }

    pub fn to_sidecar(&self, solver_state_checksum: u64) -> Vec<u8> {
        let mut bytes =
            Vec::with_capacity(80 + self.checkpoints.len() * 44 + self.segments.len() * 44);
        bytes.extend_from_slice(b"GTOBEN1\0");
        push_u32(&mut bytes, 1);
        push_u64(&mut bytes, self.run_fingerprint);
        push_u64(&mut bytes, solver_state_checksum);
        push_u32(&mut bytes, self.iteration);
        push_u32(&mut bytes, self.resume_count);
        for value in [self.build_s, self.solve_s, self.br_s, self.checkpoint_s] {
            push_f64(&mut bytes, value);
        }
        push_u32(&mut bytes, self.checkpoints.len() as u32);
        for checkpoint in &self.checkpoints {
            push_u32(&mut bytes, checkpoint.iters);
            for value in [
                checkpoint.solve_s,
                checkpoint.br_s,
                checkpoint.expl,
                checkpoint.br[0],
                checkpoint.br[1],
            ] {
                push_f64(&mut bytes, value);
            }
        }
        push_u32(&mut bytes, self.segments.len() as u32);
        for segment in &self.segments {
            push_u32(&mut bytes, segment.start_iters);
            push_u32(&mut bytes, segment.end_iters);
            for value in [
                segment.build_s,
                segment.solve_s,
                segment.br_s,
                segment.checkpoint_s,
            ] {
                push_f64(&mut bytes, value);
            }
        }
        let mut hasher = StableHasher::new(b"gto-hu/bench-sidecar/v1");
        hasher.update(&bytes);
        push_u64(&mut bytes, hasher.finish());
        bytes
    }

    pub fn from_sidecar(bytes: &[u8]) -> io::Result<(Self, u64)> {
        if bytes.len() < 8 {
            return Err(invalid_sidecar("bench sidecar is truncated"));
        }
        let (body, checksum_bytes) = bytes.split_at(bytes.len() - 8);
        let stored_checksum = u64::from_le_bytes(checksum_bytes.try_into().unwrap());
        let mut hasher = StableHasher::new(b"gto-hu/bench-sidecar/v1");
        hasher.update(body);
        if stored_checksum != hasher.finish() {
            return Err(invalid_sidecar("bench sidecar checksum mismatch"));
        }

        let mut reader = SidecarReader::new(body);
        if reader.read_exact(8)? != b"GTOBEN1\0" {
            return Err(invalid_sidecar("bench sidecar magic mismatch"));
        }
        let version = reader.read_u32()?;
        if version != 1 {
            return Err(invalid_sidecar(format!(
                "bench sidecar version mismatch: {version}"
            )));
        }
        let run_fingerprint = reader.read_u64()?;
        let solver_state_checksum = reader.read_u64()?;
        let iteration = reader.read_u32()?;
        let resume_count = reader.read_u32()?;
        let build_s = reader.read_f64()?;
        let solve_s = reader.read_f64()?;
        let br_s = reader.read_f64()?;
        let checkpoint_s = reader.read_f64()?;
        if [build_s, solve_s, br_s, checkpoint_s]
            .into_iter()
            .any(|value| value < 0.0)
        {
            return Err(invalid_sidecar("bench sidecar contains a negative timing"));
        }

        let checkpoint_count = reader.read_count(44, "checkpoints")?;
        let mut checkpoints = Vec::with_capacity(checkpoint_count);
        for _ in 0..checkpoint_count {
            checkpoints.push(Checkpoint {
                iters: reader.read_u32()?,
                solve_s: reader.read_f64()?,
                br_s: reader.read_f64()?,
                expl: reader.read_f64()?,
                br: [reader.read_f64()?, reader.read_f64()?],
            });
        }

        let segment_count = reader.read_count(40, "segments")?;
        let mut segments = Vec::with_capacity(segment_count);
        for _ in 0..segment_count {
            segments.push(RunSegment {
                start_iters: reader.read_u32()?,
                end_iters: reader.read_u32()?,
                build_s: reader.read_f64()?,
                solve_s: reader.read_f64()?,
                br_s: reader.read_f64()?,
                checkpoint_s: reader.read_f64()?,
            });
        }
        if !reader.is_empty() {
            return Err(invalid_sidecar("trailing bytes in bench sidecar"));
        }
        if checkpoints
            .windows(2)
            .any(|window| window[0].iters >= window[1].iters)
            || checkpoints
                .last()
                .is_some_and(|checkpoint| checkpoint.iters > iteration)
            || checkpoints.iter().any(|checkpoint| {
                checkpoint.solve_s < 0.0 || checkpoint.br_s < 0.0 || checkpoint.expl < 0.0
            })
        {
            return Err(invalid_sidecar(
                "invalid checkpoint ordering in bench sidecar",
            ));
        }
        if segments.is_empty() {
            return Err(invalid_sidecar("bench sidecar has no process segments"));
        }
        if segments.iter().any(|segment| {
            segment.start_iters > segment.end_iters
                || segment.end_iters > iteration
                || [
                    segment.build_s,
                    segment.solve_s,
                    segment.br_s,
                    segment.checkpoint_s,
                ]
                .into_iter()
                .any(|value| value < 0.0)
        }) {
            return Err(invalid_sidecar("invalid process segment in bench sidecar"));
        }

        Ok((
            Self {
                run_fingerprint,
                iteration,
                resume_count,
                build_s,
                solve_s,
                br_s,
                checkpoint_s,
                checkpoints,
                segments,
            },
            solver_state_checksum,
        ))
    }
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_u64(bytes: &mut Vec<u8>, value: u64) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_f64(bytes: &mut Vec<u8>, value: f64) {
    push_u64(bytes, value.to_bits());
}

fn invalid_sidecar(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}

struct SidecarReader<'a> {
    bytes: &'a [u8],
    offset: usize,
}

impl<'a> SidecarReader<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn read_exact(&mut self, len: usize) -> io::Result<&'a [u8]> {
        let end = self
            .offset
            .checked_add(len)
            .ok_or_else(|| invalid_sidecar("bench sidecar offset overflow"))?;
        let value = self
            .bytes
            .get(self.offset..end)
            .ok_or_else(|| invalid_sidecar("bench sidecar is truncated"))?;
        self.offset = end;
        Ok(value)
    }

    fn read_u32(&mut self) -> io::Result<u32> {
        Ok(u32::from_le_bytes(self.read_exact(4)?.try_into().unwrap()))
    }

    fn read_u64(&mut self) -> io::Result<u64> {
        Ok(u64::from_le_bytes(self.read_exact(8)?.try_into().unwrap()))
    }

    fn read_f64(&mut self) -> io::Result<f64> {
        let value = f64::from_bits(self.read_u64()?);
        if !value.is_finite() {
            return Err(invalid_sidecar("bench sidecar contains a non-finite value"));
        }
        Ok(value)
    }

    fn read_count(&mut self, item_bytes: usize, what: &str) -> io::Result<usize> {
        let count = self.read_u32()? as usize;
        if count > self.bytes.len().saturating_sub(self.offset) / item_bytes {
            return Err(invalid_sidecar(format!(
                "bench sidecar {what} count exceeds remaining bytes"
            )));
        }
        Ok(count)
    }

    fn is_empty(&self) -> bool {
        self.offset == self.bytes.len()
    }
}

pub fn bench_run_fingerprint(
    case: &str,
    config: &str,
    label: &str,
    seed: u64,
    iterations: u32,
    points: usize,
    threads: usize,
) -> u64 {
    let mut hasher = StableHasher::new(b"gto-hu/bench-run/v1");
    for value in [case, config, label] {
        hasher.write_u64(value.len() as u64);
        hasher.update(value.as_bytes());
    }
    hasher.write_u64(seed);
    hasher.write_u32(iterations);
    hasher.write_u64(points as u64);
    hasher.write_u64(threads as u64);
    hasher.finish()
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
            checkpoint_s: 0.0,
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
    pub state_checksum: Option<u64>,
    pub resume_count: u32,
    pub timing: RunTiming,
    pub checkpoints: Vec<Checkpoint>,
    pub segments: Vec<RunSegment>,
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
        let state_checksum = self
            .state_checksum
            .map_or_else(|| "null".to_string(), |value| format!("\"{value:016x}\""));
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
        let segments: Vec<String> = self
            .segments
            .iter()
            .map(|segment| {
                format!(
                    "    {{\"start_iters\": {}, \"end_iters\": {}, \"build_s\": {:.3}, \
                     \"solve_s\": {:.3}, \"br_s\": {:.3}, \"checkpoint_s\": {:.3}}}",
                    segment.start_iters,
                    segment.end_iters,
                    segment.build_s,
                    segment.solve_s,
                    segment.br_s,
                    segment.checkpoint_s
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
                "  \"table_bytes\": {},\n  \"peak_rss_mb\": {:.1},\n",
                "  \"state_checksum\": {},\n  \"resume_count\": {},\n",
                "  \"timing\": {{\"build_s\": {:.3}, \"solve_s\": {:.3}, ",
                "\"checkpoint_br_s\": {:.3}, \"final_br_s\": {:.3}, ",
                "\"checkpoint_s\": {:.3}}},\n",
                "  \"checkpoints\": [\n{}\n  ],\n",
                "  \"segments\": [\n{}\n  ]\n}}\n",
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
            state_checksum,
            self.resume_count,
            self.timing.build_s,
            self.timing.solve_s,
            self.timing.checkpoint_br_s,
            self.timing.final_br_s,
            self.timing.checkpoint_s,
            checkpoints.join(",\n"),
            segments.join(",\n")
        )
    }
}
