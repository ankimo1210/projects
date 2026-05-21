"""High-level Simulation wrapper holding device state."""
from __future__ import annotations

from dataclasses import dataclass

import cupy as cp
import numpy as np

from .forces import compute_acceleration
from .integrator import leapfrog_step


@dataclass
class Simulation:
    pos: cp.ndarray   # (N, 3) float32 on device
    vel: cp.ndarray   # (N, 3) float32 on device
    mass: cp.ndarray  # (N,)   float32 on device
    acc: cp.ndarray   # (N, 3) float32 on device
    dt: float
    eps: float = 1e-2
    G: float = 1.0
    t: float = 0.0

    @classmethod
    def from_host(
        cls,
        pos: np.ndarray,
        vel: np.ndarray,
        mass: np.ndarray,
        dt: float,
        eps: float = 1e-2,
        G: float = 1.0,
    ) -> "Simulation":
        pos_d = cp.asarray(pos, dtype=cp.float32)
        vel_d = cp.asarray(vel, dtype=cp.float32)
        mass_d = cp.asarray(mass, dtype=cp.float32)
        acc_d = compute_acceleration(pos_d, mass_d, eps=eps, G=G)
        return cls(pos=pos_d, vel=vel_d, mass=mass_d, acc=acc_d, dt=dt, eps=eps, G=G)

    @property
    def n(self) -> int:
        return int(self.pos.shape[0])

    def step(self, n_steps: int = 1) -> None:
        for _ in range(n_steps):
            leapfrog_step(self.pos, self.vel, self.mass, self.acc,
                          dt=self.dt, eps=self.eps, G=self.G)
            self.t += self.dt

    # --- diagnostics ---

    def kinetic_energy(self) -> float:
        v2 = (self.vel * self.vel).sum(axis=1)
        return float(0.5 * (self.mass * v2).sum())

    def potential_energy(self) -> float:
        """U = -G Σ_{i<j} m_i m_j / sqrt(r_ij^2 + eps^2). O(N^2) — debugging only."""
        p = self.pos
        m = self.mass
        # broadcast diff
        diff = p[:, None, :] - p[None, :, :]
        r2 = (diff * diff).sum(axis=-1) + self.eps * self.eps
        inv_r = 1.0 / cp.sqrt(r2)
        # zero out the diagonal contribution (self-interaction)
        n = p.shape[0]
        idx = cp.arange(n)
        inv_r[idx, idx] = 0.0
        mm = m[:, None] * m[None, :]
        U = -0.5 * self.G * (mm * inv_r).sum()  # 0.5 because we double-count i,j and j,i
        return float(U)

    def total_energy(self) -> float:
        return self.kinetic_energy() + self.potential_energy()

    def momentum(self) -> np.ndarray:
        p = (self.mass[:, None] * self.vel).sum(axis=0)
        return cp.asnumpy(p)

    def positions_host(self) -> np.ndarray:
        return cp.asnumpy(self.pos)
