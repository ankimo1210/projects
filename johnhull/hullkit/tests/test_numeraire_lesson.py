"""Delivery consumer requires numerical provenance and independently pinned results."""

import importlib
import json

import pytest

KEYS = {
    "martingale_numeraire_pricing",
    "martingale_numeraire_forward",
    "martingale_numeraire_payment",
    "martingale_numeraire_annuity",
}


def test_four_figures_consume_checked_values_and_monte_carlo_intervals():
    lesson = importlib.import_module("hullkit._numeraire_lesson")
    figures = lesson._figures()
    assert set(figures) == KEYS
    assert len(figures["martingale_numeraire_pricing"].data[0].error_y.array) == 6
    assert list(figures["martingale_numeraire_forward"].data[0].y) == pytest.approx(
        [109.37244366983968, 107.46647739330601, 108.4152721949055]
    )
    assert all(f.layout.meta["section"] == "28.4" for f in figures.values())


@pytest.mark.parametrize(
    "mutation",
    [
        "status",
        "reference hash",
        "source missing",
        "joint",
        "stock",
        "rates",
        "annuity",
        "weights",
        "mc",
        "result hash",
    ],
)
def test_consumer_rejects_corrupted_and_resigned_results(tmp_path, monkeypatch, mutation):
    lesson = importlib.import_module("hullkit._numeraire_lesson")
    record = json.loads(lesson._RECORD.read_text())
    if mutation == "status":
        record["status"] = "FAIL"
    elif mutation == "reference hash":
        record["artifact_sha256"] = "0" * 64
    elif mutation == "source missing":
        del record["source_sha256"]["hullkit/src/hullkit/_numeraire_choices.py"]
    elif mutation == "joint":
        record["api_joint"][0]["mean"][1] += 0.1
    elif mutation == "stock":
        record["api_stock"][0]["price_q"] += 1
    elif mutation == "rates":
        record["api_rates"][0]["term_payment"] += 0.01
    elif mutation == "annuity":
        record["api_annuity"][0]["mean_a_rate"] += 0.01
    elif mutation == "weights":
        record["api_annuity"][0]["weights"][0] += 0.1
    elif mutation == "mc":
        record["pricing_mc"][0]["mean"] += 3
    else:
        record["result_sha256"] = "0" * 64
    if mutation in ["joint", "stock", "rates", "annuity", "weights", "mc"]:
        record["result_sha256"] = lesson._result_digest(record)
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record))
    monkeypatch.setattr(lesson, "_RECORD", target)
    with pytest.raises(ValueError):
        lesson._figures()
