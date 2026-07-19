# P0a Algorithm Audit Plan Review

Date: 2026-07-19  
Reviewed plan: `docs/superpowers/plans/2026-07-19-p0a-algorithm-audit.md`  
Related spec: `docs/superpowers/specs/2026-07-19-gtowizard-parity-ios-design.md`

## Verdict

**HOLD — revise before execution.**

The plan has a strong TDD structure, fixed reference cases, deterministic
seeds, bit-identity guards, sequential scheduling for memory-heavy runs, and
an explicit go/no-go report. However, the current plan cannot produce valid
verdicts for all three P0a gates. The blockers below must be resolved before
the long benchmark runs begin.

## Findings

### P0-1: G-A3 is projected, while the approved spec requires a real M=25 run

The approved spec requires an M=25 blueprint with f32 and board bucketing to
fit within 48 GB **on a real run, not an estimate**. Task 8 instead computes a
projection and proposes a `conditional-go`, deferring confirmation to P0b.
That does not clear the P0a hard gate.

The current `BlueprintSolver` also supports only `1..=8` flops. Its `u8`
block mask and `zsum` indexed by all `2^M` masks are not directly suitable for
M=25. A real M=25 run therefore requires a data-structure change in addition
to f32 tables and board bucketing.

Required decision:

1. Move the minimum M=25-enabling implementation and real RSS measurement
   into P0a; or
2. explicitly renegotiate the approved spec so G-A3 is a projection gate,
   with a separate blocking real-run gate in P0b.

Do not report G-A3 as `go` while this decision remains unresolved.

### P0-2: Task 8's allocator test compares incompatible quantities

`BlueprintSolver::table_bytes()` sums only currently allocated lazy
regret/strategy slabs in its flop subgames. Immediately after construction,
those slabs are not populated, so the proposed `build_blueprint_for_test()`
comparison can return zero rather than the dense capacity modeled by
`dense_table_bytes_abstracted()`.

The proposed model also omits or conflates memory that contributes to process
RSS: preflop tables, all-in equity matrices, bucket maps, trees and indices,
RNG/discount metadata, and allocator overhead. A blanket `bytes / 2` f32
projection is valid only for f64 numeric slabs, not for total resident memory.

Required correction:

- define component-level `allocated_bytes` and `dense_capacity_bytes`;
- project f32 only for the slabs whose element type changes;
- validate the model against both component accounting and peak RSS;
- use total peak RSS, not table bytes alone, for G-A3.

### P1-1: G-A1 derives the quality gate from the time budget

Task 6 proposes finding the exploitability target reachable within 12 minutes
and then treating that value as the per-file quality gate. This reverses the
gate: any solver can satisfy the time target if the quality threshold is
relaxed after the measurement.

The planned 3,000-iteration runs are also anchored around roughly 1.17 bb,
while the report only asks for time-to 0.5, 0.3, and 0.15 bb. If none of those
targets is reached, the current report cannot decide G-A1.

Required correction:

- pre-register the per-flop quality threshold independently of runtime;
- run each case until the threshold or a 12-minute timeout;
- treat timeout as censored/no-go data, not as a new quality threshold;
- include at least SRP and 3bet trees because both are in the Tier-1 grid;
- use a representative range/tree set when sizing total generation time.

If product quality cannot supply a threshold yet, report the measured
quality/time Pareto curve and ask the user to choose it before issuing G-A1.

### P1-2: The benchmark does not record the required wall-clock time

The spec asks for wall-clock to target exploitability. `elapsed_s` in the plan
counts solve time only and excludes solver construction and every exact
best-response evaluation. This is useful for iteration throughput, but it is
not the production time needed to build and validate one artifact.

Record these separately:

- `build_s`;
- `solve_s`;
- `checkpoint_br_s`;
- `final_br_s`;
- `total_active_wall_s`.

Use `build_s + solve_s + final_br_s` for G-A1. Keep checkpoint BR time separate
so measurement frequency does not distort solver throughput.

### P1-3: MultiSample does not yet have a sound update definition

The proposed implementation calls the existing recursive `traverse()` k
times inside one chance visit and averages only the returned EV. `traverse()`
mutates regrets, strategy sums, last-visit metadata, and discount state on
each call. Consequently, the k calls are not k estimators evaluated under one
frozen strategy, and they are not obviously k normal CFR iterations either.

Before implementation, choose and document one meaning:

- accumulate k sample deltas against a frozen strategy and apply one update;
  or
- define k micro-iterations and advance all iteration/discount accounting
  consistently.

In addition to `k=1` bit identity and deterministic replay, add a tiny-game
differential test against enumeration and a multi-seed expectation test. The
assumption that slope improves monotonically with k must remain a hypothesis,
not an expected pass condition.

### P1-4: G-A2 lacks a robust statistical protocol

One fixed seed is sufficient for reproducibility but not for a sampling-noise
claim. The sample, k=4, k=16, and enumerate runs also cover different and
mostly early iteration ranges, so fitting all geometric checkpoints can mix
transient and asymptotic behavior.

Required correction:

- pre-register the fit window (normally the latter convergence region);
- run at least three independent seeds for stochastic modes;
- report median slope and a bootstrap or seed-level interval;
- compare wall-clock-to-quality as well as slope-per-iteration;
- do not pass G-A2 when the confidence interval crosses -0.85.

### P1-5: Long solver runs need durable checkpoint/resume

Current solver CLIs export final reports but cannot restore CFR training
state. A process crash, OOM, WSL restart, or machine reboot can therefore lose
hours of work. The analytical exploitability checkpoints in the benchmark
plan are not recovery snapshots.

Add a blocking recovery-snapshot task before any run expected to exceed 15
minutes. A valid snapshot must preserve iteration, regret and average-strategy
tables, sampled-mode RNG state, lazy-allocation layout, last-discount
iteration arrays, discount prefixes, and blueprint preflop/subgame state.

Required properties:

- versioned binary format with solver/config/build identity;
- streaming write without duplicating the full table in RAM;
- write-to-temp, `fsync`, atomic rename, and two retained generations;
- strict rejection of truncated, corrupt, mismatched, or incompatible files;
- uninterrupted vs save/reload/resume runs are bit-identical;
- snapshots live under `_data/gto/checkpoints/` and are never committed;
- default maximum lost compute is 30 minutes, with measured snapshot overhead;
- benchmark JSON records resume count and active timing segments.

### P2-1: `time_to()` test and implementation disagree

The synthetic test expects exactly 1.0 second for an inverse-power curve.
The proposed implementation linearly interpolates elapsed time against
`log(expl)`, which gives approximately 1.057542 seconds for the same points.
Choose either log-time/log-exploit interpolation or the current
time/log-exploit interpolation, then align the test and documentation.

### P2-2: Reproducibility metadata is too thin

`case`, a free-form label, thread count, and checkpoints do not fully capture
the experiment. Add a schema version, full git commit, dirty-tree flag,
canonical case configuration, variant, chance mode and seed, abstraction,
compiler/build profile, CPU/kernel identity, command line, and timing segment
metadata. Baseline JSON should be self-describing before it is committed.

### P2-3: Branch creation step is stale

The plan is already committed on `claude/gto-p0a-audit`. Re-running
`git checkout -b claude/gto-p0a-audit` will fail. Replace it with a branch and
clean-worktree assertion.

## Required revision order

1. Resolve the G-A3 contract and M=25 ownership between P0a and P0b.
2. Correct the G-A1 quality gate and wall-clock measurement definition.
3. Add durable checkpoint/resume before all long runs.
4. Specify MultiSample update semantics and differential tests.
5. Define the G-A2 seed count, fit window, and uncertainty rule.
6. Repair the memory model and `time_to()` test.
7. Run short harness tests first; only then start multi-hour measurements.

## Positive aspects to retain

- test-first task structure;
- fixed named reference cases and deterministic seeds;
- existing-behavior bit-identity guards;
- sequential execution of memory-heavy workloads;
- committed machine-readable baselines plus a human-readable audit report;
- explicit user decision before P0b mass generation and app phases P2+.
