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
const FLOP_SRP_CFG: &str =
    "pot=5bb stack=97bb ranges=uniform variant=cfr+ tree=srp mode=sample buckets_turn=16";
const FLOP_THREE_BET_CFG: &str =
    "board=AhKd7s pot=18bb stack=89bb ranges=uniform variant=cfr+ tree=3bet mode=sample buckets_river=24 buckets_turn=16";
const BLUEPRINT_CFG: &str =
    "flops=AhKd7s,QsJh2c,8d8h3s weights=equal stack=100bb ranges=uniform variant=cfr+ buckets_river=24 buckets_turn=16";

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
            config: FLOP_SRP_CFG,
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
            config: FLOP_SRP_CFG,
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
            config: FLOP_SRP_CFG,
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
            config: FLOP_SRP_CFG,
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
            config: BLUEPRINT_CFG,
            build: |seed| blueprint_case(true, seed),
        },
        BenchCase {
            name: "bp3_enum",
            config: BLUEPRINT_CFG,
            build: |seed| blueprint_case(false, seed),
        },
    ]
}
