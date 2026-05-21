"""Direct O(N^2) vs Barnes-Hut benchmark."""

from __future__ import annotations

import argparse
import time

import cupy as cp

from nbody.forces import compute_acceleration
from nbody.forces_bh import compute_acceleration_bh
from nbody.initial_conditions import plummer_sphere


def _time_call(fn, n_warmup=2, n_iter=5):
    for _ in range(n_warmup):
        fn()
    cp.cuda.runtime.deviceSynchronize()
    t0 = time.perf_counter()
    for _ in range(n_iter):
        fn()
    cp.cuda.runtime.deviceSynchronize()
    dt = (time.perf_counter() - t0) / n_iter
    return dt


def bench(n: int, theta: float = 0.5, eps: float = 2e-2, run_direct: bool = True) -> None:
    pos, _, mass = plummer_sphere(n=n, seed=0)
    pos_d = cp.asarray(pos)
    mass_d = cp.asarray(mass)

    if run_direct:
        dt_dir = _time_call(lambda: compute_acceleration(pos_d, mass_d, eps=eps))
    else:
        dt_dir = float("nan")

    dt_bh = _time_call(lambda: compute_acceleration_bh(pos_d, mass_d, theta=theta, eps=eps))

    speedup = dt_dir / dt_bh if dt_dir == dt_dir else float("nan")
    print(
        f"N={n:>8}  direct={dt_dir * 1e3:8.2f} ms  "
        f"bh(θ={theta})={dt_bh * 1e3:8.2f} ms  speedup={speedup:6.1f}x"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sizes", nargs="+", type=int, default=[4096, 16384, 65536, 262144, 1048576])
    p.add_argument("--theta", type=float, default=0.5)
    p.add_argument("--eps", type=float, default=2e-2)
    p.add_argument(
        "--direct-cutoff",
        type=int,
        default=131072,
        help="Skip O(N^2) baseline above this N (it gets very slow).",
    )
    args = p.parse_args()
    for n in args.sizes:
        bench(n, theta=args.theta, eps=args.eps, run_direct=(n <= args.direct_cutoff))


if __name__ == "__main__":
    main()
