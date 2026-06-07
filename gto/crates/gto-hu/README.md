# gto-hu — Abstract HU NLHE Equilibrium Solver

**This is an abstract HU NLHE equilibrium solver, not an unabstracted full
GTO solver.** Fixed action abstraction; exploitability (bb/hand) is always
reported alongside strategies.

Current scope (Phase 3): exact-combo river solver + turn+river solver with
the river dealt as a public chance node (exact enumeration or seeded public
chance sampling).

- Game: HU NLHE cash, configurable pot/stack. SRP turn action set
  (check / bet 50% / bet 100%; vs bet: fold / call / raise 3x-or-jam) and
  SRP river action set (check / bet 75% / bet 150% / all-in; vs bet:
  fold / call / raise-jam). All-in on the turn runs out the river as
  chance straight to showdown.
- Solver: CFR+ (default) or DCFR, per-combo vector traversal,
  blocker-exact showdowns; chance weight 1/44 per deal (sampling is
  importance-corrected and unbiased). Exploitability is always computed
  by exact enumeration.
- Validation: Kuhn & Leduc on the same engine family, exact best
  response, scalar-vs-vector differential tests on both the river and
  turn+river games.

## Usage

```bash
cargo run --release -p gto-hu --bin solve-hu-river -- \
  --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000

cargo run --release -p gto-hu --bin solve-hu-turn-river -- \
  --board AhKd7s2c --pot 20 --stack 90 --iterations 10000
```

Outputs land under `~/projects/_data/gto/hu/`: aggregate strategy tables,
exploitability in bb/hand, `strategy*.csv` / `summary.json`.

## Roadmap

Flop trees (two chance streets) → preflop with limp → full blueprint.
See `gto/docs/superpowers/specs/2026-06-06-hu-abstract-solver-design.md`.
