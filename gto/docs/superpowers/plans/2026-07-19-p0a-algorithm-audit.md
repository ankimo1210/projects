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

**Review status: rev 2 — all findings from
`docs/reviews/2026-07-19-p0a-plan-review.md` incorporated.** P0-1 resolved by
user decision (2026-07-19): G-A3 is a validated-projection gate in P0a, and
the first real M=25 run (peak RSS ≤ 48 GB) is a blocking **P0b entry gate**
— the spec's §5.0 gate text carries the renegotiated wording. The other
findings are folded into the tasks: Task 4A recovery snapshots (P1-5),
seed-tripled G-A2 protocol with a pre-registered fit window (P1-4),
pre-registered G-A1 thresholds with timeout-as-censored semantics and a 3bet
tree case (P1-1), segmented wall-clock accounting (P1-2), MultiSample defined
as partial enumeration without replacement (P1-3), a capacity-vs-allocated
memory model with an RSS overhead anchor (P0-2), aligned `time_to()`
semantics (P2-1), self-describing run metadata (P2-2), and a branch
assertion instead of branch creation (P2-3).

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
- Any run expected to exceed 15 minutes must use the durable recovery
  snapshots from Task 4A. Default checkpoint interval is 30 minutes. Snapshot
  files live under `_data/gto/checkpoints/`, are never committed, and retain
  two valid generations so an interrupted write cannot destroy the previous
  restore point.
- Spec gate values (post-renegotiation, see spec §5.0): G-A1 median per-flop
  **artifact time (build + solve + final BR)** to the **pre-registered** expl
  threshold **≤ 12 min** — candidate thresholds {0.5, 0.3, 0.15, 0.05} bb,
  chosen by the user from the Pareto curve before the verdict; timeouts are
  censored no-go data, never a relaxed threshold. G-A2 fitted slope exponent
  **≤ −0.85** with the whole ≥3-seed interval below the bar, fit on the
  pre-registered window (checkpoints with iters ≥ max_iters/8). G-A3
  validated-projection: modeled M=25 f32(+bucketing) **≤ 48 GB**; real-run
  confirmation is a blocking P0b entry gate, not P0a.
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
  - `pub struct BenchCase { pub name: &'static str, pub config: &'static str, pub build: fn(u64) -> CaseSolver }`
    — `build` takes the run seed (P1-4: stochastic modes run ≥ 3 seeds;
    deterministic cases ignore the argument); `config` is a canonical
    human-readable description of tree/ranges/variant/abstraction recorded
    in the run JSON (P2-2)
  - `pub fn reference_cases() -> Vec<BenchCase>`

Reference set (uniform ranges — the audit measures solver speed, not
product content; uniform is reproducible and range-shape-independent):

| name | construction |
|---|---|
| `river_srp100` | `build_river_tree(5*BB, 97*BB, &StreetConfig::srp_river())`, board `2c 7d 9h Jh Kd` |
| `turn_srp100_enum` / `turn_srp100_sample` | `build_turn_river_tree(5*BB, 97*BB, &TurnTreeConfig::srp())`, board `2c 7d 9h Jh`, `Enumerate` / `Sample{seed:42}` |
| `flop_srp100_<board>_k24` for boards `AhKd7s`, `QsJh2c`, `8d8h3s` | `build_flop_tree(5*BB, 97*BB, &FlopTreeConfig::srp())`, `Sample{seed:42}`, `Abstraction{buckets_river:24, buckets_turn:16}` |
| `flop_srp100_AhKd7s_k64` | same, `buckets_river:64` |
| `flop_3bet100_AhKd7s_k24` | `build_flop_tree(18*BB, 89*BB, &FlopTreeConfig::threebet())`, board `Ah Kd 7s`, `Sample{seed}`, `Abstraction{24,16}` — the Tier-1 grid contains both SRP and 3bet trees, so G-A1 must measure both (review P1-1) |
| `bp3_sample` / `bp3_enum` | `BlueprintSolver::new(build_preflop_tree(100*BB), uniform, cfr_plus_default, flops [AhKd7s,QsJh2c,8d8h3s], equal weights, Abstraction{24,16}, sample=true/false, seed)` — the WP2 configuration |

(If `TurnTreeConfig::srp()` does not exist, use the literal `TurnTreeConfig`
from `test_perf_baseline.rs::turn_cfg()` but with production street configs
`StreetConfig::srp_turn()` / `srp_river()`; check `tree/` for the actual
constructor names before writing.)

- [ ] **Step 1: Confirm the work branch and clean scope**

```bash
cd /home/kazumasa/projects
test "$(git branch --show-current)" = "claude/gto-p0a-audit"
git status --short --branch
```

Expected: current branch is `claude/gto-p0a-audit`; no unrelated changes are
silently staged or overwritten.

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
            let mut s = (case.build)(42);
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
                     "flop_3bet100_AhKd7s_k24", "bp3_sample", "bp3_enum"] {
        assert!(names.contains(&expected), "missing case {expected}");
    }
}

#[test]
fn river_case_is_deterministic() {
    let case = reference_cases().into_iter().find(|c| c.name == "river_srp100").unwrap();
    let run = |mut s: CaseSolver| { s.run_chunk(5); s.expl().exploitability.to_bits() };
    assert_eq!(run((case.build)(42)), run((case.build)(42)));
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
// 3bet pot: 100bb stacks, open 2.5 + 3bet to 9 → 18bb pot, 89bb behind.
const TBP_POT: u32 = 18 * BB;
const TBP_STACK: u32 = 89 * BB;

const SRP_CFG: &str = "srp 5bb pot / 97bb stacks / uniform ranges / CFR+ / K_r=24 K_t=16";
const TBP_CFG: &str = "3bet 18bb pot / 89bb stacks / uniform ranges / CFR+ / K_r=24 K_t=16";
const BP_CFG: &str = "blueprint flops AhKd7s,QsJh2c,8d8h3s / 100bb / uniform / CFR+ / K_r=24 K_t=16";

fn abs24() -> Abstraction {
    Abstraction { buckets_river: 24, buckets_turn: 16 }
}

fn river_case(_seed: u64) -> CaseSolver {
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

fn flop_case(
    board: [u8; 3],
    buckets_river: usize,
    pot: u32,
    stack: u32,
    cfg: FlopTreeConfig,
    seed: u64,
) -> CaseSolver {
    let tree = build_flop_tree(pot, stack, &cfg);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    CaseSolver::Flop(Box::new(FlopSolver::new_abstracted(
        tree,
        board,
        ranges,
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed },
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

fn blueprint_case(sample: bool, seed: u64) -> CaseSolver {
    let tree = build_preflop_tree(100 * BB);
    let ranges = [uniform_excluding(&[]), uniform_excluding(&[])];
    let flops = bp_flops();
    let weights = vec![1.0; flops.len()];
    CaseSolver::Blueprint(Box::new(BlueprintSolver::new(
        tree, ranges, CfrVariant::cfr_plus_default(), flops, weights, abs24(), sample, seed,
    )))
}

pub fn reference_cases() -> Vec<BenchCase> {
    vec![
        BenchCase { name: "river_srp100", config: SRP_CFG, build: river_case },
        BenchCase { name: "turn_srp100_enum", config: SRP_CFG,
                    build: |_| turn_case(ChanceMode::Enumerate) },
        BenchCase { name: "turn_srp100_sample", config: SRP_CFG,
                    build: |seed| turn_case(ChanceMode::Sample { seed }) },
        BenchCase { name: "flop_srp100_AhKd7s_k24", config: SRP_CFG,
                    build: |s| flop_case([c("Ah"), c("Kd"), c("7s")], 24, SRP_POT, SRP_STACK, FlopTreeConfig::srp(), s) },
        BenchCase { name: "flop_srp100_QsJh2c_k24", config: SRP_CFG,
                    build: |s| flop_case([c("Qs"), c("Jh"), c("2c")], 24, SRP_POT, SRP_STACK, FlopTreeConfig::srp(), s) },
        BenchCase { name: "flop_srp100_8d8h3s_k24", config: SRP_CFG,
                    build: |s| flop_case([c("8d"), c("8h"), c("3s")], 24, SRP_POT, SRP_STACK, FlopTreeConfig::srp(), s) },
        BenchCase { name: "flop_srp100_AhKd7s_k64", config: SRP_CFG,
                    build: |s| flop_case([c("Ah"), c("Kd"), c("7s")], 64, SRP_POT, SRP_STACK, FlopTreeConfig::srp(), s) },
        BenchCase { name: "flop_3bet100_AhKd7s_k24", config: TBP_CFG,
                    build: |s| flop_case([c("Ah"), c("Kd"), c("7s")], 24, TBP_POT, TBP_STACK, FlopTreeConfig::threebet(), s) },
        BenchCase { name: "bp3_sample", config: BP_CFG, build: |s| blueprint_case(true, s) },
        BenchCase { name: "bp3_enum", config: BP_CFG, build: |s| blueprint_case(false, s) },
    ]
}
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
- Produces (used by Task 3 CLI, Task 4 Python reader, Task 4A sidecar):
  - `pub struct Checkpoint { pub iters: u32, pub solve_s: f64, pub br_s: f64, pub expl: f64, pub br: [f64; 2] }`
    — `solve_s` = cumulative solve-only seconds at this checkpoint; `br_s` =
    seconds this checkpoint's exact best-response evaluation took (P1-2:
    measurement cost tracked separately from solver throughput)
  - `pub fn geometric_schedule(max_iters: u32, points: usize) -> Vec<u32>` — ascending cumulative iteration counts, last == max_iters
  - `pub struct RunTiming { pub build_s: f64, pub solve_s: f64, pub checkpoint_br_s: f64, pub final_br_s: f64 }`
    — `build_s` is filled by the CLI (solver construction time);
    `final_br_s` = the last checkpoint's BR time (the run's final BR IS the
    last checkpoint's evaluation); `checkpoint_br_s` = Σ br_s of the
    non-final checkpoints. **G-A1 artifact time = build_s +
    solve-time-at-threshold + final_br_s** (assembled in Task 4's Python).
  - `pub fn run_with_checkpoints(s: &mut CaseSolver, schedule: &[u32]) -> (Vec<Checkpoint>, RunTiming)` — returns `build_s: 0.0` for the caller to fill
  - `pub fn peak_rss_mb() -> f64`
  - `pub fn cpu_model() -> String` (/proc/cpuinfo model name) and
    `pub fn kernel_release() -> String` (/proc/sys/kernel/osrelease)
  - `pub struct RunRecord` — P2-2 self-describing metadata. Fields:
    `schema_version: u32` (=1), `case: String`, `config: String` (the
    BenchCase canonical config), `label: String`, `git_commit: String`
    (full SHA), `dirty: bool`, `seed: u64`, `iterations: u32`,
    `points: usize`, `threads: usize`, `build_profile: &'static str`
    (`"release"`/`"debug"` via `cfg!(debug_assertions)`), `cpu: String`,
    `kernel: String`, `cmdline: String`, `table_bytes: usize`,
    `peak_rss_mb: f64`, `resume_count: u32` (0 until Task 4A fills it),
    `timing: RunTiming`, `checkpoints: Vec<Checkpoint>`
  - `impl RunRecord { pub fn to_json(&self) -> String }` — top-level keys
    exactly as the field names; `timing` nested with keys `build_s`,
    `solve_s`, `checkpoint_br_s`, `final_br_s`; checkpoint objects with
    keys `iters`, `solve_s`, `br_s`, `expl`, `br0`, `br1`. (Values under
    our control contain no JSON-special characters; the writer does not
    escape — documented in the module.)

- [ ] **Step 1: Write the failing tests**

`gto/crates/gto-hu/tests/test_bench_run.rs`:

```rust
use gto_hu::bench::{
    geometric_schedule, peak_rss_mb, reference_cases, run_with_checkpoints, Checkpoint,
    RunRecord, RunTiming,
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
fn river_checkpoints_are_deterministic_with_separated_timing() {
    let case = reference_cases().into_iter().find(|c| c.name == "river_srp100").unwrap();
    let sched = geometric_schedule(40, 4);
    let mut a = (case.build)(42);
    let mut b = (case.build)(42);
    let (ca, ta) = run_with_checkpoints(&mut a, &sched);
    let (cb, _tb) = run_with_checkpoints(&mut b, &sched);
    assert_eq!(ca.len(), sched.len());
    for (x, y) in ca.iter().zip(&cb) {
        assert_eq!(x.iters, y.iters);
        assert_eq!(x.expl.to_bits(), y.expl.to_bits(), "nondeterministic expl");
        assert!(x.solve_s >= 0.0 && x.br_s > 0.0);
    }
    assert!(ca.last().unwrap().expl < ca.first().unwrap().expl, "no convergence");
    // Timing identities reconcile (P1-2).
    assert_eq!(ta.build_s, 0.0, "build_s is the caller's to fill");
    assert!((ta.solve_s - ca.last().unwrap().solve_s).abs() < 1e-9);
    let br_sum: f64 = ca.iter().map(|c| c.br_s).sum();
    assert!((ta.checkpoint_br_s + ta.final_br_s - br_sum).abs() < 1e-9);
    assert!((ta.final_br_s - ca.last().unwrap().br_s).abs() < 1e-12);
}

#[test]
fn json_has_expected_keys_and_metadata() {
    let rec = RunRecord {
        schema_version: 1,
        case: "x".into(), config: "cfg".into(), label: "l".into(),
        git_commit: "deadbeef".into(), dirty: false, seed: 42,
        iterations: 10, points: 2, threads: 4,
        build_profile: "release", cpu: "cpu".into(), kernel: "k".into(),
        cmdline: "solver-bench".into(),
        table_bytes: 123, peak_rss_mb: 1.5, resume_count: 0,
        timing: RunTiming { build_s: 0.1, solve_s: 0.5, checkpoint_br_s: 0.2, final_br_s: 0.3 },
        checkpoints: vec![Checkpoint { iters: 1, solve_s: 0.5, br_s: 0.3, expl: 2.0, br: [1.0, 1.0] }],
    };
    let j = rec.to_json();
    for key in ["\"schema_version\"", "\"case\"", "\"config\"", "\"label\"",
                "\"git_commit\"", "\"dirty\"", "\"seed\"", "\"iterations\"",
                "\"points\"", "\"threads\"", "\"build_profile\"", "\"cpu\"",
                "\"kernel\"", "\"cmdline\"", "\"table_bytes\"",
                "\"peak_rss_mb\"", "\"resume_count\"", "\"timing\"",
                "\"build_s\"", "\"solve_s\"", "\"checkpoint_br_s\"",
                "\"final_br_s\"", "\"checkpoints\"", "\"iters\"", "\"br_s\"",
                "\"expl\"", "\"br0\"", "\"br1\""] {
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
    /// Cumulative solve-only seconds at this checkpoint (construction and
    /// best-response evaluation excluded).
    pub solve_s: f64,
    /// Seconds this checkpoint's exact best-response evaluation took.
    pub br_s: f64,
    pub expl: f64,
    pub br: [f64; 2],
}

pub struct RunTiming {
    pub build_s: f64,
    pub solve_s: f64,
    pub checkpoint_br_s: f64,
    pub final_br_s: f64,
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

/// Run to each cumulative checkpoint. Solve and best-response time are
/// accumulated separately (P1-2): solver throughput must not be distorted
/// by measurement cost, and the G-A1 artifact time needs build + solve +
/// ONE final BR, which Task 4's Python assembles from RunTiming.
/// `build_s` is returned as 0.0 for the caller (CLI) to fill.
pub fn run_with_checkpoints(
    s: &mut CaseSolver,
    schedule: &[u32],
) -> (Vec<Checkpoint>, RunTiming) {
    let mut out = Vec::with_capacity(schedule.len());
    let mut done = 0u32;
    let mut solve_s = 0.0f64;
    let mut br_total = 0.0f64;
    for &target in schedule {
        let chunk = target - done;
        let t = Instant::now();
        s.run_chunk(chunk);
        solve_s += t.elapsed().as_secs_f64();
        done = target;
        let t = Instant::now();
        let e = s.expl();
        let br_s = t.elapsed().as_secs_f64();
        br_total += br_s;
        out.push(Checkpoint {
            iters: done,
            solve_s,
            br_s,
            expl: e.exploitability,
            br: e.br_value,
        });
    }
    let final_br_s = out.last().map(|cp| cp.br_s).unwrap_or(0.0);
    let timing = RunTiming {
        build_s: 0.0,
        solve_s,
        checkpoint_br_s: br_total - final_br_s,
        final_br_s,
    };
    (out, timing)
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

/// Best-effort host identity for self-describing runs (P2-2).
pub fn cpu_model() -> String {
    std::fs::read_to_string("/proc/cpuinfo")
        .unwrap_or_default()
        .lines()
        .find_map(|l| {
            l.strip_prefix("model name")
                .map(|r| r.trim_start_matches([':', '\t', ' ']).to_string())
        })
        .unwrap_or_default()
}

pub fn kernel_release() -> String {
    std::fs::read_to_string("/proc/sys/kernel/osrelease")
        .unwrap_or_default()
        .trim()
        .to_string()
}

/// Self-describing run record (P2-2). Field values are under our control
/// and contain no JSON-special characters; the writer does not escape.
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

impl RunRecord {
    pub fn to_json(&self) -> String {
        let cps: Vec<String> = self.checkpoints.iter().map(|c| format!(
            "    {{\"iters\": {}, \"solve_s\": {:.3}, \"br_s\": {:.3}, \"expl\": {:.6}, \"br0\": {:.6}, \"br1\": {:.6}}}",
            c.iters, c.solve_s, c.br_s, c.expl, c.br[0], c.br[1]
        )).collect();
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
                "  \"timing\": {{\"build_s\": {:.3}, \"solve_s\": {:.3}, \"checkpoint_br_s\": {:.3}, \"final_br_s\": {:.3}}},\n",
                "  \"checkpoints\": [\n{}\n  ]\n}}\n",
            ),
            self.schema_version,
            self.case, self.config, self.label,
            self.git_commit, self.dirty, self.seed,
            self.iterations, self.points, self.threads,
            self.build_profile, self.cpu, self.kernel,
            self.cmdline,
            self.table_bytes, self.peak_rss_mb, self.resume_count,
            self.timing.build_s, self.timing.solve_s,
            self.timing.checkpoint_br_s, self.timing.final_br_s,
            cps.join(",\n")
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
- Produces: CLI `solver-bench --case NAME --iterations N [--points K=10] [--threads T=0] [--seed S=42] [--label STR] [--git-commit SHA] [--dirty 0|1] [--out FILE]`; `--list` prints case names. `--threads 0` = rayon default. `--seed` feeds `BenchCase::build` (P1-4 multi-seed runs); `--git-commit`/`--dirty` are recorded verbatim in the JSON (P2-2 — the run commands pass `$(git rev-parse HEAD)` and a porcelain-derived flag). Exit 2 on bad args (house style `usage()`).

- [ ] **Step 1: Write the bin**

`gto/crates/gto-hu/src/bin/solver_bench.rs`:

```rust
//! solver-bench — P0a audit driver: run a named reference case with
//! exploitability checkpoints; write a self-describing RunRecord JSON.
//!
//! Example:
//!   solver-bench --case river_srp100 --iterations 2000 --points 10 \
//!     --seed 42 --label baseline --git-commit "$(git rev-parse HEAD)" \
//!     --dirty "$([ -z "$(git status --porcelain)" ] && echo 0 || echo 1)" \
//!     --out baselines/river.json

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
    let args: Vec<String> = argv[1..].to_vec();
    let mut case_name = String::new();
    let mut iterations: u32 = 0;
    let mut points: usize = 10;
    let mut threads: usize = 0;
    let mut seed: u64 = 42;
    let mut label = String::new();
    let mut git_commit = String::new();
    let mut dirty = false;
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
            "--seed" => { seed = need(i).parse().unwrap_or_else(|_| usage()); i += 2; }
            "--label" => { label = need(i); i += 2; }
            "--git-commit" => { git_commit = need(i); i += 2; }
            "--dirty" => { dirty = need(i) == "1"; i += 2; }
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

    eprintln!("building {case_name} (seed {seed}) …");
    let t = Instant::now();
    let mut solver = (case.build)(seed);
    let build_s = t.elapsed().as_secs_f64();
    eprintln!("built in {build_s:.1}s, table_bytes = {}", solver.table_bytes());
    let sched = geometric_schedule(iterations, points);
    let (cps, mut timing) = run_with_checkpoints(&mut solver, &sched);
    timing.build_s = build_s;
    for c in &cps {
        eprintln!("iters {:>7}  solve {:>9.1}s  br {:>7.1}s  expl {:.4} bb  (br0 {:.4} / br1 {:.4})",
                  c.iters, c.solve_s, c.br_s, c.expl, c.br[0], c.br[1]);
    }
    let rec = RunRecord {
        schema_version: 1,
        case: case_name,
        config: case.config.to_string(),
        label,
        git_commit,
        dirty,
        seed,
        iterations,
        points,
        threads: if threads == 0 { rayon::current_num_threads() } else { threads },
        build_profile: if cfg!(debug_assertions) { "debug" } else { "release" },
        cpu: cpu_model(),
        kernel: kernel_release(),
        cmdline: argv.join(" "),
        table_bytes: solver.table_bytes(),
        peak_rss_mb: peak_rss_mb(),
        resume_count: 0,
        timing,
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
  - `fit_window(checkpoints: list[dict], min_frac: float = 0.125) -> tuple[list, list]` — the **pre-registered G-A2 fit window** (P1-4): keeps checkpoints with `iters ≥ max_iters × min_frac` (the latter convergence region), returns (iters, expl) for `fit_slope`
  - `time_to(target_expl: float, checkpoints: list[dict]) -> float | None` — first crossing in cumulative `solve_s`; linear interpolation of `solve_s` against `log(expl)` between the bracketing checkpoints (P2-1: this definition is exact when the crossing lands on a checkpoint, and the tests compute the expected interpolated value from the same definition); None if never reached
  - `artifact_time_to(target_expl: float, run: dict) -> float | None` — **the G-A1 metric**: `timing.build_s + time_to(...) + timing.final_br_s`
  - `load_dir(path: Path) -> list[dict]` — parsed `*.json`, sorted by (case, seed)
  - `aggregate_seeds(runs: list[dict], min_frac: float = 0.125) -> list[dict]` — group by `case`; per case: `n_seeds`, windowed-slope median/min/max (P1-4 interval rule), the member runs
  - `render_markdown(runs: list[dict], targets: tuple[float, ...] = (0.5, 0.3, 0.15, 0.05)) -> str` — one row per **case** (seeds aggregated): seed count, slope median [min, max], median artifact-time per target (`censored` when only some seeds reached it, `—` when none), max peak RSS
  - CLI: `uv run --no-sync python -m gto.bench <dir> [-o report.md]`

- [ ] **Step 1: Write the failing tests**

`gto/tests/test_bench_report.py`:

```python
import json
import math

from gto.bench import (
    aggregate_seeds, artifact_time_to, fit_slope, fit_window, load_dir,
    render_markdown, time_to,
)


def _synthetic_run(case="synth", seed=42, c=100.0, slope=-1.0, secs_per_iter=0.01):
    iters = [10, 20, 40, 80, 160, 320]
    return {
        "schema_version": 1, "case": case, "config": "cfg", "label": "t",
        "git_commit": "deadbeef", "dirty": False, "seed": seed,
        "iterations": 320, "points": 6, "threads": 1,
        "build_profile": "release", "cpu": "c", "kernel": "k", "cmdline": "x",
        "table_bytes": 1, "peak_rss_mb": 10.0, "resume_count": 0,
        "timing": {"build_s": 2.0, "solve_s": 3.2,
                   "checkpoint_br_s": 0.5, "final_br_s": 1.0},
        "checkpoints": [
            {"iters": t, "solve_s": t * secs_per_iter, "br_s": 0.1,
             "expl": c * t ** slope, "br0": 0.0, "br1": 0.0}
            for t in iters
        ],
    }


def test_fit_slope_recovers_exponent():
    cps = _synthetic_run(slope=-1.0)["checkpoints"]
    s = fit_slope([c["iters"] for c in cps], [c["expl"] for c in cps])
    assert math.isclose(s, -1.0, abs_tol=1e-9)


def test_fit_window_keeps_the_latter_region():
    cps = _synthetic_run()["checkpoints"]
    it, ex = fit_window(cps, min_frac=0.125)
    assert it == [40, 80, 160, 320]  # iters >= 320/8
    assert len(ex) == 4


def test_time_to_exact_at_checkpoint_and_interpolates():
    cps = _synthetic_run(c=100.0, slope=-1.0)["checkpoints"]
    # Crossing exactly AT a checkpoint: expl(80) = 1.25 -> solve_s = 0.8.
    assert math.isclose(time_to(1.25, cps), 0.8, rel_tol=1e-9)
    # Between checkpoints: expected value computed from the SAME definition
    # (linear in solve_s against log expl) — P2-1 alignment.
    lo, hi = cps[3], cps[4]  # expl 1.25 -> 0.625 over solve_s 0.8 -> 1.6
    f = (math.log(lo["expl"]) - math.log(1.0)) / (math.log(lo["expl"]) - math.log(hi["expl"]))
    expected = lo["solve_s"] + f * (hi["solve_s"] - lo["solve_s"])
    assert math.isclose(time_to(1.0, cps), expected, rel_tol=1e-9)
    assert time_to(1e-9, cps) is None


def test_artifact_time_adds_build_and_final_br():
    run = _synthetic_run()
    assert math.isclose(artifact_time_to(1.25, run), 2.0 + 0.8 + 1.0, rel_tol=1e-9)
    assert artifact_time_to(1e-9, run) is None


def test_load_aggregate_and_render(tmp_path):
    for s in (1, 2, 3):
        (tmp_path / f"a_s{s}.json").write_text(json.dumps(_synthetic_run("case_a", seed=s)))
    (tmp_path / "b.json").write_text(json.dumps(_synthetic_run("case_b")))
    runs = load_dir(tmp_path)
    assert [r["case"] for r in runs] == ["case_a", "case_a", "case_a", "case_b"]
    agg = aggregate_seeds(runs)
    a = next(r for r in agg if r["case"] == "case_a")
    assert a["n_seeds"] == 3
    assert math.isclose(a["slope_median"], -1.0, abs_tol=1e-9)
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

from gto.bench.report import (
    aggregate_seeds,
    artifact_time_to,
    fit_slope,
    fit_window,
    load_dir,
    render_markdown,
    time_to,
)

__all__ = [
    "aggregate_seeds",
    "artifact_time_to",
    "fit_slope",
    "fit_window",
    "load_dir",
    "render_markdown",
    "time_to",
]
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


def fit_window(checkpoints: list[dict], min_frac: float = 0.125) -> tuple[list, list]:
    """Pre-registered G-A2 fit window (review P1-4): keep the latter
    convergence region, iters >= max_iters * min_frac, so transient early
    behavior does not contaminate the asymptotic slope."""
    mx = max(c["iters"] for c in checkpoints)
    keep = [c for c in checkpoints if c["iters"] >= mx * min_frac]
    return [c["iters"] for c in keep], [c["expl"] for c in keep]


def time_to(target_expl: float, checkpoints: list[dict]) -> float | None:
    """Cumulative solve-seconds until expl first reaches target.

    Definition (review P2-1): linear interpolation of cumulative solve_s
    against log(expl) between the bracketing checkpoints. When the
    crossing lands exactly on a checkpoint the interpolation factor is 1,
    so the checkpoint's own solve_s is returned. None if never reached.
    """
    prev = None
    for cp in checkpoints:
        if cp["expl"] <= target_expl:
            if prev is None:
                return float(cp["solve_s"])
            f = (math.log(prev["expl"]) - math.log(target_expl)) / (
                math.log(prev["expl"]) - math.log(cp["expl"])
            )
            return float(prev["solve_s"] + f * (cp["solve_s"] - prev["solve_s"]))
        prev = cp
    return None


def artifact_time_to(target_expl: float, run: dict) -> float | None:
    """G-A1 metric: build + solve-to-target + one final best response."""
    t = time_to(target_expl, run["checkpoints"])
    if t is None:
        return None
    tm = run["timing"]
    return float(tm["build_s"] + t + tm["final_br_s"])


def load_dir(path: Path) -> list[dict]:
    runs = [json.loads(p.read_text()) for p in sorted(Path(path).glob("*.json"))]
    return sorted(runs, key=lambda r: (r["case"], r.get("seed", 0)))


def aggregate_seeds(runs: list[dict], min_frac: float = 0.125) -> list[dict]:
    """Group runs by case; windowed-slope median and seed-level [min, max]
    interval (review P1-4: G-A2 passes only if the WHOLE interval is below
    the bar)."""
    # Group by (case, label): seed replicas share a label and aggregate;
    # thread-sweep runs of one case carry distinct labels and stay apart.
    by_key: dict[tuple[str, str], list[dict]] = {}
    for r in runs:
        by_key.setdefault((r["case"], r.get("label", "")), []).append(r)
    out = []
    for (case, label), rs in sorted(by_key.items()):
        slopes = sorted(fit_slope(*fit_window(r["checkpoints"], min_frac)) for r in rs)
        out.append({
            "case": case,
            "label": label,
            "n_seeds": len(rs),
            "slope_median": float(np.median(slopes)),
            "slope_min": slopes[0],
            "slope_max": slopes[-1],
            "runs": rs,
        })
    return out


def _fmt_t(seconds: float) -> str:
    return f"{seconds / 60:.1f}m" if seconds >= 60 else f"{seconds:.1f}s"


def render_markdown(runs: list[dict], targets: tuple[float, ...] = (0.5, 0.3, 0.15, 0.05)) -> str:
    """One row per case, seeds aggregated. Artifact-time cells: median when
    every seed reached the target, `censored` when only some did (review
    P1-1: partial timeouts are surfaced, never averaged away), `—` when
    none did."""
    head = (
        "| case | label | seeds | slope median [min, max] | "
        + " | ".join(f"t→{t}bb" for t in targets)
        + " | peak RSS |\n"
    )
    sep = "|" + "---|" * (5 + len(targets)) + "\n"
    rows = []
    for a in aggregate_seeds(runs):
        cells = [
            a["case"], a["label"], str(a["n_seeds"]),
            f"{a['slope_median']:.2f} [{a['slope_min']:.2f}, {a['slope_max']:.2f}]",
        ]
        for t in targets:
            ts = [artifact_time_to(t, r) for r in a["runs"]]
            reached = [x for x in ts if x is not None]
            if len(reached) == len(ts) and reached:
                cells.append(_fmt_t(float(np.median(reached))))
            elif reached:
                cells.append("censored")
            else:
                cells.append("—")
        rss = max(r["peak_rss_mb"] for r in a["runs"])
        cells.append(f"{rss / 1024:.1f} GB")
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

### Task 4A: Durable solver checkpoint/resume (blocking for long runs)

This task is distinct from the exploitability checkpoints in Task 2. Those
are measurements; this task persists the complete mutable CFR state so a
crash, OOM, WSL restart, or reboot loses at most one checkpoint interval.

**Files:**
- Create: `gto/crates/gto-hu/src/checkpoint.rs` (format, CRC, atomic rotation)
- Modify: `gto/crates/gto-hu/src/lib.rs`
- Modify: `gto/crates/gto-hu/src/solver/rng.rs` (exact state export/import)
- Modify: `gto/crates/gto-hu/src/solver/flop.rs` (stream mutable state)
- Modify: `gto/crates/gto-hu/src/solver/blueprint.rs` (preflop + subgames)
- Modify: `gto/crates/gto-hu/src/bench.rs` (CaseSolver save/restore hooks)
- Modify: `gto/crates/gto-hu/src/bin/solver_bench.rs`
- Modify: `gto/crates/gto-hu/src/bin/solve_flop.rs`
- Modify: `gto/crates/gto-hu/src/bin/solve_blueprint.rs`
- Test: `gto/crates/gto-hu/tests/test_checkpoint_resume.rs`

**Scope:** FlopSolver and BlueprintSolver are mandatory because they own the
multi-hour P0 runs. The `CaseSolver` interface may return a clear unsupported
error for River/TurnRiver initially; their planned P0a runs are shorter and
can be added after the blocking paths are proven. Do not generalize all four
solvers before the two long-running paths work end to end.

**Snapshot contract:**

- Canonical location:
  `_data/gto/checkpoints/<run-id>/checkpoint-<iteration>.bin`; never under
  `gto/`, never committed.
- Hand-rolled little-endian binary, no new dependency. Header fields: magic,
  schema version, solver kind, endianness marker, exact git commit/build id,
  canonical configuration fingerprint, completed iteration, payload length.
- Footer: payload length repeated plus a streaming CRC64. This is accidental
  corruption detection, not a security boundary.
- Persist every mutable value required for exact continuation: iteration;
  regrets; strategy sums; lazy slab presence/order; `last_discount_iter`;
  DCFR prefix arrays; raw SplitMix64 state; Blueprint preflop tables; and the
  mutable state of every `(leaf, flop)` subgame.
- Rebuild immutable trees, showdown tables, bucket maps, ranges, boards, and
  equity tables from the canonical CLI/case configuration, then require the
  stored fingerprint to match before applying mutable state.
- Write directly through `BufWriter` + checksum wrapper. Never serialize the
  full solver into an in-memory `Vec<u8>` or clone all tables.
- Commit protocol: write `checkpoint.tmp`, flush, `sync_all`, rename to the
  numbered checkpoint, fsync the directory where supported, then atomically
  replace `LATEST`. Keep the newest two validated numbered checkpoints.
- Recovery tries `LATEST`, then the prior generation. A partial/corrupt newest
  file must not prevent recovery from the previous valid snapshot.
- Strict compatibility: reject solver-kind, config, schema, build-commit,
  payload-length, or CRC mismatch. P0a has no `--force-resume` escape hatch.

**CLI contract:**

```text
--checkpoint-dir PATH
--checkpoint-every-minutes N     # default 30 for long runs; 0 disables
--checkpoint-every-iters N       # optional deterministic test/override
--resume auto|PATH               # auto = newest valid generation
--keep-checkpoints N             # default 2, minimum 2
```

Checkpoint only between complete CFR iterations, after both traversers have
finished. `solver-bench` also persists its completed analytical checkpoints,
cumulative active solve/BR timing, and process-segment list in an atomic
sidecar. Downtime is not counted as active compute; the final RunRecord records
`resume_count` and all timing segments.

- [ ] **Step 1: Write failing exact-resume tests**

Cover all of the following with tiny trees/buckets:

1. Sampled FlopSolver: uninterrupted 80 iterations vs 30 + save/load + 50;
   exploitability bits and a full mutable-state/strategy checksum must match.
2. BlueprintSolver: uninterrupted 20 vs 7 + save/load + 13, including its
   preflop tables and all `(leaf, flop)` subgames; final checksum bit-identical.
3. DCFR sampled mode: resume across a skipped-context lazy-discount interval;
   checks `last_discount_iter`, prefix arrays, and RNG are restored.
4. Configuration mismatch: changing board, seed, abstraction, variant, tree,
   or flop list must fail before mutating the rebuilt solver.
5. Corruption/truncation: a bad newest generation is rejected and `auto`
   falls back to the prior valid generation.
6. Interrupted write: a leftover `.tmp` does not change `LATEST` and does not
   remove either prior generation.

```bash
cd /home/kazumasa/projects/gto
cargo test -p gto-hu --test test_checkpoint_resume 2>&1 | tail -8
```

Expected before implementation: unresolved checkpoint APIs.

- [ ] **Step 2: Implement the streaming format and solver hooks**

Keep binary primitives and CRC code in `checkpoint.rs`. Put private-field
state traversal inside `flop.rs` and `blueprint.rs`; do not make solver fields
public merely for serialization. Expose the raw SplitMix64 state through a
small crate-private getter/constructor and pin it with a sequence-continuation
test.

Run the focused tests, then the bit-identity suite:

```bash
cargo test -p gto-hu --test test_checkpoint_resume
cargo test -p gto-hu --test test_perf_baseline
cargo test -p gto-hu
```

- [ ] **Step 3: Add CLI rotation and automatic resume**

The original command remains the source of immutable configuration. On
`--resume auto`, rebuild from those arguments, verify the snapshot fingerprint,
restore mutable state, and run only the remaining iterations. If the snapshot
already reached the requested total, do not train again; proceed to final BR
and artifact export.

Example recovery flow:

```bash
cd /home/kazumasa/projects/gto
CK=../_data/gto/checkpoints/p0a/bp3_sample
cargo run --release -p gto-hu --bin solver-bench -- \
  --case bp3_sample --iterations 1500 --points 8 \
  --checkpoint-dir "$CK" --checkpoint-every-minutes 30 --resume auto \
  --out docs/reviews/2026-07-19-p0a-audit/baselines/bp3_sample.json
```

Re-running the same command after termination resumes from the latest valid
snapshot. A different case/configuration must fail loudly.

- [ ] **Step 4: Fault-injection and operational validation**

Run a release-mode tiny/medium checkpointed job, terminate it during both
training and snapshot write, then rerun the same command. Record:

- restored iteration and lost iterations/time;
- snapshot bytes and write/read seconds;
- peak RSS delta during save/load;
- final checksum vs an uninterrupted control;
- fallback behavior after deliberate truncation of a copied newest snapshot.

Acceptance targets:

- final result bit-identical to uninterrupted execution;
- no valid prior generation lost during a failed write;
- maximum lost active compute <= configured interval (default 30 min);
- streaming save peak-RSS increase <= 256 MiB;
- checkpoint overhead target <= 10% of active wall time at the default
  interval. If size/write speed makes the loss-window and overhead targets
  incompatible, stop and present the measured trade-off instead of silently
  relaxing either target.

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/checkpoint.rs crates/gto-hu/src/lib.rs \
        crates/gto-hu/src/solver/rng.rs crates/gto-hu/src/solver/flop.rs \
        crates/gto-hu/src/solver/blueprint.rs crates/gto-hu/src/bench.rs \
        crates/gto-hu/src/bin/solver_bench.rs crates/gto-hu/src/bin/solve_flop.rs \
        crates/gto-hu/src/bin/solve_blueprint.rs \
        crates/gto-hu/tests/test_checkpoint_resume.rs
git commit -m "feat(gto-hu): durable bit-identical checkpoint and resume for long solves"
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

Runtime notes: river ≈ minutes; turn sample ≈ tens of minutes per seed;
`bp3_sample` 1500 iters ≈ 40 min **per seed × 3 seeds ≈ 2 h** (P1-4:
stochastic modes run seeds {42, 1042, 9042}; deterministic enumerate runs
once); `bp3_enum` multiplies per-iteration cost by roughly the number of
legal turns (≈ 45×) — 100 iterations ≈ 2 h. Total for this task ≈ 5 h. Run
sequentially, solo on the box. Blueprint checkpoints each pay an exact
best-response evaluation — keep `--points 8`.

Every command expected to exceed 15 minutes must add
`--checkpoint-dir ../_data/gto/checkpoints/p0a/<case> \
--checkpoint-every-minutes 30 --resume auto`. A restarted run must append a
new timing segment and preserve the earlier analytical checkpoints.

- [ ] **Step 1: Fast set (river + turn, ~1.5 h total)**

```bash
cd /home/kazumasa/projects/gto
B=docs/reviews/2026-07-19-p0a-audit/baselines
GC=$(git rev-parse HEAD)
DTY=$([ -z "$(git status --porcelain)" ] && echo 0 || echo 1)
META="--label baseline --git-commit $GC --dirty $DTY"
cargo run --release -p gto-hu --bin solver-bench -- --case river_srp100     --iterations 2000 --points 10 $META --out $B/river_srp100.json
cargo run --release -p gto-hu --bin solver-bench -- --case turn_srp100_enum --iterations 400  --points 8  $META --out $B/turn_srp100_enum.json
for S in 42 1042 9042; do
  cargo run --release -p gto-hu --bin solver-bench -- --case turn_srp100_sample --iterations 4000 --points 10 --seed $S $META --out $B/turn_srp100_sample_s$S.json
done
```
Expected: five JSON files; expl decreasing across checkpoints in each.

- [ ] **Step 2: Blueprint sample-mode slopes, 3 seeds (~2 h)**

```bash
for S in 42 1042 9042; do
  cargo run --release -p gto-hu --bin solver-bench -- --case bp3_sample --iterations 1500 --points 8 --seed $S $META \
    --checkpoint-dir ../_data/gto/checkpoints/p0a/bp3_sample_s$S --checkpoint-every-minutes 30 --resume auto \
    --out $B/bp3_sample_s$S.json
done
```
Expected: final expl per seed in the ~1.5 bb range (WP2: 1.506 bb at 1500
iters, seed 42); windowed slope near −0.5 per seed, with the seed spread
becoming the G-A2 baseline interval.

- [ ] **Step 3: Blueprint enumerate-mode slope (deterministic, 1 run, ~2 h)**

```bash
cargo run --release -p gto-hu --bin solver-bench -- --case bp3_enum --iterations 100 --points 6 $META \
  --checkpoint-dir ../_data/gto/checkpoints/p0a/bp3_enum --checkpoint-every-minutes 30 --resume auto \
  --out $B/bp3_enum.json
```
Expected: much higher per-iteration cost; slope fitted on the windowed
points. This is the core G-A2 comparison: wall-clock-to-quality (via
`artifact_time_to`), not only slope-per-iteration (P1-4).

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
- Produces: the **quality/time Pareto evidence** for G-A1 over the
  pre-registered candidate thresholds **{0.5, 0.3, 0.15, 0.05} bb** —
  per-case median artifact time (`build + solve + final BR`) to each
  candidate, with unreached targets reported as **censored** evidence
  (P1-1: the threshold is chosen from this curve by the user BEFORE the
  G-A1 verdict; a timeout never becomes a relaxed threshold). Both SRP and
  3bet trees are measured because both are in the Tier-1 grid.

Runtime: ~49 min per 3k-iteration flop run at K_r=128 historically; K_r=24
is faster per iteration. Five runs below ≈ 4–6 h total. Run sequentially.
All runs use Task 4A recovery snapshots with a per-case checkpoint
directory and `--resume auto`.

Range-representativeness note for the report: uniform ranges keep every
combo live, which upper-bounds traversal and best-response cost relative
to chart-derived production ranges — the timing is conservative on ranges;
tree-shape coverage comes from measuring SRP and 3bet configs.

- [ ] **Step 1: Run the matrix (3 SRP boards × k24, AhKd7s × k64, AhKd7s 3bet × k24)**

```bash
cd /home/kazumasa/projects/gto
F=docs/reviews/2026-07-19-p0a-audit/flops
GC=$(git rev-parse HEAD)
DTY=$([ -z "$(git status --porcelain)" ] && echo 0 || echo 1)
META="--label flop-matrix --git-commit $GC --dirty $DTY"
for case in flop_srp100_AhKd7s_k24 flop_srp100_QsJh2c_k24 flop_srp100_8d8h3s_k24 flop_srp100_AhKd7s_k64 flop_3bet100_AhKd7s_k24; do
  cargo run --release -p gto-hu --bin solver-bench -- --case $case --iterations 3000 --points 8 $META \
    --checkpoint-dir ../_data/gto/checkpoints/p0a/$case --checkpoint-every-minutes 30 --resume auto \
    --out $F/$case.json
done
```
Expected: five JSONs. Sanity anchor: WP2-era full-SRP flop reached
expl ≈ 1.17 bb at 3k iterations (K_r=128) — K_r=24 values will differ but
should be same order of magnitude.

- [ ] **Step 2: Render the Pareto table, commit**

```bash
cd /home/kazumasa/projects
uv run --no-sync python -m gto.bench gto/docs/reviews/2026-07-19-p0a-audit/flops -o gto/docs/reviews/2026-07-19-p0a-audit/flop-report.md
cd gto && git add docs/reviews/2026-07-19-p0a-audit/flops docs/reviews/2026-07-19-p0a-audit/flop-report.md
git commit -m "bench(gto): P0a flop quality/time Pareto matrix (G-A1 evidence)"
```

The report presents, per candidate threshold: median artifact time across
the measured cases (censored rows shown as censored), and the implied
Tier-1 grid GPU-hours at that threshold. **The G-A1 verdict is NOT issued
in this task**: Task 9 presents the Pareto curve, the user picks the
per-file threshold, and only then is G-A1 judged (median artifact time at
the chosen threshold ≤ 12 min; a censored median is an automatic no-go at
that threshold).

---

### Task 7: `ChanceMode::MultiSample` spike (variance/cost mid-point)

**Files:**
- Modify: `gto/crates/gto-hu/src/solver/turn_river.rs` (ChanceMode enum + its sampling site)
- Modify: `gto/crates/gto-hu/src/solver/flop.rs` (seed extraction at `flop.rs:404`, mode match at `flop.rs:602`, `chance_sample`)
- Modify: `gto/crates/gto-hu/src/bench.rs` (add cases `bp3_ms4`, `bp3_ms16`, `flop_srp100_AhKd7s_k24_ms4`)
- Test: `gto/crates/gto-hu/tests/test_multisample.rs`

**Interfaces:**
- Consumes: existing `ChanceMode { Sample { seed }, Enumerate }`.
- Produces: `ChanceMode::MultiSample { seed: u64, samples: u8 }` — defined
  as **partial enumeration** (review P1-3 resolution): at a sampled chance
  deal the solver draws k DISTINCT cards (partial Fisher–Yates over the
  deal's index range, same SplitMix64 stream), recurses into each sampled
  subtree exactly as `Enumerate` recurses into all of them (regret and
  strategy updates below happen per visited subtree — the same
  within-iteration sequential accumulation `Enumerate` already performs,
  so this is NOT claimed to be k estimators under a frozen strategy), and
  returns `(n_pub / legal) · (1/k) · Σ v_i` as the chance-node EV — an
  unbiased estimator of the enumerated value under without-replacement
  sampling. Iteration and discount accounting are untouched: one traversal
  remains one CFR iteration regardless of k.
  `MultiSample { seed, samples: 1 }` must be **bit-identical** to
  `Sample { seed }` (the first Fisher–Yates draw makes exactly the one
  `next_index(n_pub)` call the current code makes). `samples = n_pub`
  visits every child like `Enumerate` but in shuffled order — equal in
  expectation, not bit-identical.

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

// Tolerances below are generous sanity bounds (review P1-3: differential
// and expectation checks against enumeration). Tighten from observed
// values if the implementation allows; never loosen without reporting.

#[test]
fn multisample_full_k_matches_enumeration_closely() {
    // k = n_pub visits every turn child like Enumerate, in shuffled order
    // (different float summation order → tolerance, not bit identity).
    // n_pub for a turn deal is 49 (52 − 3 board cards); verify against
    // the solver's turns().len() and adjust if the fixture differs.
    let mut e = tiny_flop(ChanceMode::Enumerate);
    let mut m = tiny_flop(ChanceMode::MultiSample { seed: 3, samples: 49 });
    e.run(60);
    m.run(60);
    let ee = e.exploitability_bb().exploitability;
    let em = m.exploitability_bb().exploitability;
    assert!((ee - em).abs() / ee.max(1e-12) < 0.05, "enum {ee} vs full-k {em}");
}

#[test]
fn multisample_expectation_matches_enumeration_across_seeds() {
    // Multi-seed expectation check: the k=4 estimator's game value
    // averaged over seeds approaches the enumerated value.
    let mut e = tiny_flop(ChanceMode::Enumerate);
    e.run(40);
    let ge = e.game_value_p0();
    let seeds = [1u64, 2, 3, 4, 5, 6, 7, 8];
    let mut acc = 0.0;
    for &s in &seeds {
        let mut m = tiny_flop(ChanceMode::MultiSample { seed: s, samples: 4 });
        m.run(40);
        acc += m.game_value_p0();
    }
    let gm = acc / seeds.len() as f64;
    assert!((ge - gm).abs() < 0.15, "enum {ge} vs mean-of-seeds {gm}");
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
`chance_sample` becomes a partial-enumeration loop over k DISTINCT cards:

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
    // (n_pub, legal) lookup stays exactly as today.
    let k = (k as usize).min(n_pub).max(1);
    // Partial Fisher–Yates over 0..n_pub on a stack array (n_pub ≤ 49):
    // the j-th draw calls next_index(n_pub - j), so the k=1 path performs
    // exactly the single next_index(n_pub) call the current code makes —
    // bit-identical RNG stream and arithmetic.
    let mut order = [0usize; 52];
    for (i, o) in order.iter_mut().take(n_pub).enumerate() { *o = i; }
    let mut ev = vec![0.0; N];
    let scale = n_pub as f64 / legal;
    for j in 0..k {
        let r = self.rng.next_index(n_pub - j);
        order.swap(j, j + r);
        let idx = order[j];
        // ---- existing single-sample body for `idx`, verbatim:
        // resolve the card for this deal street, zero blocked reaches,
        // recurse via traverse (updates below happen per visited subtree,
        // as Enumerate already does), and add `scale * v[c]` into ev[c]
        // for unblocked combos ----
    }
    if k > 1 {
        let inv = 1.0 / k as f64;
        for v in ev.iter_mut() { *v *= inv; }
    }
    ev
}
```

The `k == 1` path must not multiply (no `* 1.0` reordering) and must not
change the RNG call pattern, so the Sample stream and float ops stay
bit-identical (guarded by the k=1 test and `test_perf_baseline`).
Iteration/discount accounting is NOT touched: one traversal remains one
CFR iteration for any k. Apply the same transformation to the sampling
site in `turn_river.rs` (its `Sample` samples the river deal; same
partial-Fisher–Yates pattern, same k=1 discipline). Fix all `match` sites
the compiler flags — exhaustive matches on `ChanceMode` exist in both
files and in `src/bin/` CLIs; map `MultiSample` alongside `Sample`
everywhere.

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
BenchCase { name: "flop_srp100_AhKd7s_k24_ms4", config: SRP_CFG,
            build: |s| flop_case_mode([c("Ah"), c("Kd"), c("7s")], 24,
                    ChanceMode::MultiSample { seed: s, samples: 4 }) },
BenchCase { name: "bp3_ms4",  config: BP_CFG,
            build: |s| blueprint_case_mode(ChanceMode::MultiSample { seed: s, samples: 4 }) },
BenchCase { name: "bp3_ms16", config: BP_CFG,
            build: |s| blueprint_case_mode(ChanceMode::MultiSample { seed: s, samples: 16 }) },
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

- [ ] **Step 7: Measure MultiSample slopes, 3 seeds each (~6 h)**

All runs use Task 4A recovery snapshots. A resumed run must restore the raw
SplitMix64 stream so its final result stays bit-identical to uninterrupted
execution.

```bash
cd /home/kazumasa/projects/gto
B=docs/reviews/2026-07-19-p0a-audit/baselines
GC=$(git rev-parse HEAD)
DTY=$([ -z "$(git status --porcelain)" ] && echo 0 || echo 1)
META="--label multisample --git-commit $GC --dirty $DTY"
for S in 42 1042 9042; do
  cargo run --release -p gto-hu --bin solver-bench -- --case bp3_ms4  --iterations 400 --points 8 --seed $S $META \
    --checkpoint-dir ../_data/gto/checkpoints/p0a/bp3_ms4_s$S --checkpoint-every-minutes 30 --resume auto \
    --out $B/bp3_ms4_s$S.json
  cargo run --release -p gto-hu --bin solver-bench -- --case bp3_ms16 --iterations 100 --points 6 --seed $S $META \
    --checkpoint-dir ../_data/gto/checkpoints/p0a/bp3_ms16_s$S --checkpoint-every-minutes 30 --resume auto \
    --out $B/bp3_ms16_s$S.json
done
cd /home/kazumasa/projects
uv run --no-sync python -m gto.bench gto/docs/reviews/2026-07-19-p0a-audit/baselines -o gto/docs/reviews/2026-07-19-p0a-audit/baseline-report.md
cd gto && git add docs/reviews/2026-07-19-p0a-audit && git commit -m "bench(gto): MultiSample k=4/16 blueprint slopes, 3 seeds (G-A2 evidence)"
```

**Hypothesis under test, NOT an acceptance condition (P1-3):** slope
steepens from `bp3_sample` (≈ −0.5) toward `bp3_enum` as k grows. Whatever
the data shows goes into the report; G-A2 is judged by the seed-interval
rule on the winning mode, and the mode choice for P0b weighs
wall-clock-to-quality, not slope alone.

---

### Task 8: Blueprint memory model (G-A3 projection evidence)

Review P0-2 governs this task: `BlueprintSolver::table_bytes()` sums only
the **currently allocated lazy slabs** — near zero right after construction
— so it must never be compared against dense capacity at construction time,
and a blanket `bytes / 2` is valid only for f64 numeric slabs, never for
total resident memory. The model therefore distinguishes three quantities:
**capacity** (what a fully-visited run allocates in numeric slabs),
**allocated** (`table_bytes()`, grows lazily toward capacity), and **RSS**
(process total: capacity + trees, bucket maps, equity/all-in tables,
allocator overhead — captured as a measured overhead factor, not modeled
component by component).

**Files:**
- Modify: `gto/crates/gto-hu/src/bench.rs`
- Modify: `gto/crates/gto-hu/src/solver/blueprint.rs` (expose `config_for`)
- Modify: `gto/crates/gto-hu/src/bin/solver_bench.rs` (`--memory-model`)
- Test: `gto/crates/gto-hu/tests/test_bench_memory.rs`

**Interfaces:**
- Consumes: `dense_table_bytes_abstracted(tree, abs)` (`flop.rs:197`),
  `BlueprintSolver::table_bytes()` (`blueprint.rs:229` — ALLOCATED, lazy),
  `BlueprintSolver::run`, tree builders.
- Produces:
  - `pub fn config_for(pot_type: PotType) -> FlopTreeConfig` — moved from
    `src/bin/solve_blueprint.rs` into `solver/blueprint.rs` as the single
    source of truth (the CLI re-imports it)
  - `pub fn blueprint_dense_capacity_bytes(m: usize, stack_bb: u32, abs: Abstraction) -> usize`
    — CAPACITY: per preflop betting leaf, `dense_table_bytes_abstracted`
    of that leaf's `config_for` flop tree × m, summed, plus the preflop
    layer's own numeric tables (read `BlueprintSolver::new` and count
    exactly the slabs it can allocate)
  - `pub fn f32_slab_projection(bytes: usize) -> usize` — halves ONLY the
    numeric-slab bytes passed in; callers must not feed it RSS or
    non-slab overhead
  - `pub fn build_blueprint_for_test(stack_bb: u32, abs: Abstraction) -> BlueprintSolver`
    — tiny 3-flop blueprint in **enumerate** mode (reuses the Task-1
    builder internals with stack parameterized)

- [ ] **Step 1: Write the failing tests**

`gto/crates/gto-hu/tests/test_bench_memory.rs`:

```rust
//! Capacity model vs the real allocator (review P0-2): table_bytes() is
//! LAZY — the model is validated by growing a tiny enumerate-mode run to
//! full allocation, plus real-RSS anchors in the --memory-model step.

use gto_hu::bench::{
    blueprint_dense_capacity_bytes, build_blueprint_for_test, f32_slab_projection,
};
use gto_hu::solver::Abstraction;

#[test]
fn allocated_bytes_start_near_zero_and_grow_to_capacity() {
    let abs = Abstraction { buckets_river: 8, buckets_turn: 4 };
    let mut bp = build_blueprint_for_test(20, abs);
    let at_construction = bp.table_bytes();
    let capacity = blueprint_dense_capacity_bytes(3, 20, abs);
    assert!(
        at_construction < capacity / 10,
        "lazy tables must start far below capacity: {at_construction} vs {capacity}"
    );
    // Enumerate mode visits every betting line and chance context, so a
    // few iterations allocate every slab on this tiny configuration.
    bp.run(3);
    let after = bp.table_bytes();
    assert!(after > at_construction, "no slab growth after training");
    assert!(after <= capacity, "allocated {after} exceeds capacity {capacity}");
    let frac = after as f64 / capacity as f64;
    assert!(frac > 0.9, "expected near-full allocation, got {frac:.3}");
    // If full enumeration provably cannot reach some slabs (document
    // which), lower the bound to the reachable fraction and say why in
    // this comment — reached-capacity is the honest comparison.
}

#[test]
fn f32_projection_halves_slab_bytes_only() {
    assert_eq!(f32_slab_projection(1000), 500);
}
```

- [ ] **Step 2: Run to verify failure; implement; re-run**

```bash
cargo test -p gto-hu --test test_bench_memory 2>&1 | tail -4
```

Implement by mirroring `BlueprintSolver::new`'s allocation structure:
build the preflop tree at `stack_bb`, take its betting leaves, map each
leaf's `PotType` through the now-shared `config_for`, build each flop tree
once, and sum `dense_table_bytes_abstracted(&tree, abs) * m` plus the
preflop layer's numeric tables. Then re-run: both tests pass, and the full
`cargo test -p gto-hu` suite stays green.

- [ ] **Step 3: Print the G-A3 projection table with RSS anchors**

Add a `--memory-model` flag to `solver-bench` that prints, for stack
100 bb and `Abstraction{24,16}`, rows M ∈ {3, 10, 25, 50} with columns:

1. capacity f64 (GB) — `blueprint_dense_capacity_bytes`
2. f32-slab projection (GB) — `f32_slab_projection` of column 1
3. projected peak RSS (GB) — column 2 × the **measured overhead factor**,
   printed with its provenance: WP2's real M=3 run measured 23.95 GB dense
   capacity and 27.8 GB peak RSS → overhead ≈ 1.16. The flag also prints
   the model-vs-WP2 cross-check (M=3 capacity within ~2% of 23.95 GB).

```bash
cargo run --release -p gto-hu --bin solver-bench -- --memory-model
```

The **G-A3 projection verdict** reads from the M=25 row: projected peak
RSS ≤ 48 GB. Board bucketing is NOT in the model (its reduction factor is
unknown before P0b): if M=25 passes without it, G-A3 passes with margin;
if not, the report states the required bucketing reduction factor and the
verdict is conditional on P0b achieving it — never silently assumed.

- [ ] **Step 4: Commit**

```bash
git add crates/gto-hu/src/bench.rs crates/gto-hu/src/bin/solver_bench.rs \
        crates/gto-hu/src/solver/blueprint.rs crates/gto-hu/tests/test_bench_memory.rs
git commit -m "feat(gto-hu): blueprint capacity model + f32 slab projection (G-A3 evidence)"
```

G-A3 contract note for the report (renegotiated spec §5.0): P0a ships this
**validated projection**; the engine's current M ≤ 8 cap (`blueprint.rs:119`,
u8 masks / 2^M zsum) means the model deliberately extrapolates past the
implemented range, and the **first P0b M=25 real run (peak RSS ≤ 48 GB) is
the blocking P0b entry gate** that confirms it.

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

Each individual 100-iteration process is short enough that durable snapshots
are optional here. Do not reuse a checkpoint directory across thread counts.

```bash
cd /home/kazumasa/projects/gto
T=docs/reviews/2026-07-19-p0a-audit/threads
GC=$(git rev-parse HEAD)
DTY=$([ -z "$(git status --porcelain)" ] && echo 0 || echo 1)
for n in 1 2 4 8 16; do
  cargo run --release -p gto-hu --bin solver-bench -- --case bp3_sample --iterations 100 --points 2 --threads $n \
    --label "threads-t$n" --git-commit $GC --dirty $DTY --out $T/bp3_t$n.json
done
cd /home/kazumasa/projects && uv run --no-sync python -m gto.bench gto/docs/reviews/2026-07-19-p0a-audit/threads -o gto/docs/reviews/2026-07-19-p0a-audit/thread-report.md
```
(Distinct `--label` values keep the thread runs on separate report rows —
`aggregate_seeds` groups by (case, label).)
Expected: iter/s from `solve_s` at the final checkpoint; WP2 anchor:
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
2.2 Flop quality/time **Pareto curve** (paste flop-report.md): per
    candidate threshold {0.5, 0.3, 0.15, 0.05} bb — median artifact time,
    censored cases, and implied Tier-1 grid GPU-hours. This section feeds
    the user's threshold selection; no G-A1 verdict is written here.
2.3 Variance reduction: sample / ms4 / ms16 / enumerate — windowed slope
    median [min, max] per mode (3 seeds for stochastic modes) + the
    wall-clock-to-quality winner at 0.3 bb and 0.15 bb
2.4 Thread scaling table; profiling findings (or the WSL2 caveat)
2.5 Memory model table (capacity × precision × RSS-overhead), WP2
    23.95 GB dense / 27.8 GB RSS cross-checks
2.6 Recovery snapshots: size, write/read time, peak-RSS delta, maximum lost
    work, resume count, corruption fallback, and bit-identity result

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
| G-A1 | ≤ 12 min median artifact time at the USER-SELECTED threshold (censored median = automatic no-go at that threshold) | … | go / no-go / re-scope |
| G-A2 | whole ≥3-seed slope interval ≤ −0.85 on the pre-registered window; wall-clock-to-quality reported alongside | … | … |
| G-A3 | validated projection: modeled M=25 f32(+stated bucketing factor if needed) ≤ 48 GB | … | go / no-go — real-run confirmation is the P0b ENTRY gate |

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

Present in this order: **first** the §2.2 Pareto curve for the user to
select the per-flop threshold (P1-1 — the G-A1 verdict cannot be written
before this choice), **then** the completed gate-verdict table and
recommendation for the go/no-go decision. P0b mass generation and app
phases P2+ stay blocked until the user accepts the verdicts (spec §5.0),
and the first P0b M=25 real run remains the blocking G-A3 confirmation.

---

## Self-review notes (kept for the executor)

- Spec §5.0 coverage: harness + snapshots (Tasks 1–4, 4A) → item 1;
  profiling + thread scaling (Task 9) → item 2; algorithm review (Task 9)
  → item 3; G-A1 (Task 6 evidence + Task 9 user-selected verdict), G-A2
  (Tasks 5+7, seed-interval rule), G-A3 (Task 8 validated projection;
  real-run confirmation deferred to the P0b entry gate) → item 4; report
  (Task 9) → item 5.
- Review-finding map (docs/reviews/2026-07-19-p0a-plan-review.md): P0-1 →
  renegotiated spec + Task 8 contract note; P0-2 → Task 8 capacity/
  allocated/RSS model; P1-1 → Task 6 + G-A1 wording; P1-2 → Task 2 timing
  split + Task 3 build_s + Python `artifact_time_to`; P1-3 → Task 7
  partial-enumeration semantics + differential/expectation tests; P1-4 →
  3-seed loops (Tasks 5/7) + `fit_window` + interval rule; P1-5 → Task 4A;
  P2-1 → Task 4 `time_to` tests derived from the implementation's own
  definition; P2-2 → RunRecord metadata + CLI flags; P2-3 → Task 1 Step 1
  branch assertion.
- Solver-numerics changes are Task 7 (MultiSample) and Task 4A (state
  save/restore, behavior-neutral by contract); both are fenced by
  `test_perf_baseline` checksums plus their own bit-identity tests
  (k=1 identity; save/reload/resume identity).
- API names copied from source on 2026-07-19 (`flop.rs`, `blueprint.rs`,
  `turn_river.rs`, `vector.rs`, `test_perf_baseline.rs`). Where a helper's
  existence was not verified (`TurnTreeConfig::srp()`, blueprint preflop
  range construction, `FlopSolver::average_strategy` ctx arity), the task
  says "verify against the actual code" — do that before writing.
- Long-running steps (5.1–5.3 ≈ 5 h, 6.1 ≈ 4–6 h, 7.7 ≈ 6 h, 9.1 ≈ 1 h,
  plus 4A fault-injection) are sequential solo runs; everything else is
  minutes. Every >15-minute run carries Task 4A snapshots.
