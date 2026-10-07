"""Hull §9.4 incremental concept on explicit synthetic shared scenarios."""

import math

import numpy as np
import pytest
from hullkit import _xva_foundations as x


def test_source_incremental_definition_and_independent_two_state_cash():
    book = np.array([[10, 10], [-10, -10]])
    trade = -0.6 * book
    q = np.array([0.01, 0.02])
    df = np.array([1, 1])
    a = x.incremental_cva(book, trade, q, df)
    before = sum(0.5 * sum(p * max(v, 0) for p, v in zip(q, row, strict=True)) for row in book)
    after = sum(
        0.5 * sum(p * max(v, 0) for p, v in zip(q, row, strict=True)) for row in book + trade
    )
    assert [a["before"], a["after"], a["increment"]] == pytest.approx(
        [before, after, after - before]
    )
    assert a["increment"] < 0
    standalone = x.incremental_cva(np.zeros_like(book), trade, q, df)
    assert standalone["after"] > 0
    assert a["after"] != pytest.approx(a["before"] + standalone["after"])


def test_independent_normal_positive_part_and_paired_seeded_mc():
    normal = np.random.default_rng(904).normal(0, 10, (200000, 1))
    a = x.incremental_cva(normal, -0.5 * normal, [0.03], [0.9], loss_given_default=0.6)
    analytic = -0.5 * (10 / math.sqrt(2 * math.pi)) * 0.03 * 0.9 * 0.6
    samples = a["path_loss_after"] - a["path_loss_before"]
    se = np.std(samples, ddof=1) / math.sqrt(len(samples))
    assert abs(a["increment"] - analytic) < 6 * se
    assert a["increment"] == pytest.approx(samples.mean(), abs=1e-12)
