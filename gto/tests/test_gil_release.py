"""B4 regression: heavy gto_py solves must release the GIL.

`solve_hu_river` runs for seconds; before the fix it held the GIL for its
whole duration, freezing every other Python thread (and thus the FastAPI
event loop / its ThreadPoolExecutor). With `py.allow_threads(...)` wrapping
the compute, a competing Python thread keeps making progress while the solve
runs. We measure that progress with a counter.
"""

import threading
import time

import pytest

try:
    import gto_py

    HAS_BINDING = hasattr(gto_py, "solve_hu_river")
except ImportError:
    HAS_BINDING = False

pytestmark = pytest.mark.skipif(
    not HAS_BINDING, reason="gto_py.solve_hu_river not built in this venv"
)


def test_solve_hu_river_releases_gil():
    # A small but non-trivial solve so the worker is busy for ~1-2s.
    board = ["Ah", "Kd", "7s", "2c", "9h"]
    solve_done = threading.Event()
    solve_err = []

    def run_solve():
        try:
            gto_py.solve_hu_river(board, 20.0, 90.0, 2000)
        except Exception as e:  # pragma: no cover - surfaced via assert below
            solve_err.append(e)
        finally:
            solve_done.set()

    worker = threading.Thread(target=run_solve)
    worker.start()

    # Spin a pure-Python counter in the main thread. If the solve holds the
    # GIL, this loop is starved and the counter barely moves; if the GIL is
    # released during compute, the counter climbs freely.
    counter = 0
    start = time.perf_counter()
    while not solve_done.is_set():
        counter += 1
        # Cap the wait so a hung solve can't hang the suite forever.
        if time.perf_counter() - start > 30:
            break

    worker.join(timeout=30)
    assert not solve_err, f"solve raised: {solve_err[0]!r}"
    assert not worker.is_alive(), "solve thread did not finish"

    # Generous threshold: a freed GIL lets the counter reach millions; a held
    # GIL leaves it near zero. 1000 is far above the held-GIL floor yet far
    # below what a released GIL achieves, so the test is not flaky.
    assert counter > 1000, (
        f"main-thread counter only reached {counter}; "
        "the solve appears to hold the GIL (B4 regression)"
    )
