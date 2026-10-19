import pytest
from sector_leadlag.main import ROBUSTNESS, SCENARIOS, run_main_a, run_main_b

G0 = {"selected": "lagged", "pass": True}


def _verdict(world) -> tuple[dict, dict]:
    a = run_main_a(world, {"g0": G0}, n_boot=300)
    b = run_main_b(world, {"g0": G0, "main_a": a})
    return a, b


@pytest.fixture(scope="module")
def decayed(decayed_world):
    return _verdict(decayed_world)


def test_a_real_lead_in_the_stocks_is_usable(decayed):
    a, b = decayed
    assert a["h1"]["pass"] and a["h2_pass"] and a["robust"]
    assert set(a["h2"]) == set(SCENARIOS) and set(ROBUSTNESS) < set(a["h2"])
    low, high = a["h1"]["ratio_ci"]
    assert low < a["h1"]["basket"]["beta_1e4"] / a["h1"]["etf"]["beta_1e4"] < high
    assert b["verdict"] == "usable"
    assert b["h1"]["etf"]["beta_1e4"] < 0 < b["h1"]["basket"]["beta_1e4"]
    assert b["h3"]["label"] == "decay_continued"


def test_costs_lower_the_cash_strategy_but_not_the_spread(decayed):
    a, _ = decayed
    base, costly = a["h2"]["base"], a["h2"]["cost_5bp"]
    assert costly["cash"]["mean_ann"] < base["cash"]["mean_ann"]
    assert costly["spread"]["mean_ann"] == base["spread"]["mean_ann"]


def test_a_lead_in_the_etfs_only_is_etf_only(etf_only_world):
    _, b = _verdict(etf_only_world)
    assert b["verdict"] == "etf_only"
