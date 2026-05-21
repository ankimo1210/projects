# nbody-gpu

GPU-accelerated N-body simulation with real-time 3D visualization.

## Stack

- Python 3.12+ / uv
- CuPy + RawKernel (custom CUDA C kernels)
- VisPy + PyQt6 (real-time 3D viz)
- WSL2 + RTX 5080 (Blackwell, sm_120) + WSLg

## Layout

```
src/nbody/
  forces.py            # CuPy RawKernel: tile-based O(N^2) (production)
  forces_bh.py         # Barnes-Hut traversal on LBVH (works, but slower than O(N^2) on this GPU)
  integrator.py        # leapfrog (kick-drift-kick)
  initial_conditions.py# Plummer sphere, two-body circular
  simulation.py        # Simulation class (holds device state)
  octree/
    morton.py          # 30-bit Morton codes + Z-order sort
    lbvh.py            # Karras 2012 parallel radix tree
    multipole.py       # bottom-up mass / COM / BBox propagation
src/viz/
  renderer.py          # VisPy SceneCanvas + Markers
  app.py               # sim <-> render loop
scripts/
  check_env.py         # CUDA / CuPy / VisPy sanity
  run_demo.py          # interactive demo entry
  bench.py             # direct vs BH benchmark
tests/                 # 21 tests across Kepler, energy, Morton, LBVH, multipole, BH
```

## Performance notes (RTX 5080, May 2026)

| N       | direct O(N²) | BH (θ=0.5) | winner |
|---------|--------------|------------|--------|
| 4096    | 0.08 ms      | 0.74 ms    | direct |
| 65536   | 3.4 ms       | 24 ms      | direct |
| 262144  | (slow)       | 387 ms     | BH (direct impractical) |
| 1048576 | (impractical)| 49 s       | BH (only choice) |

The naive BH (independent per-particle stack DFS) loses to the tile-based
O(N²) kernel under ~10⁵ particles on this GPU because (a) tree rebuild every
step, (b) warp divergence in traversal, (c) uncoalesced node-com loads.
Crossover only happens at very large N. Future optimisations (warp-coop
traversal, tree reuse across steps) would shift this.

## Run

```bash
uv sync
uv run python scripts/check_env.py
uv run python scripts/run_demo.py
uv run pytest
```

## Conventions

- GPU state: device arrays held in `Simulation` (positions, velocities, masses).
- Units: G=1, dimensionless. Plummer scale a=1, total mass M=1.
- Softening: ε added in r² to avoid singularity.
- Integrator: leapfrog (symplectic, energy-stable for circular orbits).
- Default production kernel: `forces.compute_acceleration` (direct). BH path
  (`forces_bh.compute_acceleration_bh`) is correct but not yet competitive.
