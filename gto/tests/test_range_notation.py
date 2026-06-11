"""Range-notation grammar: "AA,AKs:0.5,KQo" -> weight vector [1326]."""

import numpy as np
import pytest
from gto.library import range_builder
from gto.library.range_notation import parse_range_notation


def test_single_pair_class():
    w = parse_range_notation("AA")
    assert w.shape == (1326,)
    assert w.sum() == pytest.approx(6.0)  # 6 AA combos at weight 1
    for idx in range_builder.hand_to_combo_indices("AA"):
        assert w[idx] == 1.0


def test_weighted_and_multiple_classes():
    w = parse_range_notation("AA, AKs:0.5, KQo")
    assert w[range_builder.hand_to_combo_indices("AKs")[0]] == 0.5
    assert w[range_builder.hand_to_combo_indices("KQo")[0]] == 1.0
    assert w.sum() == pytest.approx(6 * 1.0 + 4 * 0.5 + 12 * 1.0)


def test_last_assignment_wins_and_bounds():
    w = parse_range_notation("AKs:0.2,AKs:0.9")
    assert w[range_builder.hand_to_combo_indices("AKs")[0]] == 0.9


@pytest.mark.parametrize("bad", ["", "ZZ", "AKs:1.5", "AKs:-1", "AKs:abc", "AK"])
def test_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_range_notation(bad)
