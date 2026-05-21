"""Two-body circular orbit: known-analytical reference."""

from __future__ import annotations

import math

import numpy as np
import pytest

from nbody import Simulation, two_body_circular


@pytest.fixture(scope="module")
def cupy_available():
    try:
        import cupy

        _ = cupy.arange(1)
        return True
    except Exception:
        pytest.skip("CuPy/CUDA not available", allow_module_level=False)


def test_circular_orbit_returns_to_start(cupy_available):
    pos, vel, mass = two_body_circular(m1=1.0, m2=1.0, separation=1.0)
    sim = Simulation.from_host(pos, vel, mass, dt=1e-3, eps=1e-3)
    T = 2.0 * math.pi / math.sqrt(2.0)
    n_steps = int(round(T / sim.dt))
    sim.step(n_steps)
    final = sim.positions_host()
    # particles should return to within 1% of separation
    err = np.linalg.norm(final - pos)
    assert err < 1e-2, f"final-initial position drift = {err}"


def test_energy_conserved_two_body(cupy_available):
    pos, vel, mass = two_body_circular(m1=1.0, m2=1.0, separation=1.0)
    sim = Simulation.from_host(pos, vel, mass, dt=1e-3, eps=1e-3)
    E0 = sim.total_energy()
    sim.step(5000)
    E1 = sim.total_energy()
    rel = abs(E1 - E0) / abs(E0)
    assert rel < 1e-4, f"energy drift {rel} over 5000 steps"


def test_momentum_conserved_two_body(cupy_available):
    pos, vel, mass = two_body_circular(m1=1.0, m2=1.0, separation=1.0)
    sim = Simulation.from_host(pos, vel, mass, dt=1e-3, eps=1e-3)
    sim.step(2000)
    p = sim.momentum()
    assert np.linalg.norm(p) < 1e-5, f"momentum = {p}"
