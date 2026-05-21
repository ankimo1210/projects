"""Barnes-Hut vs O(N^2) direct: accuracy under theta."""

from __future__ import annotations

import cupy as cp
import numpy as np
import pytest

from nbody.forces import compute_acceleration
from nbody.forces_bh import compute_acceleration_bh
from nbody.initial_conditions import plummer_sphere


@pytest.fixture(scope="module")
def cupy_available():
    try:
        import cupy

        _ = cupy.arange(1)
        return True
    except Exception:
        pytest.skip("CuPy/CUDA not available", allow_module_level=False)


def _plummer_device(n, seed):
    pos, _, mass = plummer_sphere(n=n, seed=seed)
    return cp.asarray(pos), cp.asarray(mass)


def test_bh_matches_direct_at_small_theta(cupy_available):
    """At θ very small Barnes-Hut should converge to the direct sum."""
    n = 1024
    pos, mass = _plummer_device(n, seed=0)
    eps = 2e-2
    a_direct = compute_acceleration(pos, mass, eps=eps)
    a_bh, _ = compute_acceleration_bh(pos, mass, theta=0.05, eps=eps)
    a_d = cp.asnumpy(a_direct)
    a_b = cp.asnumpy(a_bh)
    rel = np.linalg.norm(a_b - a_d, axis=1) / (np.linalg.norm(a_d, axis=1) + 1e-12)
    median = float(np.median(rel))
    p99 = float(np.percentile(rel, 99))
    print(f"θ=0.05  median rel err = {median:.2e}  p99 = {p99:.2e}")
    assert median < 1e-2, f"BH median err {median} too high at small theta"


def test_bh_relaxed_accuracy_at_theta_05(cupy_available):
    """At θ=0.5 (typical BH value) errors should be a few percent."""
    n = 4096
    pos, mass = _plummer_device(n, seed=1)
    eps = 2e-2
    a_direct = compute_acceleration(pos, mass, eps=eps)
    a_bh, _ = compute_acceleration_bh(pos, mass, theta=0.5, eps=eps)
    a_d = cp.asnumpy(a_direct)
    a_b = cp.asnumpy(a_bh)
    rel = np.linalg.norm(a_b - a_d, axis=1) / (np.linalg.norm(a_d, axis=1) + 1e-12)
    median = float(np.median(rel))
    p99 = float(np.percentile(rel, 99))
    print(f"θ=0.5   median rel err = {median:.2e}  p99 = {p99:.2e}")
    assert median < 5e-2, f"BH median err {median} too high at theta=0.5"


def test_bh_force_balance(cupy_available):
    """Newton's third law in aggregate: Σ m_i a_i ≈ 0 (no external force)."""
    n = 4096
    pos, mass = _plummer_device(n, seed=2)
    a_bh, _ = compute_acceleration_bh(pos, mass, theta=0.5, eps=2e-2)
    net = cp.asnumpy((mass[:, None] * a_bh).sum(0))
    # BH is approximate, so net force isn't exactly zero, but it must be small
    # relative to the typical per-particle force magnitude.
    typical = float(cp.linalg.norm(a_bh, axis=1).mean()) * float(mass.mean()) * n
    rel = np.linalg.norm(net) / max(typical, 1e-30)
    assert rel < 5e-3, f"net force / typical = {rel}"
