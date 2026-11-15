import copy
import json

import pytest
from basic_design.candidates import SOURCE, calculate, reference


def test_common_fee_is_included_through_rent_guarantee_and_runway():
    d = calculate()
    a = d["assumptions"]
    c = copy.deepcopy(d["candidates"][1])
    with_common = reference(c, a)
    c["common_ex_for_reference_yen"] = 0
    without_common = reference(c, a)
    assert with_common["monthly_rent_gross_yen"] == pytest.approx(1155000)
    assert with_common["reference_total_yen"] - without_common[
        "reference_total_yen"
    ] == pytest.approx(340000 * 1.1 * 9)


def test_deposit_writeoff_is_not_double_counted():
    d = calculate()
    a = d["assumptions"]
    c = copy.deepcopy(d["candidates"][0])
    before = reference(c, a)
    c["deposit_writeoff"] = "償却2か月（検証用）"
    assert reference(c, a)["reference_total_yen"] == before["reference_total_yen"]
    assert before["deposit_paid_yen"] == pytest.approx(4800000)


def test_saving_is_sensitivity_not_verified_reuse_or_feasibility():
    d = calculate()
    for c in d["candidates"]:
        assert c["verified_reuse_saving_yen"] is None
        assert c["unpriced_extras_yen"] is None
        assert c["bath_use_permission"] == "未確認"
        assert not c["fit_verified"]
        for r in c["cases"]:
            assert r["feasibility"] == "資料不足（参考総額のみ）"
        assert c["cases"][0]["reference_total_yen"] - c["cases"][2][
            "reference_total_yen"
        ] == pytest.approx(12000000 * 1.3915)


def test_closed_and_ambiguous_properties_are_not_main_candidates():
    source = json.loads(SOURCE.read_text())
    names = {c["name"] for c in source["candidates"]}
    assert len(names) == 4
    assert not names.intersection(c["name"] for c in source["excluded"] + source["holds"])
    assert source["candidates"][2]["common_confirmed_none"] is False
    assert source["candidates"][2]["common_published"].startswith("未記載")


def test_reference_uses_frozen_cost_intercept_and_explicit_fee_convention():
    d = calculate()
    a = d["assumptions"]
    for c in d["candidates"]:
        b = c["rent_ex_yen"]
        r = b + c["common_ex_for_reference_yen"]
        expected = 193701982.04305 + 9.9 * r + (c["deposit_months"] + 2.2) * b
        assert c["cases"][0]["reference_total_yen"] == pytest.approx(expected, rel=0, abs=0.05)
        assert c["cases"][0]["guarantee_reference_yen"] == pytest.approx(r * 1.1)
        needed = c["required_net_direct_saving_yen"]
        assert reference(c, a, needed)["reference_total_yen"] == pytest.approx(
            200000000, rel=0, abs=0.05
        )
