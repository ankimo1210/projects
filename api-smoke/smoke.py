"""Compare native structured outputs and a real Python tool round trip without SDKs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

PORTFOLIO_ID = "fictional-jpy-bonds-v1"
BONDS = [
    {"bond_id": "JGB_2Y", "market_value_jpy": 60000000, "rate_dv01": 12000, "spread_dv01": 0},
    {"bond_id": "JGB_10Y", "market_value_jpy": 100000000, "rate_dv01": 85000, "spread_dv01": 0},
    {"bond_id": "CORP_5Y", "market_value_jpy": 80000000, "rate_dv01": 36000, "spread_dv01": 32000},
]
SCENARIO = {"portfolio_id": PORTFOLIO_ID, "rate_shock_bp": 25, "spread_shock_bp": 40}
FACTORS = ["interest_rate", "credit_spread"]
CHECK_NAMES = ["structured_json", "tool_calling", "multi_step"]
ENDPOINTS = {
    "openai": "https://api.openai.com/v1/responses",
    "anthropic": "https://api.anthropic.com/v1/messages",
}


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


TOOL_SCHEMA = object_schema(
    {
        "portfolio_id": {"type": "string", "enum": [PORTFOLIO_ID]},
        "rate_shock_bp": {"type": "integer"},
        "spread_shock_bp": {"type": "integer"},
    }
)
REPORT_SCHEMA = object_schema(
    {
        "currency": {"type": "string", "enum": ["JPY"]},
        "total_pnl_jpy": {"type": "integer"},
        "rate_pnl_jpy": {"type": "integer"},
        "spread_pnl_jpy": {"type": "integer"},
        "positions": {
            "type": "array",
            "items": object_schema(
                {
                    "bond_id": {"type": "string", "enum": [b["bond_id"] for b in BONDS]},
                    "pnl_jpy": {"type": "integer"},
                }
            ),
        },
        "risk_factors": {
            "type": "array",
            "items": object_schema(
                {
                    "factor": {"type": "string", "enum": FACTORS},
                    "shock_bp": {"type": "integer"},
                    "pnl_jpy": {"type": "integer"},
                    "impact": {"type": "string", "enum": ["loss", "gain", "flat"]},
                }
            ),
        },
        "dominant_risk_factor": {"type": "string", "enum": FACTORS},
        "worst_bond_id": {"type": "string", "enum": [b["bond_id"] for b in BONDS]},
        "comment_ja": {"type": "string"},
        "explanation_ja": object_schema(
            {name: {"type": "string"} for name in ["total", *FACTORS, "concentration"]}
        ),
    }
)
Draft202012Validator.check_schema(REPORT_SCHEMA)
REPORT_VALIDATOR = Draft202012Validator(REPORT_SCHEMA)
TOOL_VALIDATOR = Draft202012Validator(TOOL_SCHEMA)

PROMPT = (
    "架空の円建て債券ポートフォリオのリスク分析をしてください。Web検索は使いません。"
    "DV01の単位は円/bpです。各要因のP&Lは-DV01×shock_bpで、凸性・キャリー・為替は無視します。"
    "calculate_pnlツールを必要と判断すれば利用できます。利用するかはあなたが判断してください。"
    "指定スキーマのJSONで、合計・金利・信用スプレッドの損益、全銘柄の損益、"
    "各リスク要因、最大リスク要因、最大損失銘柄、日本語コメントと日本語説明を返してください。"
    "positionsには各銘柄を1回ずつ、risk_factorsには2要因を1回ずつ含めます。"
    "explanation_jaのtotal・interest_rate・credit_spreadは、それぞれ該当する損益を"
    "符号付きの整数円（負数は必ずマイナス符号付き、カンマなし）で書き、"
    "損失・利益・変化なしの該当する語を含めてください。"
    "concentrationには最大損失銘柄のIDと、その符号付き整数円の損益と損失の語を含めてください。"
    "comment_jaには日本語で簡単な総括を記載してください。"
    "入力データ: " + json.dumps({"bonds": BONDS, "scenario": SCENARIO}, ensure_ascii=False)
)


def calculate_pnl(portfolio_id, rate_shock_bp, spread_shock_bp):
    """Fixed-DV01 linear P&L, in JPY; no pricing or investment assumptions are hidden."""
    if portfolio_id != PORTFOLIO_ID:
        raise ValueError("Unknown portfolio")
    shocks = [rate_shock_bp, spread_shock_bp]
    for shock in shocks:
        if (
            isinstance(shock, bool)
            or not isinstance(shock, (int, float))
            or not math.isfinite(shock)
            or shock != int(shock)
        ):
            raise ValueError("Shocks must be finite integral basis points")
    rate_shock_bp, spread_shock_bp = map(int, shocks)
    rate_pnl = -sum(b["rate_dv01"] for b in BONDS) * rate_shock_bp
    spread_pnl = -sum(b["spread_dv01"] for b in BONDS) * spread_shock_bp
    positions = [
        {
            "bond_id": bond["bond_id"],
            "pnl_jpy": -bond["rate_dv01"] * rate_shock_bp - bond["spread_dv01"] * spread_shock_bp,
        }
        for bond in BONDS
    ]
    factors = [
        {
            "factor": factor,
            "shock_bp": shock,
            "pnl_jpy": pnl,
            "impact": "loss" if pnl < 0 else "gain" if pnl > 0 else "flat",
        }
        for factor, shock, pnl in zip(
            FACTORS, [rate_shock_bp, spread_shock_bp], [rate_pnl, spread_pnl], strict=True
        )
    ]
    return {
        "currency": "JPY",
        "total_pnl_jpy": rate_pnl + spread_pnl,
        "rate_pnl_jpy": rate_pnl,
        "spread_pnl_jpy": spread_pnl,
        "positions": positions,
        "risk_factors": factors,
        "dominant_risk_factor": max(factors, key=lambda item: abs(item["pnl_jpy"]))["factor"],
        "worst_bond_id": min(positions, key=lambda item: item["pnl_jpy"])["bond_id"],
    }


def schema_issues(report):
    return [
        f"{'/'.join(map(str, error.absolute_path)) or '$'}: {error.message}"
        for error in REPORT_VALIDATOR.iter_errors(report)
    ]


def narrative_contract(expected):
    """Only certify complete, bounded Japanese clauses; unknown prose needs review."""
    worst = expected["worst_bond_id"]
    worst_pnl = next(p["pnl_jpy"] for p in expected["positions"] if p["bond_id"] == worst)
    prefixes = {
        "total": ["合計損益は"],
        "interest_rate": ["金利要因の損益は", "金利による損益は"],
        "credit_spread": ["信用スプレッド要因の損益は", "信用スプレッドによる損益は"],
        "concentration": [f"最大損失銘柄は{worst}で、損益は"],
    }
    numbers = {
        "total": expected["total_pnl_jpy"],
        "interest_rate": expected["rate_pnl_jpy"],
        "credit_spread": expected["spread_pnl_jpy"],
        "concentration": worst_pnl,
    }
    allowed = {}
    for field, number in numbers.items():
        direction = "損失" if number < 0 else "利益" if number > 0 else "変化なし"
        allowed[field] = {
            f"{prefix}{number}円{join}{direction}です。"
            for prefix in prefixes[field]
            for join in ["の", "で"]
        }
    # The concentration prefix itself already states that this is the maximum loss.
    if worst_pnl < 0:
        allowed["concentration"].add(f"{prefixes['concentration'][0]}{worst_pnl}円です。")
    labels = {"interest_rate": "金利", "credit_spread": "信用スプレッド"}
    dominant = expected["dominant_risk_factor"]
    other = next(factor for factor in FACTORS if factor != dominant)
    total = expected["total_pnl_jpy"]
    direction = "損失" if total < 0 else "利益" if total > 0 else "変化なし"
    comments = {
        f"合計{abs(total)}円の{direction}です。{labels[dominant]}リスクの寄与が"
        f"{labels[other]}リスクを上回り、最大損失銘柄は{worst}です。"
    }
    if expected["rate_pnl_jpy"] < 0 and expected["spread_pnl_jpy"] < 0:
        comments.add("金利上昇と信用スプレッド拡大の双方による損失が生じます。")
    return allowed, comments


def consistency_issues(report, expected):
    if schema_issues(report):
        return ["Cannot check consistency of a schema-invalid report"]
    errors = []
    for key, value in expected.items():
        actual = report[key]
        if key in {"positions", "risk_factors"}:
            identity = "bond_id" if key == "positions" else "factor"
            if len(actual) != len(value) or len({item[identity] for item in actual}) != len(value):
                errors.append(f"{key}: missing or duplicate entries")
            elif sorted(actual, key=lambda item: item[identity]) != sorted(
                value, key=lambda item: item[identity]
            ):
                errors.append(f"{key}: arithmetic, shock, or direction mismatch")
        elif actual != value:
            errors.append(f"{key}: expected {value}, got {actual}")
    allowed, comments = narrative_contract(expected)
    for field, clauses in allowed.items():
        text = report["explanation_ja"][field].strip().replace(",", "").replace("−", "-")
        if text not in clauses:
            errors.append(
                f"explanation_ja/{field}: outside verified Japanese clauses; manual review required"
            )
    if report["comment_ja"].strip() not in comments:
        errors.append("comment_ja: outside verified Japanese summaries; manual review required")
    return errors


def execute_tool(name, arguments):
    if name != "calculate_pnl":
        raise ValueError("Only calculate_pnl is permitted")
    errors = list(TOOL_VALIDATOR.iter_errors(arguments))
    if errors or arguments != SCENARIO:
        raise ValueError("Tool arguments do not match the requested portfolio and shocks")
    return calculate_pnl(**arguments)


def redact(value, secrets):
    if isinstance(value, dict):
        return {redact(key, secrets): redact(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", value)
    return value


def request_body(provider, model):
    tool_description = (
        "Compute exact JPY P&L for the provided fictional portfolio using fixed DV01 exposures."
    )
    if provider == "openai":
        return {
            "model": model,
            "input": [{"role": "user", "content": PROMPT}],
            "reasoning": {"effort": "none"},
            "max_output_tokens": 1400,
            "store": False,
            "tools": [
                {
                    "type": "function",
                    "name": "calculate_pnl",
                    "description": tool_description,
                    "parameters": TOOL_SCHEMA,
                    "strict": True,
                }
            ],
            "parallel_tool_calls": False,
            "tool_choice": "auto",
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "bond_risk",
                    "schema": REPORT_SCHEMA,
                    "strict": True,
                }
            },
        }
    return {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "thinking": {"type": "disabled"},
        "max_tokens": 1400,
        "tools": [
            {
                "name": "calculate_pnl",
                "description": tool_description,
                "input_schema": TOOL_SCHEMA,
                "strict": True,
            }
        ],
        "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        "output_config": {"format": {"type": "json_schema", "schema": REPORT_SCHEMA}},
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post_json(url, headers, body):
    """One HTTPS request, no retry or redirect; never include headers in its record."""
    start = time.perf_counter()
    request = urllib.request.Request(
        url, data=json.dumps(body, ensure_ascii=False).encode(), headers=headers, method="POST"
    )
    try:
        try:
            response = urllib.request.build_opener(NoRedirect()).open(request, timeout=45)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("API response exceeds the 1 MiB safety cap")
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = {"error": "API returned a non-JSON response"}
            return {
                "http_status": response.code,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "request_id": response.headers.get("x-request-id")
                or response.headers.get("request-id"),
                "response": parsed,
            }
    except (OSError, ValueError) as error:
        return {
            "http_status": None,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "response": {"error": {"message": str(error)}},
        }


def extract_calls(provider, response):
    if provider == "openai":
        return [item for item in response.get("output", []) if item.get("type") == "function_call"]
    return [item for item in response.get("content", []) if item.get("type") == "tool_use"]


def final_text(provider, response):
    if provider == "openai":
        parts = [
            part
            for item in response.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        ]
    else:
        parts = [part for part in response.get("content", []) if part.get("type") == "text"]
    return "".join(part.get("text", "") for part in parts)


def completed(provider, response):
    return (
        response.get("status") == "completed"
        if provider == "openai"
        else response.get("stop_reason") == "end_turn"
    )


def error_advice(status):
    return {
        400: "Inspect the recorded parameter/schema error and the selected model's supported API fields; do not retry unchanged.",
        401: "Check the inference key's validity and provider; do not print the key.",
        403: "Check model and project inference permissions.",
        429: "Inspect whether the error is a rate or billing limit; no automatic retry is performed.",
    }.get(
        status, "Inspect the saved response or network error before considering a new paid request."
    )


def run_provider(provider, api_key, model, transport=post_json):
    start = time.perf_counter()
    result = {
        "provider": provider,
        "model": model,
        "checks": dict.fromkeys(CHECK_NAMES, "FAIL"),
        "requests": [],
        "tool_trace": [],
        "failures": [],
        "report": None,
        "cost_estimate_usd": None,
        "cost_estimate_note": "Not estimated: official unit prices were not verified in this no-Web run.",
    }
    headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    if provider == "anthropic":
        headers["anthropic-version"] = "2026-10-21"

    def send(body):
        record = transport(ENDPOINTS[provider], headers, body)
        result["requests"].append(
            {"phase": len(result["requests"]) + 1, "request_body": copy.deepcopy(body), **record}
        )
        if record["http_status"] != 200:
            raise ValueError(
                f"HTTP {record['http_status']}: {json.dumps(record['response'], ensure_ascii=False)}"
            )
        response = record["response"]
        if not isinstance(response, dict):
            raise ValueError("API response must be a JSON object")
        usage = response.get("usage")
        if not isinstance(usage, dict) or any(
            type(usage.get(name)) is not int or usage[name] < 0
            for name in ["input_tokens", "output_tokens"]
        ):
            raise ValueError("API usage must contain nonnegative integer input/output token counts")
        return response

    try:
        body = request_body(provider, model)
        response = send(body)
        calls = extract_calls(provider, response)
        tool_returned = False
        if calls:
            if (provider == "openai" and response.get("status") != "completed") or (
                provider == "anthropic" and response.get("stop_reason") != "tool_use"
            ):
                raise ValueError(
                    "Initial tool-call response is incomplete or truncated; tool not executed"
                )
            if len(calls) != 1:
                raise ValueError("Expected one calculate_pnl call; refused multiple tool calls")
            call = calls[0]
            arguments = json.loads(call["arguments"]) if provider == "openai" else call["input"]
            calculation_start = time.perf_counter()
            tool_result = execute_tool(call.get("name"), arguments)
            result["tool_trace"].append(
                {
                    "name": call["name"],
                    "arguments": arguments,
                    "python_result": tool_result,
                    "latency_ms": round((time.perf_counter() - calculation_start) * 1000, 3),
                }
            )
            if provider == "openai":
                body["input"] += response["output"] + [
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(tool_result, ensure_ascii=False),
                    }
                ]
                body["tool_choice"] = "none"
            else:
                body["messages"] += [
                    {"role": "assistant", "content": response["content"]},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": call["id"],
                                "content": json.dumps(tool_result, ensure_ascii=False),
                            }
                        ],
                    },
                ]
                body["tool_choice"] = {"type": "none"}
            response = send(body)
            tool_returned = not extract_calls(provider, response)
        text = final_text(provider, response)
        if not completed(provider, response) or not text:
            raise ValueError(
                "Final response is missing or truncated; inspect status/stop_reason and token cap"
            )
        if tool_returned:
            result["checks"]["tool_calling"] = "PASS"
        else:
            result["failures"].append(
                {
                    "cause": "Model did not choose calculate_pnl with automatic tool selection",
                    "fix": "Review task and tool description; do not mislabel a forced tool call as automatic selection.",
                }
            )
        report = json.loads(text)
        result["report"] = report
        errors = schema_issues(report)
        if not errors:
            result["checks"]["structured_json"] = "PASS"
        else:
            result["failures"].append(
                {
                    "cause": "; ".join(errors),
                    "fix": "Inspect native output format and common schema.",
                }
            )
        errors = consistency_issues(report, calculate_pnl(**SCENARIO))
        if not errors and tool_returned:
            result["checks"]["multi_step"] = "PASS"
        elif errors:
            result["failures"].append(
                {
                    "cause": "; ".join(errors),
                    "fix": "Inspect the final report against Python P&L; keep the oracle unchanged.",
                }
            )
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        status = result["requests"][-1]["http_status"] if result["requests"] else None
        result["failures"].append({"cause": str(error), "fix": error_advice(status)})
    usage_records = [
        record["response"].get("usage") if isinstance(record["response"], dict) else None
        for record in result["requests"]
    ]
    result["usage"] = {}
    for name in ["input_tokens", "output_tokens"]:
        values = [usage.get(name) if isinstance(usage, dict) else None for usage in usage_records]
        result["usage"][name] = sum(value for value in values if type(value) is int and value >= 0)
    result["usage"]["complete"] = bool(usage_records) and all(
        isinstance(usage, dict)
        and all(
            type(usage.get(name)) is int and usage[name] >= 0
            for name in ["input_tokens", "output_tokens"]
        )
        for usage in usage_records
    )
    result["http_latency_ms"] = round(sum(r["latency_ms"] for r in result["requests"]), 2)
    result["wall_latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return redact(result, [api_key])


def summary_markdown(results):
    lines = [
        "# API スモークテスト結果",
        "",
        f"実行日時（UTC）: {results['created_at_utc']}",
        "",
        "| API / model | JSON | Tool Calling | 複数ステップ | HTTP回数 | HTTP合計秒 | 入力token | 出力token |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for result in results["providers"]:
        checks, usage = result["checks"], result["usage"]
        lines.append(
            f"| {result['provider']} / {result['model']} | {checks['structured_json']} | "
            f"{checks['tool_calling']} | {checks['multi_step']} | {len(result['requests'])} | "
            f"{result['http_latency_ms'] / 1000:.3f} | {usage['input_tokens']} | {usage['output_tokens']} |"
        )
    lines += [
        "",
        "料金は公式単価を確認しない条件のため未算出。各リクエストの生のusageはresults.jsonを参照。",
        "日本語説明は数値入りの限定した句形で照合し、未知の表現は手動確認が必要なFAILとする。一般的な文章力の評価ではない。",
    ]
    for result in results["providers"]:
        lines += ["", f"## {result['provider']}", ""]
        if result["report"] and not schema_issues(result["report"]):
            lines.append(result["report"]["comment_ja"])
            lines.extend(f"- {text}" for text in result["report"]["explanation_ja"].values())
        for failure in result["failures"]:
            lines += [f"- 原因: {failure['cause']}", f"- 修正案: {failure['fix']}"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openai-model", default="gpt-6-luna")
    parser.add_argument("--anthropic-model", default="claude-haiku-5-5")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--keys-stdin", action="store_true", help="Read credential JSON privately from stdin"
    )
    args = parser.parse_args()
    names = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    try:
        keys = (
            json.load(sys.stdin)
            if args.keys_stdin
            else {name: os.getenv(name, "") for name in names}
        )
        if not isinstance(keys, dict) or any(
            not isinstance(keys.get(name), str) or not keys[name].strip() for name in names
        ):
            raise ValueError("Both OPENAI_API_KEY and ANTHROPIC_API_KEY must be supplied")
        keys = {name: keys[name].strip() for name in names}
    except (ValueError, TypeError):
        parser.exit(
            2,
            "Supply both API keys through environment variables or private stdin; no keys were printed.\n",
        )
    root = Path(__file__).resolve().parent.parent
    stamp = datetime.now(UTC)
    output = args.output_dir or root / "_data" / "api-smoke" / stamp.strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(run_provider, "openai", keys[names[0]], args.openai_model),
            pool.submit(run_provider, "anthropic", keys[names[1]], args.anthropic_model),
        ]
        providers = [future.result() for future in futures]
    results = redact(
        {
            "created_at_utc": stamp.isoformat(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
            "portfolio": BONDS,
            "scenario": SCENARIO,
            "response_schema": REPORT_SCHEMA,
            "python_reference": calculate_pnl(**SCENARIO),
            "providers": providers,
        },
        list(keys.values()),
    )
    serialized = json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False)
    summary = summary_markdown(results)
    if any(secret in serialized or secret in summary for secret in keys.values()):
        parser.exit(2, "Refused to save an artifact containing credential material.\n")
    (output / "results.json").write_text(serialized + "\n", encoding="utf-8")
    (output / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Saved: {output}")
    return 0 if all(value == "PASS" for p in providers for value in p["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
