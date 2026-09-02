"""Package-level export tests."""

import subprocess
import sys

import hullkit


def test_all_submodules_exported():
    assert len(hullkit.__all__) == len(set(hullkit.__all__))
    for name in hullkit.__all__:
        assert hasattr(hullkit, name)


def test_callable_reachable_via_package():
    # exercising a function through the package object (no explicit submodule import)
    assert hullkit.bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0) > 0.0


def test_hullkit_import_graph_is_torch_free():
    # Must run in a fresh interpreter: `torch in sys.modules` is a property of
    # the whole process, so in a full-workspace run any earlier test that
    # imports torch makes this fail even though hullkit is clean. Checking it
    # here only tested which project pytest happened to collect first.
    code = "import hullkit, sys; assert 'torch' not in sys.modules, sorted(sys.modules)"
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
