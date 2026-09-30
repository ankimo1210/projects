"""Gate rejects changed references and real reset/discount/notional mutants."""

import copy
import importlib
import math

import pytest


def gate():
    return importlib.import_module("johnhull.scripts.verify_cliquet_numerics")


def data():
    return importlib.import_module("johnhull.scripts.build_cliquet_reference").build()


def test_independent_prices_and_mc_agree():
    result = gate().verify(data())
    assert result["case_count"] == 60
    assert result["max_price_error"] < 1e-9
    assert result["max_mc_standard_errors"] < 6
    assert result["max_parity_error"] < 1e-10


def test_reference_mutations_are_rejected():
    rows = gate().negative_controls(data())
    assert {row["mutation"] for row in rows} == {"price", "reset", "discount", "cap"}
    assert all(row["rejected"] for row in rows)


@pytest.mark.parametrize("mutation", ["fixed-strike", "final-discount", "fixed-notional"])
def test_real_api_mutations_are_detected(monkeypatch, mutation):
    module = gate()
    from hullkit import bsm, forward_start

    def wrong(S, r, sigma, payment_times, q=0):
        starts = [0, *payment_times[:-1]]
        if mutation == "fixed-strike":
            return sum(bsm.call_price(S, S, r, sigma, end, q) for end in payment_times)
        if mutation == "final-discount":
            return sum(
                forward_start.forward_start_call(S, r, sigma, start, end, q)
                * math.exp(-r * (payment_times[-1] - end))
                for start, end in zip(starts, payment_times, strict=True)
            )
        return sum(
            S * math.exp(-r * start) * bsm.call_price(1, 1, r, sigma, end - start, q)
            for start, end in zip(starts, payment_times, strict=True)
        )

    monkeypatch.setattr(module.cliquet, "cliquet_call", wrong)
    with pytest.raises(ValueError, match="API differs"):
        module.verify(data())


def test_changed_mc_interval_is_rejected():
    changed = copy.deepcopy(data())
    changed["mc"][0]["ci95"][1] += 1
    with pytest.raises(ValueError):
        gate().verify(changed)
