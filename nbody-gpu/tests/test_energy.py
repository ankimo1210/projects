"""Plummer-sphere energy conservation under leapfrog."""
from __future__ import annotations

import numpy as np
import pytest

from nbody import Simulation, plummer_sphere


@pytest.fixture(scope="module")
def cupy_available():
    try:
        import cupy
        _ = cupy.arange(1)
        return True
    except Exception:
        pytest.skip("CuPy/CUDA not available", allow_module_level=False)


def test_plummer_energy_drift_small(cupy_available):
    n = 512
    pos, vel, mass = plummer_sphere(n=n, total_mass=1.0, scale_radius=1.0, seed=42)
    sim = Simulation.from_host(pos, vel, mass, dt=1e-3, eps=2e-2)
    E0 = sim.total_energy()
    sim.step(1000)  # ~1 dynamical time worth
    E1 = sim.total_energy()
    drift = abs(E1 - E0) / abs(E0)
    # Plummer with N=512 and eps=2e-2: |dE/E| ~ 1e-3 over 1000 steps is acceptable
    assert drift < 5e-3, f"energy drift {drift:.2e}"


def test_plummer_momentum_drift_small(cupy_available):
    n = 512
    pos, vel, mass = plummer_sphere(n=n, total_mass=1.0, scale_radius=1.0, seed=7)
    sim = Simulation.from_host(pos, vel, mass, dt=1e-3, eps=2e-2)
    sim.step(1000)
    p = sim.momentum()
    # leapfrog preserves linear momentum exactly (up to roundoff)
    assert np.linalg.norm(p) < 1e-3, f"|p| = {np.linalg.norm(p)}"


def test_plummer_virial_initial_ratio(cupy_available):
    """At t=0 a virialised Plummer sphere should satisfy 2T + U ≈ 0."""
    n = 4096
    pos, vel, mass = plummer_sphere(n=n, total_mass=1.0, scale_radius=1.0, seed=0)
    sim = Simulation.from_host(pos, vel, mass, dt=1e-3, eps=1e-2)
    T = sim.kinetic_energy()
    U = sim.potential_energy()
    virial = (2 * T + U) / abs(U)
    # AHW-1974 sampling is approximate but should land within a few percent.
    assert abs(virial) < 0.1, f"2T+U / |U| = {virial}"
