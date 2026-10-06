"""GE Fig36.2-4 cash timing, independent policies and interacting exercise states."""

import itertools
import math

import numpy as np
import pytest
from hullkit import _commodity_foundations as c
from hullkit import _real_options_foundations as r


def source_tree():
    tree = c.build_commodity_tree(20, [22, 23, 24], 0.1, 0.2)
    return tree, r.operating_cashflows(tree, 2, 17, 6)


def independent_paths():
    """27 full histories with separately written branch probabilities/price calibration."""

    def branches(j):
        if j == 2:
            return [(2, 133 / 150), (1, 2 / 75), (0, 13 / 150)]
        if j == -2:
            return [(0, 13 / 150), (-1, 2 / 75), (-2, 133 / 150)]
        return [
            (j + 1, 1 / 6 + (0.01 * j * j - 0.1 * j) / 2),
            (j, 2 / 3 - 0.01 * j * j),
            (j - 1, 1 / 6 + (0.01 * j * j + 0.1 * j) / 2),
        ]

    histories = [((0,), 1.0)]
    layers = [histories]
    for _ in range(3):
        histories = [
            ((*path, child), weight * p)
            for path, weight in histories
            for child, p in branches(path[-1])
        ]
        layers.append(histories)
    spacing = 0.2 * math.sqrt(3)
    alpha = [math.log(20)]
    for future, layer in zip([22, 23, 24], layers[1:], strict=True):
        alpha.append(math.log(future / sum(w * math.exp(spacing * p[-1]) for p, w in layer)))
    return branches, alpha, spacing, layers


def independent_policy_value(kind):
    """Optimize 512 complete Markov policies by direct pathwise discounted cash."""
    _, alpha, spacing, layers = independent_paths()
    nodes = [(t, j) for t in range(3) for j in sorted({p[-1] for p, _ in layers[t]})]
    best = -math.inf
    for flags in itertools.product([False, True], repeat=len(nodes)):
        policy = dict(zip(nodes, flags, strict=True))
        expected = 0.0
        for path, weight in layers[-1]:
            expanded = False
            cash = 0.0
            for t, j in enumerate(path[:-1]):
                if policy[t, j]:
                    if kind == "abandon":
                        break
                    if not expanded:
                        cash -= 2 * math.exp(-0.1 * t)
                        expanded = True
                next_spot = math.exp(alpha[t + 1] + spacing * path[t + 1])
                cash += (1.2 if expanded else 1) * (2 * next_spot - 40) * math.exp(-0.1 * (t + 1))
            expected += weight * cash
        best = max(best, expected)
    return best


def test_source_project_cashflows_all_nodes_and_direct_dcf():
    tree, cash = source_tree()
    expected = [
        layer["reach_probabilities"] @ cf
        for layer, cf in zip(tree["levels"][1:], cash[1:], strict=True)
    ]
    assert expected == pytest.approx([4, 6, 8], abs=1e-12)
    values = r.project_value_tree(tree, cash, 0.1)
    assert values[0][0] == pytest.approx(14.46, rel=0, abs=0.005)
    assert values[0][0] - 15 == pytest.approx(-0.54, rel=0, abs=0.005)
    assert values[1][::-1] == pytest.approx([38.32, 10.80, -9.65], rel=0, abs=0.005)
    assert values[2][::-1] == pytest.approx([42.24, 21.42, 5.99, -5.31, -13.49], rel=0, abs=0.005)
    assert values[3] == pytest.approx(np.zeros(5), abs=1e-13)
    direct = sum(cf * math.exp(-0.1 * t) for t, cf in enumerate([0, 4, 6, 8]))
    assert values[0][0] == pytest.approx(direct, abs=1e-12)


def test_source_abandonment_expansion_all_nodes_and_independent_cash_policies():
    tree, cash = source_tree()
    abandonment = r.investment_options(tree, cash, 0.1, allow_abandon=True)
    expansion = r.investment_options(
        tree, cash, 0.1, expanded_cashflows=[1.2 * x for x in cash], expansion_cost=2
    )
    assert abandonment["option_values"][0][0] == pytest.approx(1.94, rel=0, abs=0.005)
    assert abandonment["value"] - 15 == pytest.approx(1.40, rel=0, abs=0.005)
    assert abandonment["option_values"][1][::-1] == pytest.approx([0, 0.80, 9.65], rel=0, abs=0.005)
    assert abandonment["option_values"][2][::-1] == pytest.approx(
        [0, 0, 0, 5.31, 13.49], rel=0, abs=0.005
    )
    assert list(abandonment["decisions"][1][0][::-1]) == ["continue", "continue", "abandon"]
    assert list(abandonment["decisions"][2][0][::-1]) == ["continue"] * 3 + ["abandon"] * 2
    assert expansion["option_values"][0][0] == pytest.approx(1.06, rel=0, abs=0.005)
    assert expansion["value"] - 15 == pytest.approx(0.52, rel=0, abs=0.005)
    assert expansion["option_values"][1][::-1] == pytest.approx([5.66, 0.34, 0], rel=0, abs=0.005)
    assert expansion["option_values"][2][::-1] == pytest.approx(
        [6.45, 2.28, 0, 0, 0], rel=0, abs=0.005
    )
    assert list(expansion["decisions"][1][0][::-1]) == ["expand", "continue", "continue"]
    assert list(expansion["decisions"][2][0][::-1]) == ["expand"] * 2 + ["continue"] * 3
    d = tree["levels"][1]
    d_wait = math.exp(-0.1) * sum(
        p * abandonment["option_values"][2][k]
        for p, k in zip(d["probabilities"][0], d["successors"][0], strict=True)
    )
    assert d_wait == pytest.approx(4.64, rel=0, abs=0.005)
    assert 0.2 * expansion["base_values"][1][1] - 2 == pytest.approx(0.16, rel=0, abs=0.005)
    assert 0.2 * expansion["base_values"][0][0] - 2 == pytest.approx(0.89, rel=0, abs=0.005)
    for result, kind in [(abandonment, "abandon"), (expansion, "expand")]:
        assert result["value"] == pytest.approx(independent_policy_value(kind), abs=1e-11)


def test_joint_source_states_and_nonrecombining_history_reference():
    tree, cash = source_tree()
    joint = r.investment_options(
        tree,
        cash,
        0.1,
        allow_abandon=True,
        expanded_cashflows=[1.2 * x for x in cash],
        expansion_cost=2,
    )
    abandon = r.investment_options(tree, cash, 0.1, allow_abandon=True)
    expand = r.investment_options(
        tree, cash, 0.1, expanded_cashflows=[1.2 * x for x in cash], expansion_cost=2
    )
    # Additional check, NOT a printed value. Joint optimization does not match
    # the source footnote claiming no interaction in this coarse example.
    # An independently enumerated admissible policy already exceeds additivity:
    # expand today, then optimally abandon the proportionally enlarged project.
    strategy = 1.2 * independent_policy_value("abandon") - 2
    assert joint["value"] == pytest.approx(strategy, abs=1e-11)
    assert joint["option_values"][0][0] == pytest.approx(3.217896081, abs=5e-10)
    assert joint["value"] > abandon["value"] + expand["value"] - joint["base_values"][0][0]
    assert joint["decisions"][0][0, 0] == "expand"
    branches, alpha, spacing, _ = independent_paths()

    def history_value(t, j, expanded):
        if t == 3:
            return 0.0

        def carry(mode):
            return math.exp(-0.1) * sum(
                p
                * (
                    (1.2 if mode else 1) * (2 * math.exp(alpha[t + 1] + spacing * k) - 40)
                    + history_value(t + 1, k, mode)
                )
                for k, p in branches(j)
            )

        return max(0, carry(True)) if expanded else max(0, carry(False), carry(True) - 2)

    for t, level in enumerate(tree["levels"]):
        for state in [0, 1]:
            assert joint["state_values"][t][state] == pytest.approx(
                [history_value(t, int(j), bool(state)) for j in level["labels"]], abs=1e-11
            )
        assert joint["state_values"][t][2:] == pytest.approx(
            np.zeros((2, len(level["spot"]))), abs=1e-13
        )
        assert set(joint["decisions"][t][1]) <= {"continue", "abandon", "complete"}
        assert np.all(joint["decisions"][t][2:] == "absorbed")


def test_interaction_nonproportional_cashflows_and_once_only_expansion():
    tree = c.build_commodity_tree(1, [1], 0, 0)
    base = [np.zeros(1), np.array([-5.0])]
    enlarged = [np.zeros(1), np.array([5.0])]
    abandon = r.investment_options(tree, base, 0, allow_abandon=True)
    expand = r.investment_options(tree, base, 0, expanded_cashflows=enlarged, expansion_cost=2)
    joint = r.investment_options(
        tree, base, 0, allow_abandon=True, expanded_cashflows=enlarged, expansion_cost=2
    )
    assert [abandon["value"], expand["value"], joint["value"]] == pytest.approx(
        [0, 3, 3], abs=1e-13
    )
    assert joint["option_values"][0][0] == pytest.approx(8, abs=1e-13)
    assert (
        joint["option_values"][0][0]
        < abandon["option_values"][0][0] + expand["option_values"][0][0]
    )
    assert joint["decisions"][0][0, 0] == "expand"
    assert joint["state_values"][0][1, 0] == pytest.approx(5, abs=1e-13)
    # Fixed costs unchanged: enlarged cash is not 1.2 times base cash.
    tree, base = source_tree()
    enlarged = r.operating_cashflows(tree, 2.4, 17, 6)
    result = r.investment_options(tree, base, 0.1, expanded_cashflows=enlarged, expansion_cost=2)
    direct = sum(
        math.exp(-0.1 * t) * (2.4 * f - 2.4 * 17 - 6) for t, f in enumerate([22, 23, 24], start=1)
    )
    assert result["state_values"][0][1, 0] == pytest.approx(direct, abs=1e-11)
    assert result["state_values"][0][1, 0] > 1.2 * result["base_values"][0][0]
    # Half-year cash timing and end-of-life salvage are explicit.
    tree = c.build_commodity_tree(20, [20, 20], 0, 0, dt=0.5)
    cash = r.operating_cashflows(tree, 2, 17, 6)
    assert [x[0] for x in cash] == pytest.approx([0, 0, 0], abs=1e-13)
    salvage = r.investment_options(tree, cash, 0.1, allow_abandon=True, salvage=3)
    assert salvage["value"] == pytest.approx(3, abs=1e-13)
    assert salvage["decisions"][0][0, 0] == "abandon"
    with pytest.raises(ValueError):
        r.investment_options(tree, cash, 0.1, expansion_cost=2)
    with pytest.raises(ValueError):
        r.project_value_tree(tree, cash[:-1], 0.1)
