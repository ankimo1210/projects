"""Claude API agent with tool_use loop for investment analysis."""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic
from dotenv import load_dotenv

from api.tools import TOOL_DEFINITIONS, execute_tool, get_captured_figures, clear_captured_figures

_MODEL = "claude-sonnet-4-6"
_MAX_ROUNDS = 10

_SYSTEM = """あなたは stockkit に組み込まれた投資分析 AI アシスタントです。
ユーザーの言語に合わせて返答してください（日本語で聞かれたら日本語で答える）。

## 利用可能なツール

- **get_price_data**: 株価・ETF・先物・FX・暗号資産の日次OHLCVデータ取得
- **get_macro**: FRED のマクロ経済指標取得（米CPI・雇用・金利・日本輸出入等）
- **get_jp_cpi**: 日本CPI月次データ（e-Stat、1970年〜最新）
- **search_fred**: FRED シリーズをキーワード検索して series_id を発見
- **execute_python**: Python コードを実行して分析・グラフ作成

## 主な取得可能データ

**日本市場**
- 日経225: ^N225 / TOPIX ETF: 1306.T / JPX-400 ETF: 1592.T
- J-REIT ETF: 1343.T / マザーズETF: 2516.T
- 個別株: 6857.T（アドバンテスト）, 7203.T（トヨタ）など4桁.T形式

**米国市場**
- 指数: ^GSPC（S&P500）, ^IXIC（NASDAQ）, ^DJI, ^RUT, ^VIX
- 先物: ES=F（S&P）, NQ=F（NASDAQ）
- ETF: SPY, QQQ, IWM, TLT（20Y債）, IEF, GLD, SLV, HYG, LQD

**コモディティ先物**
- GC=F（金）, SI=F（銀）, CL=F（WTI）, BZ=F（ブレント）
- NG=F（天然ガス）, HG=F（銅）, ZC=F（コーン）, ZW=F（小麦）

**FX**
- JPY=X（USD/JPY）, EURUSD=X, GBPUSD=X, AUDUSD=X, DX-Y.NYB（DXY）

**暗号資産**: BTC-USD, ETH-USD

**海外指数**: ^STOXX50E, ^GDAXI（DAX）, ^FTSE, ^HSI（ハンセン）, ^KS11（KOSPI）

**FRED マクロ（主要）**
- 米: CPIAUCSL, PCEPILFE, PAYEMS, UNRATE, FEDFUNDS, DGS10, DGS2, T10Y2Y
- 日: IRLTLT01JPM156N（JGB10Y）, XTEXVA01JPM667S（輸出）, LRUNTTTTJPM156S（失業率）
- FX: DEXJPUS（ドル円日次）, DEXUSEU, DCOILWTICO（WTI日次）

## コード実行のガイドライン

execute_python を使う場合：
- plotly で可視化し `fig.show()` で出力する（自動キャプチャされる）
- グラフのタイトル・軸ラベルは日本語で書く
- `pd`, `np`, `go`, `px`, `get_prices()`, `get_macro()`, `get_jp_cpi()` が利用可能
- `print()` で数値・テキスト結果を出力する

## 分析スタイル

1. まず必要なデータを取得ツールで取得する
2. execute_python でデータを組み合わせて分析・可視化する
3. 結果を日本語で簡潔に解説する
4. 不明なシリーズIDは search_fred で調べてから取得する
"""


def run(conversation: list[dict], user_message: str) -> dict[str, Any]:
    """Run Claude agent loop. Returns {text, figures, code_blocks}."""
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が .env に設定されていません")

    client = anthropic.Anthropic(api_key=api_key)

    messages = list(conversation)
    messages.append({"role": "user", "content": user_message})

    figures: list[str] = []
    code_blocks: list[str] = []
    final_text = ""

    for _ in range(_MAX_ROUNDS):
        response = client.messages.create(
            model=_MODEL,
            max_tokens=8192,
            system=_SYSTEM,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Collect assistant message content
        tool_calls = []
        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if text_parts:
            final_text = "\n".join(text_parts)

        # Append assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn" or not tool_calls:
            break

        # Execute tool calls and collect results
        tool_results = []
        for tc in tool_calls:
            inputs = tc.input if isinstance(tc.input, dict) else {}

            # Track code for display
            if tc.name == "execute_python":
                code_blocks.append(inputs.get("code", ""))
                clear_captured_figures()

            result_str = execute_tool(tc.name, inputs)

            if tc.name == "execute_python":
                figures.extend(get_captured_figures())

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})

    return {
        "text": final_text,
        "figures": figures,
        "code_blocks": code_blocks,
    }


