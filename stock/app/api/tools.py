"""Claude tool definitions and implementations for stockkit chat."""

from __future__ import annotations

import os
from typing import Any

TOOL_DEFINITIONS = [
    {
        "name": "get_price_data",
        "description": (
            "株価・ETF・指数・先物・FX・暗号資産のOHLCV日次データを取得する。\n"
            "symbol例: AAPL, NVDA, 6857.T（アドバンテスト）, ^N225（日経225）, "
            "1306.T（TOPIX ETF）, ^GSPC（S&P500）, ES=F（S&P先物）, NQ=F（NASDAQ先物）, "
            "GC=F（金先物）, CL=F（WTI）, BZ=F（ブレント）, HG=F（銅）, "
            "JPY=X（ドル円）, EURUSD=X, DX-Y.NYB（DXY）, BTC-USD, ETH-USD, "
            "^VIX, TLT, QQQ, GLD, 1343.T（J-REIT ETF）, ^HSI（香港ハンセン）"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "yfinance形式のティッカーシンボル",
                },
                "period": {
                    "type": "string",
                    "description": "取得期間: 1mo / 3mo / 6mo / 1y / 2y / 5y / max",
                    "default": "1y",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_macro",
        "description": (
            "FREDのマクロ経済時系列データを取得する。\n"
            "主要series_id:\n"
            "  US: CPIAUCSL（米CPI月次）, PCEPILFE（コアPCE）, PAYEMS（NFP雇用）, "
            "UNRATE（米失業率）, FEDFUNDS（FF金利）, GDP（米GDP四半期）, "
            "DGS10（米10Y利回り日次）, DGS2（米2Y利回り）, T10Y2Y（逆イールド）, "
            "RSAFS（小売売上高）, UMCSENT（ミシガン消費者信頼感）, M2SL（米M2）, "
            "DCOILWTICO（WTI日次）, VIXCLS（VIX）\n"
            "  JP: IRLTLT01JPM156N（JGB10Y月次）, XTEXVA01JPM667S（日本輸出）, "
            "XTIMVA01JPM667S（日本輸入）, LRUNTTTTJPM156S（日本失業率）, "
            "DEXJPUS（ドル円日次）\n"
            "  FX: DEXUSEU（EUR/USD）, DEXUSUK（GBP/USD）, DEXCHUS（USD/CNY）"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "string",
                    "description": "FREDシリーズID",
                },
                "start": {
                    "type": "string",
                    "description": "取得開始日 YYYY-MM-DD（省略時は最大）",
                },
            },
            "required": ["series_id"],
        },
    },
    {
        "name": "get_jp_cpi",
        "description": (
            "日本のCPI（消費者物価指数）月次データをe-Stat APIから取得する。"
            "2020年基準=100。1970年〜2026年3月まで利用可能。引数は省略可。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "string",
                    "description": "取得開始日 YYYY-MM-DD（省略時は全期間）",
                },
            },
        },
    },
    {
        "name": "search_fred",
        "description": (
            "FREDのシリーズをキーワード検索してseries_idと説明を返す。"
            "「日本の生産指数のシリーズIDを調べて」のような用途に使う。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索キーワード（英語推奨）",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大取得件数（デフォルト5）",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "execute_python",
        "description": (
            "Pythonコードを実行して分析・グラフ作成を行う。\n"
            "利用可能なオブジェクト: pd（pandas）, np（numpy）, go（plotly.graph_objects）, "
            "px（plotly.express）, get_prices(), get_macro(), get_jp_cpi()\n"
            "グラフはfig.show()で表示（自動キャプチャ）。printで数値を出力。\n"
            "グラフのタイトル・軸ラベルは日本語で記述すること。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "実行するPythonコード",
                },
            },
            "required": ["code"],
        },
    },
]


import threading
_thread_local = threading.local()


def get_captured_figures() -> list[str]:
    """Return figures captured by the last execute_python call (this thread)."""
    return list(getattr(_thread_local, "figures", []))


def clear_captured_figures() -> None:
    _thread_local.figures = []


def execute_tool(name: str, inputs: dict[str, Any]) -> str:
    """Dispatch a tool call and return the result as a string."""
    try:
        if name == "get_price_data":
            return _get_price_data(**inputs)
        if name == "get_macro":
            return _get_macro(**inputs)
        if name == "get_jp_cpi":
            return _get_jp_cpi(**inputs)
        if name == "search_fred":
            return _search_fred(**inputs)
        if name == "execute_python":
            return _execute_python(**inputs)
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error ({name}): {e}"


# ---------- implementations ----------

def _get_price_data(symbol: str, period: str = "1y") -> str:
    from stockkit.data import get_prices
    df = get_prices(symbol, period=period, source="yfinance")
    if df.empty:
        return f"データなし: {symbol}"
    return (
        f"{symbol} の価格データ取得完了。"
        f"期間: {df.index[0].date()} 〜 {df.index[-1].date()}, "
        f"{len(df)}日分。最新終値: {df['close'].iloc[-1]:.4g}"
    )


def _get_macro(series_id: str, start: str | None = None) -> str:
    from stockkit.data import get_macro
    s = get_macro(series_id, start=start)
    s = s.dropna()
    if s.empty:
        return f"データなし: {series_id}"
    return (
        f"FRED {series_id} 取得完了。"
        f"期間: {s.index[0].date()} 〜 {s.index[-1].date()}, "
        f"{len(s)}件。最新値: {s.iloc[-1]:.4g}"
    )


def _get_jp_cpi(start: str | None = None) -> str:
    from stockkit.data import get_jp_cpi
    s = get_jp_cpi(start=start)
    if s.empty:
        return "Japan CPI データなし"
    return (
        f"日本CPI取得完了（e-Stat）。"
        f"期間: {s.index[0].date()} 〜 {s.index[-1].date()}, "
        f"{len(s)}件。最新値: {s.iloc[-1]:.4g}"
    )


def _search_fred(query: str, limit: int = 5) -> str:
    from fredapi import Fred
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        return "FRED_API_KEY が設定されていません"
    fred = Fred(api_key=api_key)
    results = fred.search(query, limit=limit)
    if results is None or results.empty:
        return f"'{query}' に一致するシリーズが見つかりませんでした"
    lines = [f"FREDシリーズ検索結果（クエリ: {query}）:"]
    for sid, row in results.iterrows():
        lines.append(f"  {sid}: {row.get('title', '')}")
    return "\n".join(lines)


def _execute_python(code: str) -> str:
    from api.sandbox import run
    result = run(code)
    # Store figures in thread-local so claude_agent can collect them
    _thread_local.figures = result.get("figures", [])
    parts: list[str] = []
    if result["output"]:
        parts.append(f"[出力]\n{result['output'].strip()}")
    if result["figures"]:
        parts.append(f"[グラフ] {len(result['figures'])}件生成")
    if result["error"]:
        parts.append(f"[エラー]\n{result['error']}")
    if not parts:
        parts.append("(出力なし)")
    return "\n".join(parts)
