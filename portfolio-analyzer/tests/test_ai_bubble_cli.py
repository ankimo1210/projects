"""The research CLI keeps holdings on the private side and leaves its inputs untouched (spec 8.1)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "research_ai_bubble.py"
SEMI, BOND, CASH = 98_765_432.0, 13_579_246.0, 11_111_111.0
TOTAL = SEMI + BOND + CASH
# Every way the private amounts are printed: raw, with separators, in 万円.
SECRETS = ("98765432", "98,765,432", "9,877", "13579246", "1,358", "123455789", "12,346")


@pytest.fixture(scope="module")
def cli():
    spec = importlib.util.spec_from_file_location("research_ai_bubble", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def flows(value: float) -> dict:
    return {"fcff": [value] * 10, "terminal_fcff": value}


@pytest.fixture
def run(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "run"
    write(root / "manifest.json", json.dumps({"as_of_utc": "2026-10-21T00:00:00Z", "inputs": []}))
    nvda = {
        "issuer_id": "NVDA",
        "layer": "design",
        "status": "評価",
        "r_j": 0.0932,
        "market": {"market_cap": 100.0, "ev_observed": 125.0},
        "flows": {"central": flows(10.0), "optimistic": flows(12.5), "stress": flows(8.0)},
        "valuation": {
            "v": "支持",
            "ev_ratio": {"central": 0.8},
            "implied_irr": {"status": "ok", "solutions": [0.095]},
        },
    }
    tsm = {"issuer_id": "TSM", "layer": "fab_memory", "status": "未評価: no quarterly filings"}
    write(
        root / "public" / "valuation.json",
        json.dumps({"as_of_utc": "2026-10-21T00:00:00Z", "companies": [nvda, tsm]}),
    )
    write(
        root / "public" / "funding.json",
        json.dumps({"companies": [{"issuer_id": "NVDA", "f": "弱める"}]}),
    )
    write(
        root / "public" / "history.json",
        json.dumps(
            {
                "label": "fixture",
                "companies": [{"issuer_id": "NVDA", "s": "混在", "industry": "Chips"}],
            }
        ),
    )
    write(
        root / "private" / "proxy-map.json",
        json.dumps(
            {
                "holdings": {
                    "SEMI": {"proxy": "^SOX", "currency": "USD", "kind": "semiconductor ETF"},
                    "BOND": {
                        "proxy": None,
                        "currency": "JPY",
                        "kind": "bond ETF: no registered proxy",
                    },
                    "CASH_JPY": {"proxy": "JPY", "currency": "JPY", "kind": "yen cash"},
                }
            }
        ),
    )
    days = ["2000-03-23", "2002-10-09", "2007-10-08", "2009-03-09", "2021-11-18", "2022-10-12"]
    write(
        root / "private" / "raw" / "proxies" / "closes.csv",
        "Date,^SOX\n"
        + "".join(
            f"{d},{v}\n" for d, v in zip(days, (1000, 300, 500, 200, 4000, 2200), strict=True)
        ),
    )
    h10 = "".join(
        f'<tr><th id="r1" headers="a1"> {d[8:]}-{m}-{d[2:4]} </th><td headers="a2 a1 r1"> {v} </td></tr>\n'
        for d, m, v in zip(
            days,
            ("MAR", "OCT", "OCT", "MAR", "NOV", "OCT"),
            (111.0, 123.0, 117.0, 98.0, 114.0, 146.0),
            strict=True,
        )
    )
    write(root / "public" / "raw" / "rates" / "h10-jpy-2000.htm", f"<table>{h10}</table>")
    holdings = write(
        tmp_path / "mtm-history.private.jsonl",
        json.dumps(
            {
                "as_of": "2026-10-20",
                "generated_at": "2026-10-21T07:30:01+09:00",
                "total_jpy": TOTAL,
                "positions": {
                    "global_broker:SEMI": {"value_jpy": SEMI},
                    "global_broker:BOND": {"value_jpy": BOND},
                },
                "accounts": {"global_broker": {"total_jpy": TOTAL}},
            }
        )
        + "\n",
    )
    reference = write(
        tmp_path / "analysis_reference.private.json",
        json.dumps(
            {
                "as_of": "2026-09-11",
                "instruments": [
                    {
                        "symbol": "SEMI",
                        "as_of": "2026-07-31",
                        "country_default": "米国",
                        "exposures": [
                            {
                                "group": "issuer",
                                "category": "Nvidia",
                                "weight": 0.2,
                                "theme": "AIサプライチェーン",
                            },
                            {
                                "group": "issuer",
                                "category": "Taiwan Semiconductor Manufacturing",
                                "weight": 0.1,
                                "theme": "AIサプライチェーン",
                            },
                        ],
                    },
                    {
                        "symbol": "BOND",
                        "as_of": "2026-08-13",
                        "country_default": "日本",
                        "exposures": [],
                    },
                ],
            }
        ),
    )
    return {"root": root, "holdings": holdings, "reference": reference}


def digests(paths: list[Path]) -> dict[Path, str]:
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_holdings_stay_private_and_inputs_are_untouched(cli, run):
    root = run["root"]
    inputs = [run["holdings"], run["reference"], *sorted(p for p in root.rglob("*") if p.is_file())]
    before = digests(inputs)
    public_before = {p for p in (root / "public").rglob("*") if p.is_file()}

    assert (
        cli.main(
            [
                "portfolio",
                str(root),
                "--holdings",
                str(run["holdings"]),
                "--reference",
                str(run["reference"]),
            ]
        )
        == 0
    )
    assert {p for p in (root / "public").rglob("*") if p.is_file()} == public_before
    assert cli.main(["report", str(root)]) == 0

    assert digests(inputs) == before
    private = (root / "private" / "portfolio-impact.md").read_text() + (
        root / "private" / "portfolio-impact.json"
    ).read_text()
    assert "9,877" in private and "98765432" in private  # the search can see the amounts
    for path in (root / "public").rglob("*"):
        if path.is_file():
            text = path.read_text(errors="replace")
            assert not [s for s in SECRETS if s in text], path


def test_the_private_result_reprices_the_evaluated_issuer_and_keeps_the_rest_unevaluated(cli, run):
    root = run["root"]
    cli.main(
        [
            "portfolio",
            str(root),
            "--holdings",
            str(run["holdings"]),
            "--reference",
            str(run["reference"]),
        ]
    )
    out = json.loads((root / "private" / "portfolio-impact.json").read_text())
    issuers = {r["issuer_id"]: r for r in out["idiosyncratic"]["issuers"]}
    assert issuers["NVDA"]["status"] == "ok" and issuers["NVDA"]["change"]["central"] == 0.0
    assert issuers["NVDA"]["change"]["stress"] < 0
    assert issuers["TSM"]["status"] == "unevaluated"
    assert out["ai_exposure"]["total_jpy"] == pytest.approx(0.3 * SEMI)
    assert out["ai_exposure"]["evaluated_share"] == pytest.approx(2 / 3)
    assert out["ai_exposure"]["unclassified_fund_remainder_jpy"] == pytest.approx(0.7 * SEMI + BOND)
    dotcom = next(e for e in out["systematic"] if e["id"] == "dotcom")
    assert dotcom["impact_jpy"] == pytest.approx(SEMI * (300 * 123.0) / (1000 * 111.0) - SEMI)
    assert dotcom["complete"] is False and "BOND" in dotcom["reason"]
    assert out["unproxied"] == ["BOND"]
