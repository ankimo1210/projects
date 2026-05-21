"""Real-time 3D demo of a Plummer sphere relaxing under self-gravity."""
from __future__ import annotations

import argparse

from nbody import Simulation, plummer_sphere
from viz import run_simulation


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-n", "--n-particles", type=int, default=8192)
    p.add_argument("--dt", type=float, default=1e-3)
    p.add_argument("--eps", type=float, default=2e-2)
    p.add_argument("--steps-per-frame", type=int, default=4)
    p.add_argument("--point-size", type=float, default=3.0)
    p.add_argument("--no-energy", action="store_true",
                   help="Skip O(N^2) energy diagnostic (faster for large N).")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    print(f"Generating Plummer sphere: N={args.n_particles}")
    pos, vel, mass = plummer_sphere(
        n=args.n_particles, total_mass=1.0, scale_radius=1.0, seed=args.seed
    )
    sim = Simulation.from_host(pos, vel, mass, dt=args.dt, eps=args.eps)
    print(f"Initial energy: {sim.total_energy():.6e}")
    print("Launching viewer (close window or press q to exit).")
    run_simulation(
        sim,
        steps_per_frame=args.steps_per_frame,
        point_size=args.point_size,
        show_energy=(not args.no_energy and args.n_particles <= 8192),
        title=f"nbody-gpu  N={args.n_particles}",
    )


if __name__ == "__main__":
    main()
