# gto-hu — Abstract HU NLHE Equilibrium Solver

**This is an abstract HU NLHE equilibrium solver, not an unabstracted full
GTO solver.** Fixed action abstraction; exploitability (bb/hand) is always
reported alongside strategies.

Current scope (Phase 2): exact-combo river solver.

- Game: HU NLHE cash, configurable pot/stack, SRP river action set
  (check / bet 75% / bet 150% / all-in; vs bet: fold / call / raise-jam)
- Solver: CFR+ (default) or DCFR, per-combo vector traversal,
  blocker-exact showdowns
- Validation: Kuhn & Leduc on the same engine family, exact best response,
  scalar-vs-vector differential tests

## Usage

```bash
cargo run --release -p gto-hu --bin solve-hu-river -- \
  --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000
```

Outputs an aggregate strategy table, exploitability in bb/hand, and
`strategy.csv` / `summary.json` under `~/projects/_data/gto/hu/`.

## Roadmap

Turn+river (public chance sampling) → flop trees → preflop with limp →
full blueprint. See `gto/docs/superpowers/specs/2026-06-06-hu-abstract-solver-design.md`.
