"""Checked correlated factors must survive re-signed delivery corruption."""

import importlib
import json

import pytest

KEYS = {
    "factor_ratio_ito",
    "factor_ratio_conditional",
    "factor_basis_covariance",
    "factor_measure_price",
}


def test_four_figures_preserve_correlated_arithmetic_and_raw_mc_intervals():
    m = importlib.import_module("hullkit._multi_factor_lesson")
    figs = m._figures()
    assert set(figs) == KEYS
    assert all(f.layout.meta["section"] == "28.5" for f in figs.values())
    assert list(figs["factor_ratio_ito"].data[0].y) == pytest.approx([-0.06684, 0.06904, -0.0022])
    assert sum(figs["factor_ratio_ito"].data[0].y) == pytest.approx(0, abs=1e-15)
    assert len(figs["factor_ratio_conditional"].data[0].error_y.array) == 6
    assert list(figs["factor_basis_covariance"].data[0].y) == pytest.approx(
        list(figs["factor_basis_covariance"].data[1].y)
    )
    assert len(m._cells()) == 11
    text = "\n".join("".join(c["source"]) for c in m._cells())
    for n in range(1, 7):
        assert f"### 6D.{n} " in text
    for phrase in ["脚注7", "局所", "可積分", "log", "C s_g", "相関座標", "印刷"]:
        assert phrase in text


@pytest.mark.parametrize(
    "mutation",
    [
        "status",
        "reference hash",
        "source missing",
        "source escape",
        "cases",
        "conditional",
        "pricing",
        "mc",
        "mc se zero",
        "truncated",
        "result hash",
        "max mc",
        "negative control",
        "reference resigned",
    ],
)
def test_consumer_rejects_resigned_result_mutations(tmp_path, monkeypatch, mutation):
    m = importlib.import_module("hullkit._multi_factor_lesson")
    record = json.loads(m._RECORD.read_text())
    if mutation == "status":
        record["status"] = "FAIL"
    elif mutation == "reference hash":
        record["reference_sha256"] = "0" * 64
    elif mutation == "source missing":
        del record["source_sha256"]["hullkit/src/hullkit/_multi_factor_martingales.py"]
    elif mutation == "source escape":
        record["source_sha256"]["../escape"] = "0" * 64
    elif mutation == "cases":
        record["api_cases"][0]["covariance"] += 0.01
    elif mutation == "conditional":
        record["api_conditional_means"][0]["g_mean"] += 0.1
    elif mutation == "pricing":
        record["pricing"][0]["price_g"] += 1
    elif mutation == "mc":
        record["pricing_mc"][0]["call_g"]["mean"] += 1
    elif mutation == "mc se zero":
        record["pricing_mc"][0]["call_g"]["se"] = 0
    elif mutation == "truncated":
        record["api_conditional_means"].pop()
    elif mutation == "result hash":
        record["result_sha256"] = "0" * 64
    elif mutation == "max mc":
        record["max_mc_se"] = 0
    elif mutation == "negative control":
        record["negative_controls"][0]["rejected"] = False
    else:
        import hashlib

        data = json.loads(m._DATA.read_text())
        data["cases"][0]["g_drifts"][0] += 0.01
        p = tmp_path / "reference.json"
        p.write_text(json.dumps(data))
        monkeypatch.setattr(m, "_DATA", p)
        record["reference_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    if mutation not in ["result hash", "truncated"]:
        record["result_sha256"] = m._result_digest(record)
    p = tmp_path / "record.json"
    p.write_text(json.dumps(record))
    monkeypatch.setattr(m, "_RECORD", p)
    with pytest.raises(ValueError):
        m._figures()


def test_price_figure_holds_f_market_fixed_while_choosing_three_g_loadings():
    m = importlib.import_module("hullkit._multi_factor_lesson")
    fig = m._figures()["factor_measure_price"]
    assert list(fig.data[0].x) == ["correlated_3", "correlated_3_negative_g", "correlated_3_zero_g"]
    data, record = m._load_reference()
    selected = data["cases"][1:4]
    assert all(
        r["f_loadings"] == selected[0]["f_loadings"]
        and r["correlation"] == selected[0]["correlation"]
        for r in selected
    )
    assert [r["price_q"] for r in record["pricing"][1:4]] == pytest.approx(
        [record["pricing"][1]["price_q"]] * 3
    )


@pytest.mark.parametrize(
    "target,field,mean",
    [
        ("pricing_mc", "call_g", -100.0),
        ("pricing_mc", "call_g", 109.05207105830452),
        ("pricing_mc", "density", 101.0),
        ("api_conditional_means", "mc", 101.25),
    ],
)
def test_consumer_rejects_jointly_resigned_mc_mean_se_and_summaries(
    tmp_path, monkeypatch, target, field, mean
):
    m = importlib.import_module("hullkit._multi_factor_lesson")
    record = json.loads(m._RECORD.read_text())
    item = record[target][1 if target == "pricing_mc" else 13][field]
    item["mean"], item["se"] = mean, 100.0
    item["z"] = abs(item["mean"] - item["reference"]) / item["se"]
    summaries = [v for row in record["pricing_mc"] for v in row.values() if isinstance(v, dict)]
    summaries += [row["mc"] for row in record["api_conditional_means"]]
    record["max_mc_se"] = max(row["z"] for row in summaries)
    record["result_sha256"] = m._result_digest(record)
    path = tmp_path / "jointly-resigned.json"
    path.write_text(json.dumps(record))
    monkeypatch.setattr(m, "_RECORD", path)
    with pytest.raises(ValueError):
        m._figures()


def test_consumer_accepts_teacher_roundoff_at_portable_numerical_tolerance(tmp_path, monkeypatch):
    import hashlib

    m = importlib.import_module("hullkit._multi_factor_lesson")
    data = json.loads(m._DATA.read_text())
    data["cases"][0]["g_drifts"][0] += 1e-15
    reference = tmp_path / "rounded-reference.json"
    reference.write_text(json.dumps(data))
    record = json.loads(m._RECORD.read_text())
    record["reference_sha256"] = hashlib.sha256(reference.read_bytes()).hexdigest()
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record))
    monkeypatch.setattr(m, "_DATA", reference)
    monkeypatch.setattr(m, "_RECORD", target)
    assert set(m._figures()) == KEYS


def test_consumer_accepts_fixed_seed_mean_and_se_roundoff(tmp_path, monkeypatch):
    import math

    m = importlib.import_module("hullkit._multi_factor_lesson")
    record = json.loads(m._RECORD.read_text())
    item = record["pricing_mc"][1]["call_g"]
    item["mean"] = math.nextafter(item["mean"], math.inf)
    item["se"] = math.nextafter(item["se"], math.inf)
    item["z"] = abs(item["mean"] - item["reference"]) / item["se"]
    summaries = [v for row in record["pricing_mc"] for v in row.values() if isinstance(v, dict)]
    summaries += [row["mc"] for row in record["api_conditional_means"]]
    record["max_mc_se"] = max(row["z"] for row in summaries)
    record["result_sha256"] = m._result_digest(record)
    target = tmp_path / "rounded-results.json"
    target.write_text(json.dumps(record))
    monkeypatch.setattr(m, "_RECORD", target)
    assert set(m._figures()) == KEYS
