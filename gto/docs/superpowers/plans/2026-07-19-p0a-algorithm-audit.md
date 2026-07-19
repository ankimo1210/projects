# P0a — Algorithm Optimization Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the benchmark/profiling harness and run the measurements that
produce the G-A1..G-A3 go/no-go verdicts of spec
`docs/superpowers/specs/2026-07-19-gtowizard-parity-ios-design.md` §5.0,
ending in a written audit report.

**Architecture:** A `bench` module inside `gto-hu` wraps the four solver
types behind one interface, runs them in chunks with exploitability
checkpoints, and emits hand-rolled JSON. A new `solver-bench` CLI drives
named reference cases. A small Python package fits convergence slopes and
renders the audit tables. One solver change is included as a spike:
`ChanceMode::MultiSample` (k-sample turn deals) to measure the
variance/cost trade-off between the existing `Sample` and `Enumerate`
modes. Everything else is measurement, not optimization — optimizations are
P0b work, sized by this audit.

**Tech Stack:** Rust (gto-hu; rayon only — **no new crate dependencies**),
Python 3.12 (numpy; already a dep), pytest, hand-rolled JSON (house style,
no serde).

## Global Constraints

- **No new production dependencies** in Rust or Python without explicit
  user approval (workspace policy). JSON is hand-rolled like
  `src/bin/solve_blueprint.rs` does; CLI args are hand-parsed like existing
  bins; slope fitting uses numpy (already in `gto/pyproject.toml`).
- **Bit-identity discipline**: any change touching solver numerics must
  leave existing behavior bit-identical (house pattern:
  `crates/gto-hu/tests/test_perf_baseline.rs` checksum tests).
  `MultiSample { samples: 1 }` must be bit-identical to `Sample`.
- **Determinism**: fixed seeds everywhere; two runs of the same case must
  produce identical expl sequences (SplitMix64 stream is part of the test
  contract).
- Rust commands run from `/home/kazumasa/projects/gto`; Python/pytest run
  from `/home/kazumasa/projects` (repo root) with `uv run --no-sync`
  (a bare `uv sync` deletes the maturin-built `gto_py`/`gto_cuda` — never
  run it).
- Benchmark runs use `--release`. Tests use the default profile.
- Long solver runs: run solo (no concurrent heavy jobs — WP2's first run
  OOM'd under concurrent load), monitor by PID, SIGSTOP/SIGCONT allowed.
- Spec gate values (verbatim): G-A1 median per-flop solve to its expl gate
  **≤ 12 min**; G-A2 fitted blueprint slope exponent **≤ −0.85** (baseline
  −0.51); G-A3 M=25 blueprint **≤ 48 GB** with f32 + board bucketing.
- Commit messages follow house style (`feat(gto-hu): …`, `bench(gto): …`,
  `docs(gto): …`) and end with the Claude trailer used on this branch.

**Branch:** work on `claude/gto-p0a-audit` cut from `claude/gto-ios-v1-spec`
(create in Task 1 Step 1). Audit artifacts (JSON baselines, report) are
committed to the repo under `gto/docs/reviews/2026-07-19-p0a-audit/`.

---

### Task 1: Bench case fixtures — one wrapper over the four solvers

**Files:**
- Create: `gto/crates/gto-hu/src/bench.rs`
- Modify: `gto/crates/gto-hu/src/lib.rs` (add `pub mod bench;`)
- Test: `gto/crates/gto-hu/tests/test_bench_cases.rs`

**Interfaces:**
- Consumes: `VectorRiverSolver`, `TurnRiverSolver`, `FlopSolver`,
  `BlueprintSolver`, `ChanceMode`, `Abstraction`, `CfrVariant`, tree
  builders, `uniform_excluding` (all existing, `gto_hu::solver` /
  `gto_hu::tree` / `gto_hu::ranges`).
- Produces (used by Tasks 2–3):
  - `pub enum CaseSolver { River(VectorRiverSolver), TurnRiver(TurnRiverSolver), Flop(Box<FlopSolver>), Blueprint(Box<BlueprintSolver>) }`
  - `impl CaseSolver { pub fn run_chunk(&mut self, n: u32); pub fn expl(&self) -> ExplReport; pub fn table_bytes(&self) -> usize }`
  - `pub struct BenchCase { pub name: &'static str, pub build: fn() -> CaseSolver }`
  - `pub fn reference_cases() -> Vec<BenchCase>`

Reference set (uniform ranges — the audit measures solver speed, not
product content; uniform is reproducible and range-shape-independent):

| name | construction |
|---|---|
| `river_srp100` | `build_river_tree(5*BB, 97*BB, &StreetConfig::srp_river())`, board `2c 7d 9h Jh Kd` |
| `turn_srp100_enum` / `turn_srp100_sample` | `build_turn_river_tree(5*BB, 97*BB, &TurnTreeConfig::srp())`, board `2c 7d 9h Jh`, `Enumerate` / `Sample{seed:42}` |
| `flop_srp100_<board>_k24` for boards `AhKd7s`, `QsJh2c`, `8d8h3s` | `build_flop_tree(5*BB, 97*BB, &FlopTreeConfig::srp())`, `Sample{seed:42}`, `Abstraction{buckets_river:24, buckets_turn:16}` |
| `flop_srp100_AhKd7s_k64` | same, `buckets_river:64` |
| `bp3_sample` / `bp3_enum` | `BlueprintSolver::new(build_preflop_tree(100*BB), uniform, cfr_plus_default, flops [AhKd7s,QsJh2c,8d8h3s], equal weights, Abstraction{24,16}, sample=true/false, seed 42)` — the WP2 configuration |

(If `TurnTreeConfig::srp()` does not exist, use the literal `TurnTreeConfig`
from `test_perf_baseline.rs::turn_cfg()` but with production street configs
`StreetConfig::srp_turn()` / `srp_river()`; check `tree/` for the actual
constructor names before writing.)

- [ ] **Step 1: Create the work branch**

```bash
cd /home/kazumasa/projects && git checkout claude/gto-ios-v1-spec && git checkout -b claude/gto-p0a-audit
```

- [ ] **Step 2: Write the failing test**

`gto/crates/gto-hu/tests/test_bench_cases.rs`:

```rust
//! P0a bench-case fixtures: every reference case constructs, runs, and
//! reports finite exploitability; construction is deterministic.

use gto_hu::bench::{reference_cases, CaseSolver};

#[test]
fn all_cases_construct_and_report_finite_expl() {
    for case in reference_cases() {
        // Blueprint/flop construction allocates GBs; keep this test to
        // the cheap cases and just require the builders exist for all.
        if case.name.starts_with("river") || case.name.starts_with("turn") {
            let mut s = (case.build)();
            s.run_chunk(2);
            let e = s.expl();
            assert!(e.exploitability.is_finite(), "{}", case.name);
            assert!(s.table_bytes() > 0, "{}", case.name);
        }
    }
}

#[test]
fn case_names_are_unique_and_stable() {
    let names: Vec<&str> = reference_cases().iter().map(|c| c.name).collect();
    let mut dedup = names.clone();
    dedup.sort();
    dedup.dedup();
    assert_eq!(names.len(), dedup.len(), "duplicate case names");
    for expected in ["river_srp100", "turn_srp100_enum", "turn_srp100_sample",
                     "flop_srp100_AhKd7s_k24", "flop_srp100_QsJh2c_k24",
                     "flop_srp100_8d8h3s_k24", "flop_srp100_AhKd7s_k64",
                     "bp3_sample", "bp3_enum"] {
        assert!(names.contains(&expected), "missing case {expected}");
    }
}

#[test]
fn river_case_is_deterministic() {
    let case = reference_cases().into_iter().find(|c| c.name == "river_srp100").unwrap();
    let run = |mut s: CaseSolver| { s.run_chunk(5); s.expl().exploitability.to_bits() };
    assert_eq!(run((case.build)()), run((case.build)()));
}
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /home/kazumasa/projects/gto && cargo test -p gto-hu --test test_bench_cases 2>&1 | tail -5
```
Expected: FAIL — `could not find `bench` in `gto_hu``.

- [ ] **Step 4: Implement `bench.rs` fixtures**

`gto/crates/gto-hu/src/bench.rs` (add `pub mod bench;` to `lib.rs`):

```rust
//! P0a benchmark harness: reference cases, checkpointed runs, JSON output.
//! Audit spec: docs/superpowers/specs/2026-07-19-gtowizard-parity-ios-design.md §5.0.

use crate::game::BB;
use crate::ranges::uniform_excluding;
use crate::solver::{
    Abstraction, BlueprintSolver, CfrVariant, ChanceMode, ExplReport, FlopSolver,
    TurnRiverSolver, VectorRiverSolver,
};
use crate::tree::{
    build_flop_tree, build_preflop_tree, build_river_tree, build_turn_river_tree,
    FlopTreeConfig, StreetConfig, TurnTreeConfig,
};
use gto_core::eval::parse_card;

pub enum CaseSolver {
    River(VectorRiverSolver),
    TurnRiver(TurnRiverSolver),
    Flop(Box<FlopSolver>),
    Blueprint(Box<BlueprintSolver>),
}

impl CaseSolver {
    pub fn run_chunk(&mut self, n: u32) {
        match self {
            CaseSolver::River(s) => s.run(n),
            CaseSolver::TurnRiver(s) => s.run(n),
            CaseSolver::Flop(s) => s.run(n),
            CaseSolver::Blueprint(s) => s.run(n),
        }
    }
    pub fn expl(&self) -> ExplReport {
        match self {
            CaseSolver::River(s) => s.exploitability_bb(),
            CaseSolver::TurnRiver(s) => s.exploitability_bb(),
            CaseSolver::Flop(s) => s.exploitability_bb(),
            CaseSolver::Blueprint(s) => s.exploitability_bb(),
        }
    }
    pub fn table_bytes(&self) -> usize {
        match self {
            CaseSolver::River(s) => s.table_bytes(),
            CaseSolver::TurnRiver(s) => s.table_bytes(),
            CaseSolver::Flop(s) => s.table_bytes(),
            CaseSolver::Blueprint(s) => s.table_bytes(),
        }
    }
}

pub struct BenchCase {
    pub name: &'static str,
    pub build: fn() -> CaseSolver,
}

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

const SRP_POT: u32 = 5 * BB;
const SRP_STACK: u32 = 97 * BB;
const SEED: u64 = 42;

fn abs24() -> Abstraction {
    Abstraction { buckets_river: 24, buckets_turn: 16 }
}

fn river_case() -> CaseSolver {
    let tree = build_river_tree(SRP_POT, SRP_STACK, &StreetConfig::srp_river());
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    CaseSolver::River(VectorRiverSolver::new(tree, board, ranges, CfrVariant::cfr_plus_default()))
}

fn turn_case(mode: ChanceMode) -> CaseSolver {
    let tree = build_turn_river_tree(SRP_POT, SRP_STACK, &TurnTreeConfig::srp());
    let board = [c("2c"), c("7d"), c("9h"), c("Jh")];
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    CaseSolver::TurnRiver(TurnRiverSolver::new(
        tree, board, ranges, CfrVariant::cfr_plus_default(), mode,
    ))
}

fn flop_case(board: [u8; 3], buckets_river: usize) -> CaseSolver {
    let tree = build_flop_tree(SRP_POT, SRP_STACK, &FlopTreeConfig::srp());
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    CaseSolver::Flop(Box::new(FlopSolver::new_abstracted(
        tree,
        board,
        ranges,
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed: SEED },
        Abstraction { buckets_river, buckets_turn: 16 },
    )))
}

pub fn bp_flops() -> Vec<[u8; 3]> {
    vec![
        [c("Ah"), c("Kd"), c("7s")],
        [c("Qs"), c("Jh"), c("2c")],
        [c("8d"), c("8h"), c("3s")],
    ]
}

fn blueprint_case(sample: bool) -> CaseSolver {
    let tree = build_preflop_tree(100 * BB);
    let ranges = [uniform_excluding(&[]), uniform_excluding(&[])];
    let flops = bp_flops();
    let weights = vec![1.0; flops.len()];
    CaseSolver::Blueprint(Box::new(BlueprintSolver::new(
        tree, ranges, CfrVariant::cfr_plus_default(), flops, weights, abs24(), sample, SEED,
    )))
}

pub fn reference_cases() -> Vec<BenchCase> {
    vec![
        BenchCase { name: "river_srp100", build: river_case_thunk },
        BenchCase { name: "turn_srp100_enum", build: || turn_case(ChanceMode::Enumerate) },
        BenchCase { name: "turn_srp100_sample", build: || turn_case(ChanceMode::Sample { seed: SEED }) },
        BenchCase { name: "flop_srp100_AhKd7s_k24", build: || flop_case([c2("Ah"), c2("Kd"), c2("7s")], 24) },
        BenchCase { name: "flop_srp100_QsJh2c_k24", build: || flop_case([c2("Qs"), c2("Jh"), c2("2c")], 24) },
        BenchCase { name: "flop_srp100_8d8h3s_k24", build: || flop_case([c2("8d"), c2("8h"), c2("3s")], 24) },
        BenchCase { name: "flop_srp100_AhKd7s_k64", build: || flop_case([c2("Ah"), c2("Kd"), c2("7s")], 64) },
        BenchCase { name: "bp3_sample", build: || blueprint_case(true) },
        BenchCase { name: "bp3_enum", build: || blueprint_case(false) },
    ]
}

fn river_case_thunk() -> CaseSolver { river_case() }
fn c2(s: &str) -> u8 { c(s) }
```

Adaptation notes for the implementer (verify against the actual code, do
not guess): `BB` may be `u32` or `f64` — match the tree-builder signatures
(`test_perf_baseline.rs` uses `20 * BB` with `build_river_tree`);
`uniform_excluding(&[])` for the preflop range — check how
`solve_blueprint.rs` builds its ranges and copy that; `TurnTreeConfig::srp()`
— if absent, use the production config the turn CLI uses
(`src/bin/solve_turn_river.rs`). Closures as `fn` pointers work only if
non-capturing — all builders above are non-capturing.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/kazumasa/projects/gto && cargo test -p gto-hu --test test_bench_cases 2>&1 | tail -5
```
Expected: `3 passed`.

- [ ] **Step 6: Run the full gto-hu suite (no regressions)**

```bash
cargo test -p gto-hu 2>&1 | tail -3
```
Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add crates/gto-hu/src/bench.rs crates/gto-hu/src/lib.rs crates/gto-hu/tests/test_bench_cases.rs
git commit -m "feat(gto-hu): P0a bench reference cases behind one CaseSolver wrapper"
```

---

### Task 2: Checkpointed runner, RSS, JSON output

**Files:**
- Modify: `gto/crates/gto-hu/src/bench.rs`
- Test: `gto/crates/gto-hu/tests/test_bench_run.rs`

**Interfaces:**
- Consumes: `CaseSolver` (Task 1).
- Produces (used by Task 3 CLI and Task 4 Python reader):
  - `pub struct Checkpoint { pub iters: u32, pub elapsed_s: f64, pub expl: f64, pub br: [f64; 2] }`
  - `pub fn geometric_schedule(max_iters: u32, points: usize) -> Vec<u32>` — ascending cumulative iteration counts, last == max_iters
  - `pub fn run_with_checkpoints(s: &mut CaseSolver, schedule: &[u32]) -> Vec<Checkpoint>` — `elapsed_s` counts **solve time only** (exploitability evaluation excluded)
  - `pub fn peak_rss_mb() -> f64`
  - `pub struct RunRecord { pub case: String, pub label: String, pub threads: usize, pub table_bytes: usize, pub peak_rss_mb: f64, pub checkpoints: Vec<Checkpoint> }`
  - `impl RunRecord { pub fn to_json(&self) -> String }` — keys exactly: `case`, `label`, `threads`, `table_bytes`, `peak_rss_mb`, `checkpoints` (array of objects with keys `iters`, `elapsed_s`, `expl`, `br0`, `br1`)

- [ ] **Step 1: Write the failing tests**

`gto/crates/gto-hu/tests/test_bench_run.rs`:

```rust
use gto_hu::bench::{
    geometric_schedule, peak_rss_mb, reference_cases, run_with_checkpoints, RunRecord,
};

#[test]
fn schedule_is_ascending_dedup_and_ends_at_max() {
    let s = geometric_schedule(2000, 8);
    assert_eq!(*s.last().unwrap(), 2000);
    assert!(s.windows(2).all(|w| w[0] < w[1]), "{s:?}");
    assert!(s.len() <= 8);
    assert_eq!(geometric_schedule(4, 8), vec![1, 2, 4]);
}

#[test]
fn river_checkpoints_are_deterministic_and_monotone_in_iters() {
    let case = reference_cases().into_iter().find(|c| c.name == "river_srp100").unwrap();
    let sched = geometric_schedule(40, 4);
    let mut a = (case.build)();
    let mut b = (case.build)();
    let ca = run_with_checkpoints(&mut a, &sched);
    let cb = run_with_checkpoints(&mut b, &sched);
    assert_eq!(ca.len(), sched.len());
    for (x, y) in ca.iter().zip(&cb) {
        assert_eq!(x.iters, y.iters);
        assert_eq!(x.expl.to_bits(), y.expl.to_bits(), "nondeterministic expl");
        assert!(x.elapsed_s >= 0.0);
    }
    assert!(ca.last().unwrap().expl < ca.first().unwrap().expl, "no convergence");
}

#[test]
fn json_has_expected_keys() {
    let rec = RunRecord {
        case: "x".into(), label: "l".into(), threads: 4,
        table_bytes: 123, peak_rss_mb: 1.5,
        checkpoints: vec![gto_hu::bench::Checkpoint { iters: 1, elapsed_s: 0.5, expl: 2.0, br: [1.0, 1.0] }],
    };
    let j = rec.to_json();
    for key in ["\"case\"", "\"label\"", "\"threads\"", "\"table_bytes\"",
                "\"peak_rss_mb\"", "\"checkpoints\"", "\"iters\"",
                "\"elapsed_s\"", "\"expl\"", "\"br0\"", "\"br1\""] {
        assert!(j.contains(key), "missing {key} in {j}");
    }
    assert!(peak_rss_mb() > 0.0);
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cargo test -p gto-hu --test test_bench_run 2>&1 | tail -5
```
Expected: FAIL — unresolved imports.

- [ ] **Step 3: Implement in `bench.rs`**

Append to `gto/crates/gto-hu/src/bench.rs`:

```rust
use std::time::Instant;

pub struct Checkpoint {
    pub iters: u32,
    pub elapsed_s: f64,
    pub expl: f64,
    pub br: [f64; 2],
}

/// Ascending cumulative iteration counts: max, max/2, max/4, … (deduped,
/// ≥ 1), reversed. Geometric so log-log slope fits get evenly spaced points.
pub fn geometric_schedule(max_iters: u32, points: usize) -> Vec<u32> {
    let mut v = Vec::with_capacity(points);
    let mut x = max_iters.max(1);
    for _ in 0..points {
        v.push(x);
        if x == 1 { break; }
        x = (x / 2).max(1);
    }
    v.dedup();
    v.reverse();
    v
}

/// Run to each cumulative checkpoint; `elapsed_s` accumulates SOLVE time
/// only — the exact best-response evaluation at each checkpoint is
/// excluded so timing reflects generation cost, not measurement cost.
pub fn run_with_checkpoints(s: &mut CaseSolver, schedule: &[u32]) -> Vec<Checkpoint> {
    let mut out = Vec::with_capacity(schedule.len());
    let mut done = 0u32;
    let mut solve_s = 0.0f64;
    for &target in schedule {
        let chunk = target - done;
        let t = Instant::now();
        s.run_chunk(chunk);
        solve_s += t.elapsed().as_secs_f64();
        done = target;
        let e = s.expl();
        out.push(Checkpoint {
            iters: done,
            elapsed_s: solve_s,
            expl: e.exploitability,
            br: e.br_value,
        });
    }
    out
}

/// Peak resident set (VmHWM) in MB from /proc/self/status (Linux/WSL2).
pub fn peak_rss_mb() -> f64 {
    let status = std::fs::read_to_string("/proc/self/status").unwrap_or_default();
    for line in status.lines() {
        if let Some(rest) = line.strip_prefix("VmHWM:") {
            let kb: f64 = rest.trim().trim_end_matches(" kB").trim().parse().unwrap_or(0.0);
            return kb / 1024.0;
        }
    }
    0.0
}

pub struct RunRecord {
    pub case: String,
    pub label: String,
    pub threads: usize,
    pub table_bytes: usize,
    pub peak_rss_mb: f64,
    pub checkpoints: Vec<Checkpoint>,
}

impl RunRecord {
    pub fn to_json(&self) -> String {
        let cps: Vec<String> = self.checkpoints.iter().map(|c| format!(
            "    {{\"iters\": {}, \"elapsed_s\": {:.3}, \"expl\": {:.6}, \"br0\": {:.6}, \"br1\": {:.6}}}",
            c.iters, c.elapsed_s, c.expl, c.br[0], c.br[1]
        )).collect();
        format!(
            "{{\n  \"case\": \"{}\",\n  \"label\": \"{}\",\n  \"threads\": {},\n  \"table_bytes\": {},\n  \"peak_rss_mb\": {:.1},\n  \"checkpoints\": [\n{}\n  ]\n}}\n",
            self.case, self.label, self.threads, self.table_bytes,
            self.peak_rss_mb, cps.join(",\n")
        )
    }
}
```

- [ ] **Step 4: Run tests**

```bash
cargo test -p gto-hu --test test_bench_run 2>&1 | tail -5
```
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/bench.rs crates/gto-hu/tests/test_bench_run.rs
git commit -m "feat(gto-hu): checkpointed bench runner with solve-only timing and JSON output"
```

---

### Task 3: `solver-bench` CLI

**Files:**
- Create: `gto/crates/gto-hu/src/bin/solver_bench.rs`
- Modify: `gto/crates/gto-hu/Cargo.toml` (append `[[bin]] name = "solver-bench", path = "src/bin/solver_bench.rs"`)

**Interfaces:**
- Consumes: `reference_cases`, `geometric_schedule`, `run_with_checkpoints`,
  `peak_rss_mb`, `RunRecord` (Tasks 1–2).
- Produces: CLI `solver-bench --case NAME --iterations N [--points K=10] [--threads T=0] [--label S=""] [--out FILE]`; `--list` prints case names. `--threads 0` = rayon default. Exit 2 on bad args (house style `usage()`).

- [ ] **Step 1: Write the bin**

`gto/crates/gto-hu/src/bin/solver_bench.rs`:

```rust
//! solver-bench — P0a audit driver: run a named reference case with
//! exploitability checkpoints; write a RunRecord JSON.
//!
//! Example:
//!   solver-bench --case river_srp100 --iterations 2000 --points 10 \
//!     --label "$(git rev-parse --short HEAD)" --out baselines/river.json

use std::process::exit;

use gto_hu::bench::{
    geometric_schedule, peak_rss_mb, reference_cases, run_with_checkpoints, RunRecord,
};

fn usage() -> ! {
    eprintln!(
        "usage: solver-bench --case NAME --iterations N [--points K=10] \
         [--threads T=0] [--label S] [--out FILE] | --list"
    );
    exit(2);
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut case_name = String::new();
    let mut iterations: u32 = 0;
    let mut points: usize = 10;
    let mut threads: usize = 0;
    let mut label = String::new();
    let mut out: Option<String> = None;

    let mut i = 0;
    while i < args.len() {
        let need = |i: usize| args.get(i + 1).cloned().unwrap_or_else(|| usage());
        match args[i].as_str() {
            "--list" => {
                for c in reference_cases() { println!("{}", c.name); }
                return;
            }
            "--case" => { case_name = need(i); i += 2; }
            "--iterations" => { iterations = need(i).parse().unwrap_or_else(|_| usage()); i += 2; }
            "--points" => { points = need(i).parse().unwrap_or_else(|_| usage()); i += 2; }
            "--threads" => { threads = need(i).parse().unwrap_or_else(|_| usage()); i += 2; }
            "--label" => { label = need(i); i += 2; }
            "--out" => { out = Some(need(i)); i += 2; }
            _ => usage(),
        }
    }
    if case_name.is_empty() || iterations == 0 { usage(); }
    if threads > 0 {
        rayon::ThreadPoolBuilder::new().num_threads(threads).build_global()
            .expect("rayon pool already initialized");
    }
    let case = reference_cases().into_iter().find(|c| c.name == case_name)
        .unwrap_or_else(|| { eprintln!("unknown case '{case_name}' (use --list)"); exit(2) });

    eprintln!("building {case_name} …");
    let mut solver = (case.build)();
    eprintln!("table_bytes = {}", solver.table_bytes());
    let sched = geometric_schedule(iterations, points);
    let cps = run_with_checkpoints(&mut solver, &sched);
    for c in &cps {
        eprintln!("iters {:>7}  solve {:>9.1}s  expl {:.4} bb  (br0 {:.4} / br1 {:.4})",
                  c.iters, c.elapsed_s, c.expl, c.br[0], c.br[1]);
    }
    let rec = RunRecord {
        case: case_name,
        label,
        threads: if threads == 0 { rayon::current_num_threads() } else { threads },
        table_bytes: solver.table_bytes(),
        peak_rss_mb: peak_rss_mb(),
        checkpoints: cps,
    };
    match out {
        Some(path) => {
            if let Some(dir) = std::path::Path::new(&path).parent() {
                std::fs::create_dir_all(dir).expect("mkdir out dir");
            }
            std::fs::write(&path, rec.to_json()).expect("write json");
            eprintln!("wrote {path}");
        }
        None => println!("{}", rec.to_json()),
    }
}
```

Note: `rayon` must be a direct dependency of `gto-hu` (it is — see
`Cargo.toml`).

- [ ] **Step 2: Register the bin and build**

Append to `gto/crates/gto-hu/Cargo.toml`:

```toml
[[bin]]
name = "solver-bench"
path = "src/bin/solver_bench.rs"
```

```bash
cargo build --release -p gto-hu --bin solver-bench 2>&1 | tail -3
```
Expected: compiles clean.

- [ ] **Step 3: Smoke run (river, ~seconds)**

```bash
cargo run --release -p gto-hu --bin solver-bench -- --list
cargo run --release -p gto-hu --bin solver-bench -- --case river_srp100 --iterations 200 --points 5
```
Expected: case list; then 5 checkpoint lines with decreasing expl and a JSON
document on stdout.

- [ ] **Step 4: Commit**

```bash
git add crates/gto-hu/src/bin/solver_bench.rs crates/gto-hu/Cargo.toml
git commit -m "feat(gto-hu): solver-bench CLI for P0a audit runs"
```

---

### Task 4: Python slope-fit and report tool

**Files:**
- Create: `gto/src/gto/bench/__init__.py`
- Create: `gto/src/gto/bench/report.py`
- Create: `gto/src/gto/bench/__main__.py`
- Test: `gto/tests/test_bench_report.py`

**Interfaces:**
- Consumes: RunRecord JSON files (Task 2 schema).
- Produces:
  - `fit_slope(iters: Sequence[float], expl: Sequence[float]) -> float` — least-squares slope of log(expl) vs log(iters)
  - `time_to(target_expl: float, checkpoints: list[dict]) -> float | None` — first crossing, log-linear interpolation on (elapsed_s, expl); None if never reached
  - `load_dir(path: Path) -> list[dict]` — parsed `*.json`, sorted by case
  - `render_markdown(runs: list[dict], targets: tuple[float, ...] = (0.5, 0.3, 0.15)) -> str` — one table row per run: case, label, threads, final iters/expl, slope, time-to each target (`—` if unreached), peak RSS
  - CLI: `uv run --no-sync python -m gto.bench <dir> [-o report.md]`

- [ ] **Step 1: Write the failing tests**

`gto/tests/test_bench_report.py`:

```python
import json
import math

from gto.bench import fit_slope, load_dir, render_markdown, time_to


def _synthetic_run(case="synth", c=100.0, slope=-1.0, secs_per_iter=0.01):
    iters = [10, 20, 40, 80, 160, 320]
    return {
        "case": case, "label": "t", "threads": 1, "table_bytes": 1,
        "peak_rss_mb": 10.0,
        "checkpoints": [
            {"iters": t, "elapsed_s": t * secs_per_iter,
             "expl": c * t ** slope, "br0": 0.0, "br1": 0.0}
            for t in iters
        ],
    }


def test_fit_slope_recovers_exponent():
    run = _synthetic_run(slope=-1.0)
    cps = run["checkpoints"]
    s = fit_slope([c["iters"] for c in cps], [c["expl"] for c in cps])
    assert math.isclose(s, -1.0, abs_tol=1e-9)


def test_time_to_interpolates_and_handles_unreached():
    cps = _synthetic_run(c=100.0, slope=-1.0)["checkpoints"]
    # expl == 1.0 at iters=100 -> elapsed 1.0s (log-linear interpolation)
    assert math.isclose(time_to(1.0, cps), 1.0, rel_tol=1e-6)
    assert time_to(1e-9, cps) is None


def test_load_dir_and_render(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(_synthetic_run("case_a")))
    (tmp_path / "b.json").write_text(json.dumps(_synthetic_run("case_b")))
    runs = load_dir(tmp_path)
    assert [r["case"] for r in runs] == ["case_a", "case_b"]
    md = render_markdown(runs)
    assert "case_a" in md and "case_b" in md and "slope" in md
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /home/kazumasa/projects && uv run --no-sync pytest gto/tests/test_bench_report.py -q 2>&1 | tail -3
```
Expected: FAIL — `ModuleNotFoundError: gto.bench`.

- [ ] **Step 3: Implement**

`gto/src/gto/bench/__init__.py`:

```python
"""P0a audit: convergence-slope fitting and report rendering.

Reads solver-bench RunRecord JSON (see crates/gto-hu/src/bench.rs).
"""

from gto.bench.report import fit_slope, load_dir, render_markdown, time_to

__all__ = ["fit_slope", "time_to", "load_dir", "render_markdown"]
```

`gto/src/gto/bench/report.py`:

```python
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np


def fit_slope(iters: Sequence[float], expl: Sequence[float]) -> float:
    """Least-squares slope of log(expl) vs log(iters). ~-0.5 = 1/sqrt(T),
    -1.0 = 1/T. Points with expl <= 0 are dropped (log-domain)."""
    pairs = [(t, e) for t, e in zip(iters, expl) if e > 0 and t > 0]
    if len(pairs) < 2:
        raise ValueError("need >= 2 positive checkpoints to fit a slope")
    x = np.log([p[0] for p in pairs])
    y = np.log([p[1] for p in pairs])
    return float(np.polyfit(x, y, 1)[0])


def time_to(target_expl: float, checkpoints: list[dict]) -> float | None:
    """Solve-seconds until expl first crosses target (log-linear
    interpolation between the bracketing checkpoints); None if unreached."""
    prev = None
    for cp in checkpoints:
        if cp["expl"] <= target_expl:
            if prev is None or prev["expl"] <= target_expl:
                return float(cp["elapsed_s"])
            # interpolate in (elapsed, log expl)
            f = (math.log(prev["expl"]) - math.log(target_expl)) / (
                math.log(prev["expl"]) - math.log(cp["expl"])
            )
            return float(prev["elapsed_s"] + f * (cp["elapsed_s"] - prev["elapsed_s"]))
        prev = cp
    return None


def load_dir(path: Path) -> list[dict]:
    runs = [json.loads(p.read_text()) for p in sorted(Path(path).glob("*.json"))]
    return sorted(runs, key=lambda r: (r["case"], r.get("label", "")))


def _fmt_t(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    return f"{seconds / 60:.1f}m" if seconds >= 60 else f"{seconds:.1f}s"


def render_markdown(runs: list[dict], targets: tuple[float, ...] = (0.5, 0.3, 0.15)) -> str:
    head = (
        "| case | label | threads | iters | expl (bb) | slope | "
        + " | ".join(f"t→{t}bb" for t in targets)
        + " | peak RSS |\n"
    )
    sep = "|" + "---|" * (7 + len(targets)) + "\n"
    rows = []
    for r in runs:
        cps = r["checkpoints"]
        slope = fit_slope([c["iters"] for c in cps], [c["expl"] for c in cps])
        last = cps[-1]
        cells = [
            r["case"], r.get("label", ""), str(r["threads"]),
            str(last["iters"]), f"{last['expl']:.4f}", f"{slope:.2f}",
            *[_fmt_t(time_to(t, cps)) for t in targets],
            f"{r['peak_rss_mb'] / 1024:.1f} GB",
        ]
        rows.append("| " + " | ".join(cells) + " |")
    return head + sep + "\n".join(rows) + "\n"
```

`gto/src/gto/bench/__main__.py`:

```python
import argparse
from pathlib import Path

from gto.bench import load_dir, render_markdown


def main() -> None:
    ap = argparse.ArgumentParser(prog="gto.bench", description="P0a audit report")
    ap.add_argument("dir", type=Path, help="directory of RunRecord *.json")
    ap.add_argument("-o", "--out", type=Path, default=None)
    args = ap.parse_args()
    md = render_markdown(load_dir(args.dir))
    if args.out:
        args.out.write_text(md)
        print(f"wrote {args.out}")
    else:
        print(md)


main()
```

- [ ] **Step 4: Run tests**

```bash
uv run --no-sync pytest gto/tests/test_bench_report.py -q 2>&1 | tail -3
```
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add gto/src/gto/bench gto/tests/test_bench_report.py
git commit -m "feat(gto): bench slope-fit and audit report renderer"
```

---

### Task 5: Baseline capture — fast set + blueprint sample/enumerate slopes (G-A2 evidence)

**Files:**
- Create: `gto/docs/reviews/2026-07-19-p0a-audit/baselines/*.json` (run artifacts)
- Create: `gto/docs/reviews/2026-07-19-p0a-audit/baseline-report.md` (rendered)

**Interfaces:**
- Consumes: `solver-bench` (Task 3), `gto.bench` (Task 4).
- Produces: committed baseline JSONs + rendered table; the `bp3_sample` vs
  `bp3_enum` slope comparison that decides G-A2's direction.

Runtime notes: river ≈ minutes; turn sample ≈ tens of minutes; `bp3_sample`
1500 iters ≈ 40 min (WP2 measured 1.54 s/iter); `bp3_enum` multiplies
per-iteration cost by roughly the number of legal turns (≈ 45×) — 100
iterations ≈ 2 h. Run sequentially, solo on the box. Blueprint checkpoints
each pay an exact best-response evaluation — keep `--points 8`.

- [ ] **Step 1: Fast set (river + turn, ~1 h total)**

```bash
cd /home/kazumasa/projects/gto
B=docs/reviews/2026-07-19-p0a-audit/baselines
L=$(git rev-parse --short HEAD)
cargo run --release -p gto-hu --bin solver-bench -- --case river_srp100      --iterations 2000  --points 10 --label "$L" --out $B/river_srp100.json
cargo run --release -p gto-hu --bin solver-bench -- --case turn_srp100_enum  --iterations 400   --points 8  --label "$L" --out $B/turn_srp100_enum.json
cargo run --release -p gto-hu --bin solver-bench -- --case turn_srp100_sample --iterations 4000 --points 10 --label "$L" --out $B/turn_srp100_sample.json
```
Expected: three JSON files; expl decreasing across checkpoints in each.

- [ ] **Step 2: Blueprint sample-mode slope (~40 min)**

```bash
cargo run --release -p gto-hu --bin solver-bench -- --case bp3_sample --iterations 1500 --points 8 --label "$L" --out $B/bp3_sample.json
```
Expected: final expl in the ~1.5 bb range (WP2: 1.506 bb at 1500 iters);
fitted slope near −0.5.

- [ ] **Step 3: Blueprint enumerate-mode slope (~2 h)**

```bash
cargo run --release -p gto-hu --bin solver-bench -- --case bp3_enum --iterations 100 --points 6 --label "$L" --out $B/bp3_enum.json
```
Expected: much higher per-iteration cost; slope fitted on 6 points. This is
the core G-A2 measurement: does enumerate reach a given expl in less
wall-clock than sample despite the per-iter cost?

- [ ] **Step 4: Render and commit**

```bash
cd /home/kazumasa/projects
uv run --no-sync python -m gto.bench gto/docs/reviews/2026-07-19-p0a-audit/baselines -o gto/docs/reviews/2026-07-19-p0a-audit/baseline-report.md
cd gto && git add docs/reviews/2026-07-19-p0a-audit && git commit -m "bench(gto): P0a baselines — river/turn fast set + bp3 sample vs enumerate slopes"
```

---

### Task 6: Flop time-to-expl matrix (G-A1 evidence)

**Files:**
- Create: `gto/docs/reviews/2026-07-19-p0a-audit/flops/*.json`
- Create: `gto/docs/reviews/2026-07-19-p0a-audit/flop-report.md`

**Interfaces:**
- Consumes: `solver-bench` flop cases (Task 1), `gto.bench` (Task 4).
- Produces: per-flop time-to-{0.5, 0.3, 0.15} bb table — the direct G-A1
  input (median across the three boards at each target).

Runtime: ~49 min per 3k-iteration flop run at K_r=128 historically; K_r=24
is faster per iteration. Four runs below ≈ 3–5 h total. Run sequentially.

- [ ] **Step 1: Run the matrix (3 boards × k24, plus AhKd7s × k64)**

```bash
cd /home/kazumasa/projects/gto
F=docs/reviews/2026-07-19-p0a-audit/flops
L=$(git rev-parse --short HEAD)
for case in flop_srp100_AhKd7s_k24 flop_srp100_QsJh2c_k24 flop_srp100_8d8h3s_k24 flop_srp100_AhKd7s_k64; do
  cargo run --release -p gto-hu --bin solver-bench -- --case $case --iterations 3000 --points 8 --label "$L" --out $F/$case.json
done
```
Expected: four JSONs. Sanity anchor: WP2-era full-SRP flop reached
expl ≈ 1.17 bb at 3k iterations (K_r=128) — K_r=24 values will differ but
should be same order of magnitude.

- [ ] **Step 2: Render, read the medians, commit**

```bash
cd /home/kazumasa/projects
uv run --no-sync python -m gto.bench gto/docs/reviews/2026-07-19-p0a-audit/flops -o gto/docs/reviews/2026-07-19-p0a-audit/flop-report.md
cd gto && git add docs/reviews/2026-07-19-p0a-audit/flops docs/reviews/2026-07-19-p0a-audit/flop-report.md
git commit -m "bench(gto): P0a flop time-to-expl matrix (G-A1 evidence)"
```

In the report, note explicitly: which expl target is *reachable* within the
G-A1 12-minute budget at these settings, and what per-file expl gate that
implies for spec §4.2 (the spec left the per-flop gate number to this
measurement).

---

### Task 7: `ChanceMode::MultiSample` spike (variance/cost mid-point)

**Files:**
- Modify: `gto/crates/gto-hu/src/solver/turn_river.rs` (ChanceMode enum + its sampling site)
- Modify: `gto/crates/gto-hu/src/solver/flop.rs` (seed extraction at `flop.rs:404`, mode match at `flop.rs:602`, `chance_sample`)
- Modify: `gto/crates/gto-hu/src/bench.rs` (add cases `bp3_ms4`, `bp3_ms16`, `flop_srp100_AhKd7s_k24_ms4`)
- Test: `gto/crates/gto-hu/tests/test_multisample.rs`

**Interfaces:**
- Consumes: existing `ChanceMode { Sample { seed }, Enumerate }`.
- Produces: `ChanceMode::MultiSample { seed: u64, samples: u8 }` — k
  i.i.d. turn samples (with replacement, same SplitMix64 stream), EV =
  mean of the k single-sample estimators. `MultiSample { seed, samples: 1 }`
  must be **bit-identical** to `Sample { seed }`.

- [ ] **Step 1: Write the failing bit-identity + determinism tests**

`gto/crates/gto-hu/tests/test_multisample.rs`:

```rust
//! MultiSample{k=1} must reproduce Sample bit-identically (same RNG
//! stream, same arithmetic); k>1 must be deterministic and converge.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{uniform_excluding, NUM_COMBOS};
use gto_hu::solver::{Abstraction, CfrVariant, ChanceMode, FlopSolver};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig};

fn c(s: &str) -> u8 { parse_card(s).unwrap() }

fn mix(acc: &mut u64, x: f64) {
    *acc = acc.rotate_left(7) ^ x.to_bits().wrapping_mul(0x9E37_79B9_7F4A_7C15);
}

fn tiny_flop(mode: ChanceMode) -> FlopSolver {
    // Small tree via reduced bucketing keeps this test in seconds.
    let tree = build_flop_tree(5 * BB, 20 * BB, &FlopTreeConfig::srp());
    let board = [c("Ah"), c("Kd"), c("7s")];
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    FlopSolver::new_abstracted(
        tree, board, ranges, CfrVariant::cfr_plus_default(), mode,
        Abstraction { buckets_river: 8, buckets_turn: 4 },
    )
}

fn checksum(s: &FlopSolver) -> u64 {
    let mut acc = 0u64;
    for node_id in s.action_node_ids() {
        for combo in 0..NUM_COMBOS {
            for p in s.average_strategy(node_id, combo) {
                mix(&mut acc, p);
            }
        }
    }
    acc
}

#[test]
fn multisample_k1_is_bit_identical_to_sample() {
    let mut a = tiny_flop(ChanceMode::Sample { seed: 42 });
    let mut b = tiny_flop(ChanceMode::MultiSample { seed: 42, samples: 1 });
    a.run(50);
    b.run(50);
    assert_eq!(
        a.exploitability_bb().exploitability.to_bits(),
        b.exploitability_bb().exploitability.to_bits(),
        "k=1 diverged from Sample"
    );
    assert_eq!(checksum(&a), checksum(&b));
}

#[test]
fn multisample_k4_is_deterministic_and_converges() {
    let run = |seed| {
        let mut s = tiny_flop(ChanceMode::MultiSample { seed, samples: 4 });
        s.run(50);
        (s.exploitability_bb().exploitability, checksum(&s))
    };
    let (e1, c1) = run(7);
    let (e2, c2) = run(7);
    assert_eq!(e1.to_bits(), e2.to_bits());
    assert_eq!(c1, c2);
    assert!(e1.is_finite() && e1 > 0.0);
}
```

Note: `average_strategy` on FlopSolver takes `(node_id, combo)` per
`flop.rs:903` — verify the exact signature (turn/river nodes may need a
ctx like the turn solver; if so, restrict the checksum to flop-street
action nodes, which is sufficient for the identity check).

- [ ] **Step 2: Run to verify failure**

```bash
cargo test -p gto-hu --test test_multisample 2>&1 | tail -5
```
Expected: FAIL — `MultiSample` is not a variant of `ChanceMode`.

- [ ] **Step 3: Implement `MultiSample`**

In `turn_river.rs`, extend the enum (keep `Copy`/`Clone` derives intact):

```rust
pub enum ChanceMode {
    Enumerate,
    Sample { seed: u64 },
    /// k i.i.d. public-card samples (with replacement) per chance visit;
    /// the EV estimate is the mean of the k single-sample estimators.
    /// `samples: 1` is bit-identical to `Sample`.
    MultiSample { seed: u64, samples: u8 },
}
```

In **flop.rs**: seed extraction (`flop.rs:404`) gains
`ChanceMode::MultiSample { seed, .. } => seed`; the traverse match
(`flop.rs:602`) treats `MultiSample { .. }` exactly like `Sample { .. }`
(turn deal sampled, river enumerated) but passes the sample count; and
`chance_sample` becomes a k-loop around its existing single-sample body:

```rust
fn chance_sample(
    &mut self,
    child: usize,
    deal_street: Street,
    traverser: u8,
    reach: &[f64; N],
    opp_reach: &[f64; N],
    ctx: Ctx,
    k: u8, // 1 for Sample; ChanceMode::MultiSample passes its `samples`
) -> Vec<f64> {
    let mut ev = vec![0.0; N];
    for _ in 0..k {
        // ---- existing single-sample body, verbatim, accumulating: ----
        // draw idx from self.rng exactly as today, deal the card,
        // recurse, and add `scale * v[c]` into ev[c] for unblocked combos
    }
    if k > 1 {
        let inv = 1.0 / k as f64;
        for v in ev.iter_mut() { *v *= inv; }
    }
    ev
}
```

The `k == 1` path must not multiply (no `* 1.0` reordering) so the Sample
stream and float ops stay bit-identical. Apply the same transformation to
the sampling site in `turn_river.rs` (its `Sample` samples the river deal;
same k-loop pattern, same k=1 discipline). Fix all `match` sites the
compiler flags — exhaustive matches on `ChanceMode` exist in both files
and in `src/bin/` CLIs; map `MultiSample` alongside `Sample` everywhere.

- [ ] **Step 4: Run the new tests and the full suite (bit-identity guard)**

```bash
cargo test -p gto-hu --test test_multisample 2>&1 | tail -4
cargo test -p gto-hu 2>&1 | tail -3
```
Expected: 2 passed; and **every** existing test still green — in
particular `test_perf_baseline` checksums, which prove `Sample` behavior
is untouched.

- [ ] **Step 5: Add bench cases and a blueprint plumb-through**

In `bench.rs`, add to `reference_cases()` (blueprint: `sample: bool` cannot
express MultiSample — check how `BlueprintSolver` builds its subgame
`ChanceMode` from `sample`/`seed` and add a mode-typed constructor variant
`new_with_mode(..., mode: ChanceMode)` that the existing `new` delegates
to; `solve_blueprint.rs` gains `--turn-samples N` mapping to
`MultiSample { seed, samples }`):

```rust
BenchCase { name: "flop_srp100_AhKd7s_k24_ms4",
            build: || flop_case_mode([c2("Ah"), c2("Kd"), c2("7s")], 24,
                    ChanceMode::MultiSample { seed: SEED, samples: 4 }) },
BenchCase { name: "bp3_ms4",  build: || blueprint_case_mode(ChanceMode::MultiSample { seed: SEED, samples: 4 }) },
BenchCase { name: "bp3_ms16", build: || blueprint_case_mode(ChanceMode::MultiSample { seed: SEED, samples: 16 }) },
```

(`flop_case_mode` / `blueprint_case_mode` are the Task-1 builders with the
mode parameter hoisted; refactor `flop_case`/`blueprint_case` to delegate.)

- [ ] **Step 6: Run bench-case tests, commit**

```bash
cargo test -p gto-hu --test test_bench_cases --test test_multisample 2>&1 | tail -4
git add crates/gto-hu/src/solver/turn_river.rs crates/gto-hu/src/solver/flop.rs \
        crates/gto-hu/src/solver/blueprint.rs crates/gto-hu/src/bin/solve_blueprint.rs \
        crates/gto-hu/src/bench.rs crates/gto-hu/tests/test_multisample.rs
git commit -m "feat(gto-hu): ChanceMode::MultiSample turn deals (k=1 bit-identical to Sample)"
```

- [ ] **Step 7: Measure MultiSample slopes (~2 h)**

```bash
cd /home/kazumasa/projects/gto
B=docs/reviews/2026-07-19-p0a-audit/baselines
L=$(git rev-parse --short HEAD)
cargo run --release -p gto-hu --bin solver-bench -- --case bp3_ms4  --iterations 400 --points 8 --label "$L" --out $B/bp3_ms4.json
cargo run --release -p gto-hu --bin solver-bench -- --case bp3_ms16 --iterations 100 --points 6 --label "$L" --out $B/bp3_ms16.json
cd /home/kazumasa/projects
uv run --no-sync python -m gto.bench gto/docs/reviews/2026-07-19-p0a-audit/baselines -o gto/docs/reviews/2026-07-19-p0a-audit/baseline-report.md
cd gto && git add docs/reviews/2026-07-19-p0a-audit && git commit -m "bench(gto): MultiSample k=4/16 blueprint slopes (G-A2 evidence)"
```

Expected: slope steepens monotonically from `bp3_sample` (−0.5) toward
`bp3_enum` as k grows; the report now contains the full
sample/ms4/ms16/enumerate trade-off curve.

---

### Task 8: Blueprint memory model (G-A3 evidence)

**Files:**
- Modify: `gto/crates/gto-hu/src/bench.rs`
- Test: `gto/crates/gto-hu/tests/test_bench_memory.rs`

**Interfaces:**
- Consumes: `dense_table_bytes_abstracted(tree, abs)` (`flop.rs:197`),
  `BlueprintSolver::table_bytes()` (`blueprint.rs:229`),
  `BlueprintSolver::betting_leaf_node_ids()`, tree builders.
- Produces:
  - `pub fn blueprint_bytes_model(m: usize, stack_bb: u32, abs: Abstraction) -> usize` — predicted total table bytes for an M-flop blueprint at the production configs (per preflop betting leaf: pot-type config → `dense_table_bytes_abstracted` × M, summed; plus the preflop layer, modeled the same way `BlueprintSolver` allocates it)
  - `pub fn f32_projection(bytes: usize) -> usize` — bytes × 1/2 for the f64 slabs (document which slabs halve: regret + strategy accumulators; index/bucket maps do not)

- [ ] **Step 1: Write the failing test**

`gto/crates/gto-hu/tests/test_bench_memory.rs`:

```rust
//! The memory model must reproduce the real allocator's accounting on a
//! configuration small enough to construct in a test.

use gto_hu::bench::{blueprint_bytes_model, f32_projection};
use gto_hu::solver::Abstraction;

#[test]
fn model_matches_actual_m3_tables_within_2pct() {
    let abs = Abstraction { buckets_river: 8, buckets_turn: 4 };
    // Construct the real thing at a small stack + tiny buckets so the
    // test allocates MBs, not GBs — same code path as production.
    let actual = {
        use gto_hu::bench::build_blueprint_for_test;
        let bp = build_blueprint_for_test(20, abs);
        bp.table_bytes()
    };
    let model = blueprint_bytes_model(3, 20, abs);
    let err = (model as f64 - actual as f64).abs() / actual as f64;
    assert!(err < 0.02, "model {model} vs actual {actual} (err {err:.3})");
}

#[test]
fn f32_projection_halves() {
    assert_eq!(f32_projection(1000), 500);
}
```

(`build_blueprint_for_test(stack_bb, abs)` is a small helper added to
`bench.rs` that builds the 3-flop blueprint at the given stack — reuse the
Task-1 `blueprint_case` internals with stack parameterized.)

- [ ] **Step 2: Run to verify failure; implement; re-run**

```bash
cargo test -p gto-hu --test test_bench_memory 2>&1 | tail -4
```

Implement `blueprint_bytes_model` by mirroring `BlueprintSolver::new`'s
allocation structure: build the preflop tree at `stack_bb`, take its
betting leaves, map each leaf's `PotType` through the same `config_for`
the solver uses (`src/bin/solve_blueprint.rs::config_for` — move/expose it
in `solver/blueprint.rs` as `pub fn config_for(pot_type) -> FlopTreeConfig`
so both share one source of truth), build each flop tree once, and sum
`dense_table_bytes_abstracted(&tree, abs) * m` plus the preflop layer's own
tables (read `BlueprintSolver::table_bytes` to see exactly which pieces it
counts, and count the same pieces). Then re-run: both tests pass.

- [ ] **Step 3: Print the G-A3 projection table**

Add a `--memory-model` flag to `solver-bench` that prints, for
stack 100 bb: M ∈ {3, 10, 25, 50} × f64/f32 (via `f32_projection`) ×
`Abstraction{24,16}`, in GB. Run it and paste the table into the audit
report (Task 9):

```bash
cargo run --release -p gto-hu --bin solver-bench -- --memory-model
```
Expected: M=3/f64 within ~2% of WP2's measured 23.95 GB dense table
(external validation of the model against a real historical run); the
M=25/f32 row is the G-A3 number.

- [ ] **Step 4: Commit**

```bash
git add crates/gto-hu/src/bench.rs crates/gto-hu/src/bin/solver_bench.rs \
        crates/gto-hu/src/solver/blueprint.rs crates/gto-hu/tests/test_bench_memory.rs
git commit -m "feat(gto-hu): blueprint memory model + f32 projection (G-A3 evidence)"
```

G-A3 honesty note for the report: the f32 and board-bucketing *factors* are
projections (those features are P0b work); the model itself is validated
against real allocations (test) and a real run (WP2). Final confirmation
lands with the first P0b M=25 run — say so explicitly in the report.

---

### Task 9: Profiling, thread scaling, algorithm review, audit report

**Files:**
- Create: `gto/docs/reviews/2026-07-19-p0a-audit/threads/*.json`
- Create: `gto/docs/reviews/2026-07-19-p0a-audit/profiles/` (flamegraph SVG / perf output, if obtainable)
- Create: `gto/docs/reviews/2026-07-19-p0a-algorithm-audit.md` (the deliverable)

**Interfaces:**
- Consumes: everything above.
- Produces: the audit report with G-A1/G-A2/G-A3 verdicts and a go/no-go
  recommendation, presented to the user.

- [ ] **Step 1: Thread-scaling sweep on the blueprint (~1 h)**

```bash
cd /home/kazumasa/projects/gto
T=docs/reviews/2026-07-19-p0a-audit/threads
L=$(git rev-parse --short HEAD)
for n in 1 2 4 8 16; do
  cargo run --release -p gto-hu --bin solver-bench -- --case bp3_sample --iterations 100 --points 2 --threads $n --label "$L-t$n" --out $T/bp3_t$n.json
done
cd /home/kazumasa/projects && uv run --no-sync python -m gto.bench gto/docs/reviews/2026-07-19-p0a-audit/threads -o gto/docs/reviews/2026-07-19-p0a-audit/thread-report.md
```
Expected: iter/s from `elapsed_s` at the final checkpoint; WP2 anchor:
(leaf,m) rayon parallelism gave 7.7× on this workload. Note: each `--threads`
run is a fresh process (build_global can only be called once per process).

- [ ] **Step 2: Profiling (best-effort on WSL2)**

```bash
perf stat -e task-clock,context-switches,page-faults -- \
  cargo run --release -p gto-hu --bin solver-bench -- --case flop_srp100_AhKd7s_k24 --iterations 100 --points 2 2>&1 | tail -15
cargo flamegraph --release -p gto-hu --bin solver-bench --output docs/reviews/2026-07-19-p0a-audit/profiles/flop_k24.svg -- --case flop_srp100_AhKd7s_k24 --iterations 100 --points 1
```
**WSL2 caveat (expected, not a failure):** hardware counters
(cache-misses, instructions) are usually unavailable under WSL2, and
`perf`/`cargo flamegraph` may need `cargo install flamegraph` plus a
matching perf build. Capture what works; if flamegraphs are unobtainable,
record that in the report and substitute the coarse evidence we do have
(thread scaling + table_bytes vs RSS + per-street iteration costs). Do
**not** add profiling crates to the workspace for this.

- [ ] **Step 3: Write the audit report**

`gto/docs/reviews/2026-07-19-p0a-algorithm-audit.md` — structure:

```markdown
# P0a Algorithm Optimization Audit — Report

Date / commit / box (RTX 5080, RAM, WSL2 kernel)

## 1. Method
(reference cases, uniform ranges, solve-only timing, links to baselines)

## 2. Results
2.1 Baseline table (paste baseline-report.md)
2.2 Flop time-to-expl matrix (paste flop-report.md) → implied per-flop
    expl gate for spec §4.2 and Tier-1 grid hours at that gate
2.3 Variance reduction: sample / ms4 / ms16 / enumerate slopes + the
    time-to-expl winner at 0.3 bb and 0.15 bb
2.4 Thread scaling table; profiling findings (or the WSL2 caveat)
2.5 Memory model table (M × precision), WP2 23.95 GB cross-check

## 3. Algorithm review
- CFR variant + parameterization vs literature (CFR+/DCFR choices)
- Sampling scheme conclusion (which ChanceMode for P0b, with numbers)
- SIMD/vectorization and layout opportunities seen in profiles (P0b list,
  each with an expected-order-of-magnitude note; house protocol:
  reference impl → property/differential tests → optimize last)
- External sanity anchors, with citation dates: published open-source
  postflop solver timings and the Pluribus blueprint compute budget.
  State explicitly that these are order-of-magnitude anchors only
  (different trees, different abstractions).

## 4. Gate verdicts
| Gate | Target | Measured | Verdict |
| G-A1 | ≤ 12 min median per-flop to gate | … | go / no-go / re-scope |
| G-A2 | slope ≤ −0.85 | … | … |
| G-A3 | M=25 ≤ 48 GB (f32+bucketing projection) | … | conditional-go: model validated; confirm at first P0b M=25 run |

## 5. Recommendation
(what P0b should build, in what order; what the Tier-1 grid actually is
at the measured throughput; anything to re-negotiate in the spec)
```

Fill every section from the committed artifacts — no estimates where a
measurement exists. Where a verdict is `no-go` or `re-scope`, write the
concrete alternative (e.g. "at X min/flop, Tier 1 = N flops × M configs
fits the 2-week budget; either accept N or fund optimization Y first").

- [ ] **Step 4: Commit and present**

```bash
cd /home/kazumasa/projects/gto
git add docs/reviews/2026-07-19-p0a-audit docs/reviews/2026-07-19-p0a-algorithm-audit.md
git commit -m "docs(gto): P0a algorithm audit report with G-A1..3 verdicts"
```

Present the gate-verdict table and recommendation to the user for the
go/no-go decision — P0b mass generation and app phases P2+ stay blocked
until the user accepts the verdicts (spec §5.0).

---

## Self-review notes (kept for the executor)

- Spec §5.0 coverage: harness (Tasks 1–4) → item 1; profiling +
  thread scaling (Task 9) → item 2; algorithm review (Task 9) → item 3;
  G-A1 (Task 6), G-A2 (Tasks 5+7), G-A3 (Task 8) → item 4; report
  (Task 9) → item 5.
- The only solver-numerics change is Task 7; it is fenced by the
  `test_perf_baseline` suite plus its own k=1 bit-identity test.
- API names copied from source on 2026-07-19 (`flop.rs`, `blueprint.rs`,
  `turn_river.rs`, `vector.rs`, `test_perf_baseline.rs`). Where a helper's
  existence was not verified (`TurnTreeConfig::srp()`, blueprint preflop
  range construction, `FlopSolver::average_strategy` ctx arity), the task
  says "verify against the actual code" — do that before writing.
- Long-running steps (5.2–5.3, 6.1, 7.7, 9.1) are sequential solo runs;
  everything else is minutes.
