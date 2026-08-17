"""`tools/` のうち、間違えると数字が黙って嘘になる部分。

ツールはパッケージの外（`tools/`）にあるのでファイルパスから読み込む。
ネットワークには触らない。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_as_of_is_the_last_completed_month():
    """当月の月足は月末値ではないので as-of にしない。

    Yahoo の月足は当月分も返す。その値は「今日までの終値」なので、そのまま
    as-of にすると月中の水準を「◯月末時点」と書いてしまう（実際に一度やった）。
    """
    qp = _load("quadrant_performance")
    assert qp.last_complete_month(pd.Timestamp("2026-08-17")) == pd.Period("2026-07", freq="M")
    assert qp.last_complete_month(pd.Timestamp("2026-08-31")) == pd.Period("2026-07", freq="M")
    assert qp.last_complete_month(pd.Timestamp("2026-01-01")) == pd.Period("2025-12", freq="M")


def test_fetch_prices_drops_the_unfinished_month_and_never_touches_the_network(tmp_path, monkeypatch):
    """as-of より後の足は落とす。キャッシュが as-of より新しければ取得もしない。"""
    qp = _load("quadrant_performance")
    cache = tmp_path / "prices_monthly.json"
    cache.write_text(
        json.dumps(
            {
                "fetched": "2026-08-17",
                "prices": {"1234": {"2022-11": 100.0, "2026-07": 150.0, "2026-08": 900.0}},
            }
        )
    )
    monkeypatch.setattr(qp, "CACHE", cache)

    def _fail(code):  # pragma: no cover - 呼ばれたらテスト失敗
        raise AssertionError(f"network hit for {code}")

    monkeypatch.setattr(qp, "_one", _fail)

    frame = qp.fetch_prices(["1234"], pd.Period("2026-07", freq="M"))
    assert frame.index.max() == pd.Period("2026-07", freq="M")
    assert 900.0 not in set(frame["1234"])


def test_a_cache_older_than_the_as_of_month_is_refetched(tmp_path, monkeypatch):
    """一度キャッシュに入った銘柄を二度と更新しない、という旧実装のバグの回帰テスト。"""
    qp = _load("quadrant_performance")
    cache = tmp_path / "prices_monthly.json"
    cache.write_text(
        json.dumps({"fetched": "2026-06-30", "prices": {"1234": {"2022-11": 100.0}}})
    )
    monkeypatch.setattr(qp, "CACHE", cache)

    asked: list[str] = []

    def _stub(code):
        asked.append(code)
        return code, {"2022-11": 100.0, "2026-07": 150.0}

    monkeypatch.setattr(qp, "_one", _stub)

    frame = qp.fetch_prices(["1234"], pd.Period("2026-07", freq="M"))
    assert asked == ["1234"]
    assert frame.loc[pd.Period("2026-07", freq="M"), "1234"] == 150.0
    assert json.loads(cache.read_text())["prices"]["1234"]["2026-07"] == 150.0
