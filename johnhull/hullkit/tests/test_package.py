"""Package-level export tests."""

import hullkit


def test_all_submodules_exported():
    assert len(hullkit.__all__) == 14
    for name in hullkit.__all__:
        assert hasattr(hullkit, name)


def test_callable_reachable_via_package():
    # exercising a function through the package object (no explicit submodule import)
    assert hullkit.bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0) > 0.0
