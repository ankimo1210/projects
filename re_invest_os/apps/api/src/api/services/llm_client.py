"""LLM クライアント抽象。

責務:
- provider 切替 (ollama / anthropic / openai)
- JSON 強制出力
- リトライ (1回)
- prompt id / model / latency を記録した呼び出し meta を返す

呼び出し側はこれだけ使う:
    result = chat_json(prompt, vars={"document_text": "..."}, model="qwen2.5:7b")
    result.data         # dict
    result.meta.model   # 実際使ったモデル
    result.meta.prompt_id
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from api.services.prompts import Prompt


class LLMError(RuntimeError):
    """LLM 呼び出し / JSON パース失敗の共通例外。"""


@dataclass(frozen=True)
class CallMeta:
    provider: str
    model: str
    prompt_id: str  # "classify_document:v1"
    latency_ms: int
    attempts: int = 1
    raw_response_snippet: str = ""  # デバッグ用 (先頭500文字)


@dataclass(frozen=True)
class LLMResult:
    data: dict[str, Any]
    meta: CallMeta
    warnings: list[str] = field(default_factory=list)


class _Provider(Protocol):
    name: str

    def complete_json(
        self,
        system: str,
        user: str,
        model: str,
        schema: dict[str, Any] | None,
        timeout_s: float,
    ) -> tuple[str, dict[str, Any]]:
        """raw text と (provider 固有の) call info を返す。"""


# ---------- Ollama ----------


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def complete_json(
        self,
        system: str,
        user: str,
        model: str,
        schema: dict[str, Any] | None,
        timeout_s: float,
    ) -> tuple[str, dict[str, Any]]:
        # format="json" で有効 JSON を保証する。
        # schema を format に渡すと Ollama の grammar 制約で optional フィールドが
        # 落ちる問題があるため、スキーマはプロンプト側で誘導し format は常に "json" のみ。
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0},
            "format": "json",
        }
        _ = schema  # 将来 Anthropic/OpenAI では使う

        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            body = resp.json()

        content = body.get("message", {}).get("content", "")
        return content, {"eval_count": body.get("eval_count"), "model": body.get("model")}


# ---------- Anthropic ----------


_ANTHROPIC_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class AnthropicProvider:
    name = "anthropic"

    def complete_json(
        self,
        system: str,
        user: str,
        model: str,
        schema: dict[str, Any] | None,
        timeout_s: float,
    ) -> tuple[str, dict[str, Any]]:
        import anthropic  # lazy import — not required when using Ollama

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY が設定されていません。"
                "LLM_PROVIDER=anthropic 使用時は環境変数が必要です。"
            )
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=timeout_s,
        )
        content = msg.content[0].text if msg.content else ""
        return content, {
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        }


# ---------- factory ----------

_PROVIDERS: dict[str, _Provider] = {}


def _provider() -> _Provider:
    prov = os.getenv("LLM_PROVIDER", "ollama").lower()
    if prov not in _PROVIDERS:
        if prov == "ollama":
            _PROVIDERS[prov] = OllamaProvider()
        elif prov == "anthropic":
            _PROVIDERS[prov] = AnthropicProvider()
        else:
            raise LLMError(f"unsupported LLM_PROVIDER: {prov} (supported: ollama, anthropic)")
    return _PROVIDERS[prov]


def _default_model(prompt_name: str) -> str:
    prov = os.getenv("LLM_PROVIDER", "ollama").lower()
    if prov == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", _ANTHROPIC_DEFAULT_MODEL)
    return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


# ---------- JSON 強制 + リトライ ----------


_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 出力から JSON オブジェクトを取り出す。"""
    # 1. そのままパース
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2. ```json ... ``` フェンス内
    if m := _JSON_FENCE.search(text):
        return json.loads(m.group(1))
    # 3. 最初の { ... }
    if m := _JSON_OBJECT.search(text):
        return json.loads(m.group(0))
    raise LLMError(f"JSON not found in response: {text[:200]}")


def chat_json(
    prompt: Prompt,
    *,
    vars: dict[str, Any] | None = None,
    model: str | None = None,
    timeout_s: float = 60.0,
) -> LLMResult:
    """Prompt を実行して JSON 辞書を返す。1回までリトライ。"""
    provider = _provider()
    model = model or _default_model(prompt.name)
    user = prompt.render_user(**(vars or {}))
    warnings: list[str] = []

    attempts = 0
    last_err: Exception | None = None
    raw: str = ""
    t0 = time.perf_counter()
    while attempts < 2:
        attempts += 1
        try:
            raw, _info = provider.complete_json(
                system=prompt.system,
                user=user,
                model=model,
                schema=prompt.output_schema,
                timeout_s=timeout_s,
            )
            data = _extract_json(raw)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return LLMResult(
                data=data,
                meta=CallMeta(
                    provider=provider.name,
                    model=model,
                    prompt_id=prompt.id,
                    latency_ms=latency_ms,
                    attempts=attempts,
                    raw_response_snippet=raw[:500],
                ),
                warnings=warnings,
            )
        except (LLMError, json.JSONDecodeError, httpx.HTTPError) as e:
            last_err = e
            warnings.append(f"attempt {attempts} failed: {type(e).__name__}: {e}")
            continue

    raise LLMError(f"LLM call failed after {attempts} attempts: {last_err}. last_raw={raw[:200]}")
