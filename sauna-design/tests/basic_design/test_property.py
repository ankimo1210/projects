import pytest

IDENTITY = {"name": "検証用物件", "location": "東京都・検証用所在地"}


def finance_evidence():
    from basic_design.property import KEYS

    return {k: "検証用の費用資料" for k in KEYS}


def test_search_formula_matches_full_budget_and_frozen_target():
    from basic_design.property import candidate_budget, goal_inputs, rent_limit, search_total

    r = candidate_budget(goal_inputs())
    assert r["total_cash"] == pytest.approx(198243982.04305)
    assert search_total(1200000, 6, 12000000) == pytest.approx(r["total_cash"])
    assert rent_limit(6, 12000000) == pytest.approx(1299209.375, rel=1e-5)
    assert rent_limit(6, 7000000) == pytest.approx(906130.958, rel=1e-5)


def test_blank_finance_is_unknown_and_real_zero_is_valid():
    from basic_design.property import candidate_budget, goal_inputs

    p = goal_inputs()
    p["extra_cash"] = None
    assert candidate_budget(p)["total_cash"] is None
    p["extra_cash"] = 0
    assert candidate_budget(p)["total_cash"] is not None


def test_favourable_budget_does_not_override_missing_or_failed_evidence():
    from basic_design.property import assess, gate_template, goal_inputs

    gates = gate_template()
    assert assess(goal_inputs(), gates)["status"] == "資料不足"
    gates[0].update(status=3, evidence="用途禁止の貸主書面", checked_at="2026-11-15")
    assert (
        assess(goal_inputs(), gates, identity=IDENTITY, finance_evidence=finance_evidence())[
            "status"
        ]
        == "成立困難"
    )


def test_every_gate_needs_evidence_and_change_is_not_a_pass():
    from basic_design.property import assess, gate_template, goal_inputs

    gates = gate_template()
    for g in gates:
        g.update(status=1, evidence="検証用の仮証拠", checked_at="2026-11-15")
    assert (
        assess(goal_inputs(), gates, identity=IDENTITY, finance_evidence=finance_evidence())[
            "status"
        ]
        == "成立見込み（予備判定）"
    )
    gates[-1]["evidence"] = ""
    assert assess(goal_inputs(), gates)["status"] == "資料不足"
    gates[-1]["evidence"] = "検証用の仮証拠"
    gates[-1]["status"] = 2
    assert (
        assess(goal_inputs(), gates, identity=IDENTITY, finance_evidence=finance_evidence())[
            "status"
        ]
        == "変更で対応"
    )


def test_unsubstantiated_rejection_is_still_missing_information():
    from basic_design.property import assess, gate_template, goal_inputs

    gates = gate_template()
    gates[0]["status"] = 3
    assert assess(goal_inputs(), gates)["status"] == "資料不足"


def test_additional_cost_and_delay_consume_shared_budget_headroom():
    from basic_design.property import candidate_budget, goal_inputs

    p = goal_inputs()
    before = candidate_budget(p)
    p["paid_preopening_months"] += 1
    after = candidate_budget(p)
    assert after["total_cash"] - before["total_cash"] == pytest.approx(1320000)
    p["extra_direct"] = 1000000
    assert candidate_budget(p)["total_cash"] - after["total_cash"] == pytest.approx(1391500)


def test_saving_limits_and_negative_nonrent_operation_are_not_silently_accepted():
    from basic_design.property import candidate_budget, goal_inputs

    p = goal_inputs()
    p["pit_saving"] = 100000000
    with pytest.raises(ValueError):
        candidate_budget(p)
    p = goal_inputs()
    p["opex_delta"] = -100000000
    with pytest.raises(ValueError):
        candidate_budget(p)


def test_placeholder_evidence_invalid_dates_and_unknown_identity_do_not_pass():
    from basic_design.property import assess, gate_template, goal_inputs

    gates = gate_template()
    for g in gates:
        g.update(status=1, evidence="  ", checked_at="未確認")
    assert (
        assess(goal_inputs(), gates, identity=IDENTITY, finance_evidence=finance_evidence())[
            "status"
        ]
        == "資料不足"
    )
    for g in gates:
        g.update(evidence="検証資料", checked_at="2026-02-30")
    assert (
        assess(goal_inputs(), gates, identity=IDENTITY, finance_evidence=finance_evidence())[
            "status"
        ]
        == "資料不足"
    )
    for g in gates:
        g["checked_at"] = "2026-11-15"
    assert assess(goal_inputs(), gates, finance_evidence=finance_evidence())["status"] == "資料不足"
    e = finance_evidence()
    e["extra_cash"] = "未取得"
    assert (
        assess(goal_inputs(), gates, identity=IDENTITY, finance_evidence=e)["status"] == "資料不足"
    )


def test_over_budget_without_a_specific_change_plan_is_not_changeable():
    from basic_design.property import assess, gate_template, goal_inputs

    gates = gate_template()
    for g in gates:
        g.update(status=1, evidence="検証資料", checked_at="2026-11-15")
    p = goal_inputs()
    p["extra_cash"] = 5000000
    assert (
        assess(p, gates, identity=IDENTITY, finance_evidence=finance_evidence())["status"]
        == "予算超過・変更案未確認"
    )
    assert (
        assess(
            p,
            gates,
            identity=IDENTITY,
            finance_evidence=finance_evidence(),
            budget_change_plan="別工種の再見積案・確認待ち",
        )["status"]
        == "変更で対応"
    )
