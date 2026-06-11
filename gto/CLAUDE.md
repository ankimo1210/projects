# gto — Claude Code Guide

## Purpose

GTO (Game Theory Optimal) Texas Hold'em analysis app. Combines a Rust CFR
solver (CPU + GPU/NVRTC), a FastAPI backend, a Next.js frontend, and a
Parquet-backed solution library. Personal project, eventually commercial.

Respond to the user in Japanese by default; code and identifiers in English.

## Architecture

| Layer | Path | Role |
|---|---|---|
| Solver core | `crates/gto-core/` | CFR/DCFR, hand evaluator, `PokerVariant` trait/`Nlhe` (variant seam) (Rust, CPU). (`multistreet.rs` removed in M1a.) |
| GPU solver | `crates/gto-cuda/` | NVRTC JIT kernels, batch CFR on RTX 5080 (sm_120). CUDA Driver API via `ctypes`. |
| Python bindings | `crates/gto-py/` | pyo3 wrapper: `solve_hu_river` / `solve_hu_turn_river` (ranges + bet sizes + pot type + `RakeModel` + equity/per-combo-EV/NashConv outputs), `solve_spot` (gto-cuda preview), `equity` |
| HU solver | `crates/gto-hu/` | Abstract HU NLHE equilibrium solver: vector CFR+, rake + general-sum exploitability (NashConv), Kuhn/Leduc validation, exact best response. CLIs: `solve-hu-river`, `solve-hu-turn-river`, `solve-hu-flop`, `solve-hu-preflop`, `solve-hu-blueprint` |
| Backend API | `src/gto/api/` | FastAPI app + routers (`solve` = GameSpec `POST /api/solve` + capabilities, `equity`, `trainer`, `solver`, `library`, `simulation`, `review`, `hu` [deprecated → `/api/solve`]) |
| Solution store | `src/gto/library/` | Batch precompute, Parquet I/O, range builder, flop canonical-form |
| Trainer | `src/gto/trainer/` | Preflop GTO frequency tables (hardcoded approximation, not solved) |
| Hand review | `src/gto/review/` | PokerStars hand-history parser + preflop GTO deviation flags |
| Web UI | `web/` | Next.js 16 / React 19 / Tailwind v4 (pages: `/neon`, `/library`, `/report`, `/solver`, `/simulation`, `/review`, `/hu`) |

Data flow: see `ARCHITECTURE.md`. Roadmap and known limitations: `PROGRESS.md`.

## Run & Verify

Python deps live in the workspace `.venv` at `~/projects/`. Rust crates
build in place to `gto/target/`.

```bash
# One-time install (from workspace root)
cd ~/projects && make install                          # = uv sync --all-packages

# Build Rust extensions (after Rust changes, or whenever a uv sync wiped them)
cd ~/projects/gto && source ~/.cargo/env
uv run --no-sync maturin develop --uv --manifest-path crates/gto-py/Cargo.toml   --release
uv run --no-sync maturin develop --uv --manifest-path crates/gto-cuda/Cargo.toml --release

# Backend (port 8000)
uv run --no-sync uvicorn gto.api.main:app --host 0.0.0.0 --port 8000

# Frontend (port 3000)
cd web && pnpm install && pnpm exec next dev

# Tests
uv run --no-sync pytest gto/tests
cargo test --manifest-path gto/Cargo.toml
```

## Conventions

- **Solution store**: canonical path is `~/projects/_data/gto/solutions/`
  (resolved as `Path(__file__).parents[4] / "_data" / "gto" / "solutions"`
  in `src/gto/library/store.py`). Never write Parquet under `gto/`.
- **Card encoding**: `card = rank * 4 + suit` (rank: 0=2 … 12=A, suit: c d h s).
  Combo index is `lo*51 - lo*(lo-1)/2 + hi - lo - 1`. 1326 total. See
  `ARCHITECTURE.md` for the math.
- **CFR algorithm**: Discounted CFR (DCFR α=1.5, β=0). Bet sizes per street
  vary (Flop 50% / Turn 75% / River 75% in `gto-core`; 33/75/100 in `gto-cuda`).
- **Single-letter math variables (N, K, S, V, ...)** are allowed in solver
  code (ruff N806 suppressed for `gto/src/gto/solver/`).
- **PyTorch** comes from the workspace's `pytorch-cu128` index (declared at
  workspace root, not in `gto/pyproject.toml`).

## Gotchas

- **`gto-cuda` is single-street only.** It solves Flop with Call→Showdown,
  ignoring Turn/River — qualitatively wrong flop incentives; it is the
  "instant-preview" tier only (`equilibrium_claim=false`). For correct
  postflop equilibria use **gto-hu** via `POST /api/solve` (river / turn+river
  exact; flop is M1b). River-only gto-cuda solves are still correct.
  (The old `gto-core::multistreet` approximation tier was removed in M1a.)
- **Preflop is hardcoded**, not solved by CFR. The frequencies in
  `src/gto/trainer/preflop_data.py` are an approximation table.
- **`2c` phantom card bug** — fixed (Phase 1 evaluator rewrite, see
  `eval::showdown_strengths`). The library was regenerated with the fixed
  evaluator on 2026-06-07, then **again on 2026-06-11** with the core-logic
  review fixes (gto-cuda B1/B2/B3 — per-spot pot, blocked-combo showdown,
  node-pot showdown). Both prior Parquet snapshots are kept:
  `_data/gto/solutions_backup_20260611/` (pre-B2/B3) and
  `_data/gto/solutions_legacy_backup_20260607/` (pre-evaluator-fix).
- **`uv sync` (or `uv run` without `--no-sync`) removes the maturin-built
  `gto_py` / `gto_cuda` modules** from the workspace venv — they are not in
  the lockfile. Rebuild with `maturin develop --uv` (plain `maturin develop`
  fails: no pip in a uv venv).
- **CUDA 12.8 + sm_120**: hardware/driver assumption is RTX 5080 (Blackwell).
  Older GPUs likely fail at JIT compile.
- **Do not delete** `_data/gto/solutions/` Parquet without explicit user
  request — regenerating the full 19,305-spot library takes ~53 minutes on GPU
  (`batch_solve_rust` hybrid path: BTN/CO/SB×{50,100,200} + HJ/UTG×{100},
  iters=300, batch-size=32). Back up first (`mv solutions solutions_backup_<date>`).
- **`gto/web/node_modules/`** is large; never grep into it.
- **gto-hu is the only solver allowed to claim equilibrium output**, and
  only with its exploitability number attached. gto-core/gto-cuda remain
  single-street approximations (river-only correctness).

## Algorithm Implementation Protocol

For any non-trivial algorithm (CFR, search, ML inference, GPU kernels, etc.):

1. **Reference first** — find a known-correct version (paper, OSS, textbook) and match
   its structure before introducing optimizations.
2. **Small known cases** — test against hand-computable inputs (e.g., Kuhn poker for CFR)
   before scaling to production size.
3. **Property tests** — verify invariants that must hold (zero-sum, monotonic convergence,
   probability sums = 1).
4. **Differential testing** — if multiple implementations exist (CPU, GPU, reference), they
   must agree on shared inputs. Catch divergence early; don't stack features on an
   unvalidated base.
5. **Optimization comes last** — only after correctness is proven. Premature GPU/SIMD/
   parallelization hides bugs.
