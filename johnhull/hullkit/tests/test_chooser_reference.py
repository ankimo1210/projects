"""Independent conditional valuation and narrow-transition regression."""

import importlib

import pytest


def reference():
    return importlib.import_module("johnhull.scripts.build_chooser_reference")


@pytest.mark.parametrize(
    "t1,pin",
    [
        (0.1, 10.483695744000126),
        (0.5, 13.344280448069238),
        (0.9, 15.168232237397923),
        (0.999999, 15.55708234558728),
    ],
)
def test_independent_integral_pins_and_near_expiry(t1, pin):
    value, error = reference().integrate_chooser(100, 100, 0.05, 0.2, t1, 1, 0.02)
    assert value == pytest.approx(pin, abs=1e-10)
    assert error < 1e-8


def test_inventory_mc_and_special_limits():
    d = reference().build()
    assert len(d["cases"]) == 64
    assert len(d["mc"]) == 4
    assert all(
        r["paths"] == 524288 and abs(r["price"] - r["reference_price"]) < 6 * r["standard_error"]
        for r in d["mc"]
    )
    assert any(r["T1"] == 0 for r in d["cases"])
    assert any(r["T1"] == r["T2"] for r in d["cases"])
    assert any(r["sigma"] == 0 for r in d["cases"])
    assert any(r["T2"] == 0 for r in d["cases"])
    assert any(r["q"] < 0 and r["r"] < 0 for r in d["cases"])


def test_reference_recomputation_does_not_use_hullkit(monkeypatch):
    from hullkit import bsm, chooser

    def forbidden(*args, **kwargs):
        raise AssertionError("production dependency reached")

    monkeypatch.setattr(bsm, "call_price", forbidden)
    monkeypatch.setattr(bsm, "put_price", forbidden)
    monkeypatch.setattr(chooser, "chooser_price", forbidden)
    reference().build.cache_clear()
    assert reference().build()["example"]["price"] == pytest.approx(13.344280448069238, abs=1e-10)
