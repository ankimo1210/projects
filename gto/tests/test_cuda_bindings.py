"""Native binding guards: gto_cuda weight-length validation (#14) and GIL
release (#4), plus the gto_py equity iterations guard (#11). Skipped when the
maturin-built extensions are absent from the venv."""

from __future__ import annotations

import threading
import time

import pytest

try:
    import gto_cuda

    HAS_CUDA = hasattr(gto_cuda, "batch_solve_rust")
except ImportError:
    HAS_CUDA = False

try:
    import gto_py

    HAS_EQUITY = hasattr(gto_py, "equity")
except ImportError:
    HAS_EQUITY = False

SPOT = {"board": ["Ah", "Kd", "7s"], "pot_bb": 6.0, "effective_stack_bb": 100.0}


@pytest.mark.skipif(not HAS_CUDA, reason="gto_cuda not built in this venv")
@pytest.mark.parametrize(
    "ip_w,oop_w",
    [([0.1] * 10, None), (None, [0.1] * 2000)],
)
def test_batch_solve_rejects_bad_weight_length(ip_w, oop_w):
    # iw[k % nc] would otherwise panic (short) or silently truncate (long).
    with pytest.raises(ValueError):
        gto_cuda.batch_solve_rust([SPOT], 50, None, ip_w, oop_w)


@pytest.mark.skipif(not HAS_CUDA, reason="gto_cuda not built in this venv")
def test_batch_solve_releases_gil():
    done = threading.Event()

    def run():
        try:
            gto_cuda.batch_solve_rust([SPOT], 1500)
        finally:
            done.set()

    threading.Thread(target=run).start()
    counter = 0
    start = time.perf_counter()
    while not done.is_set():
        counter += 1
        if time.perf_counter() - start > 30:
            break
    # A freed GIL lets the counter reach millions; a held GIL leaves it near zero.
    assert counter > 1000, "gto_cuda solve appears to hold the GIL (#4 regression)"


@pytest.mark.skipif(not HAS_EQUITY, reason="gto_py.equity not built in this venv")
def test_equity_rejects_zero_iterations():
    with pytest.raises(ValueError):
        gto_py.equity("Ah As", "Kc Kd", "", 0)
