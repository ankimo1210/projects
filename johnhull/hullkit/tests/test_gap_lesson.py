"""Plots preserve the signed payoff and insurer/holder distinction."""

import hashlib
import importlib
import json

import pytest


def _lesson():
    return importlib.import_module("hullkit._gap_lesson")


def _trace(figure, role):
    return next(trace for trace in figure.data if trace.meta["role"] == role)


def test_payoff_jump_is_not_drawn_as_a_continuous_diagonal():
    figure = _lesson()._figures()["gap_payoff"]
    call = _trace(figure, "call-active")
    put = _trace(figure, "put-active")
    assert call.x[0] == 100 and call.y[0] == -20
    assert put.x[-1] == 100 and put.y[-1] == -20
    boundary = _trace(figure, "trigger-value")
    assert list(boundary.x) == [100]
    assert list(boundary.y) == [0]
    assert _trace(figure, "call-limit").marker.symbol == "circle-open"


def test_insurance_plot_shows_insurer_sixty_holder_ten_at_340k():
    figure = _lesson()._figures()["gap_insurance"]
    insurer = _trace(figure, "insurer-active")
    holder = _trace(figure, "holder")
    assert insurer.y[list(insurer.x).index(340)] == 60
    assert holder.y[list(holder.x).index(340)] == 10
    assert _trace(figure, "insurer-trigger").y[0] == 0


def test_premium_decomposition_includes_expected_transfer_cost():
    figure = _lesson()._figures()["gap_premium"]
    insurer = _trace(figure, "insurer")
    holder = _trace(figure, "holder")
    transfer = _trace(figure, "transfer")
    assert insurer.y[0] == pytest.approx(3.4359470199, abs=1e-9)
    for gross, net, fee in zip(insurer.y, holder.y, transfer.y, strict=True):
        assert gross - net == pytest.approx(fee, abs=1e-10)


def test_reference_loader_rejects_unapproved_record(tmp_path):
    data = tmp_path / "reference.json"
    data.write_text('{"section": "26.4", "cases": []}', encoding="utf-8")
    record = tmp_path / "numeric.json"
    record.write_text(
        json.dumps(
            {
                "section": "26.4",
                "status": "FAIL",
                "artifact_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="passing"):
        _lesson()._load_reference(data, record)
