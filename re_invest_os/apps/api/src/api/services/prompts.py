"""Prompt loader: docs/prompts/*.md からバージョン付きプロンプトを読み込む。

設計原則:
- プロンプト本体は docs/prompts/ にマークダウンで残す (人が読める)
- ローダーは fenced code block を section ヘッダーで抽出
- 各 prompt は name + version を保持し、AnalysisResult に prompt_versions として記録
- 出力スキーマ (JSON Schema) も同じファイルに記述 → LLM の JSON 強制に使用

ファイル命名規約: ``{name}_v{N}.md`` (例: classify_document_v1.md)
ヘッダー規約: ``## version`` / ``## system`` / ``## user_template`` / ``## output_schema``
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


def _find_prompts_dir() -> Path:
    """Repo root の docs/prompts を解決する。

    ``REINVEST_PROMPTS_DIR`` env で上書き可能 (テスト用)。
    """
    import os

    if env := os.environ.get("REINVEST_PROMPTS_DIR"):
        return Path(env)
    # apps/api/src/api/services/prompts.py からの相対 → repo root
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "prompts"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("docs/prompts/ ディレクトリが見つかりません")


@dataclass(frozen=True)
class Prompt:
    name: str  # "classify_document"
    version: str  # "v1"
    system: str  # system 指示
    user_template: str  # {{var}} 置換用テンプレート
    output_schema: dict[str, Any] | None
    raw_path: Path

    @property
    def id(self) -> str:
        return f"{self.name}:{self.version}"

    def render_user(self, **vars: Any) -> str:
        """{{key}} を vars[key] で置換。"""
        out = self.user_template
        for k, v in vars.items():
            out = out.replace(f"{{{{{k}}}}}", str(v))
        return out


# ## heading 配下、最初の ``` ... ``` ブロックを取り出す
_SECTION_PATTERN = re.compile(
    r"^##\s+(?P<heading>[^\n]+)\n+"
    r"(?P<body>(?:(?!^##\s).*\n?)+)",
    re.MULTILINE,
)
_FENCE_PATTERN = re.compile(r"```(?:\w+)?\n(?P<code>.*?)\n```", re.DOTALL)


def _normalize_heading(h: str) -> str:
    """``output_schema (JSON Schema)`` → ``output_schema``。

    括弧書き・補足語を落とし、最初の単語列だけ取る。
    """
    h = h.strip().lower()
    # 括弧書きを除去
    h = re.sub(r"\([^)]*\)", "", h).strip()
    # 最初の連続する英数字_を採用
    m = re.match(r"[a-z0-9_]+", h)
    return m.group(0) if m else h


def _parse_markdown(text: str) -> dict[str, str]:
    """``## heading`` セクション → 最初の fenced block (なければ素テキスト) の辞書。"""
    sections: dict[str, str] = {}
    for m in _SECTION_PATTERN.finditer(text):
        heading = _normalize_heading(m.group("heading"))
        body = m.group("body")
        fence = _FENCE_PATTERN.search(body)
        if fence:
            sections[heading] = fence.group("code").strip()
        else:
            sections[heading] = body.strip()
    return sections


_VERSION_RE = re.compile(r"v\d+")
_FILENAME_RE = re.compile(r"^(?P<name>.+)_v(?P<ver>\d+)\.md$")


def _load_one(path: Path) -> Prompt:
    m = _FILENAME_RE.match(path.name)
    if not m:
        raise ValueError(f"プロンプトファイル名規約違反: {path.name}")
    name = m.group("name")
    version = f"v{m.group('ver')}"

    sections = _parse_markdown(path.read_text(encoding="utf-8"))

    # version セクションが書かれていればそちらを優先 (ファイル名と一致確認)
    if v := sections.get("version"):
        if mm := _VERSION_RE.search(v):
            ver_in_body = mm.group(0)
            if ver_in_body != version:
                raise ValueError(
                    f"{path.name}: filename version={version} body version={ver_in_body} 不一致"
                )

    system = sections.get("system", "").strip()
    user_template = sections.get("user_template", "").strip()
    schema_str = sections.get("output_schema")
    output_schema: dict[str, Any] | None = None
    if schema_str:
        try:
            output_schema = json.loads(schema_str)
        except json.JSONDecodeError:
            # スキーマが Markdown 解説の場合もある → None でよい
            output_schema = None

    return Prompt(
        name=name,
        version=version,
        system=system,
        user_template=user_template,
        output_schema=output_schema,
        raw_path=path,
    )


@lru_cache(maxsize=1)
def _all_prompts() -> dict[str, Prompt]:
    """name → Prompt (最新 version) の辞書。"""
    dir_ = _find_prompts_dir()
    by_name: dict[str, Prompt] = {}
    for path in sorted(dir_.glob("*_v*.md")):
        p = _load_one(path)
        existing = by_name.get(p.name)
        if existing is None or p.version > existing.version:
            by_name[p.name] = p
    return by_name


def load(name: str) -> Prompt:
    """name (例: 'classify_document') の最新バージョンを返す。"""
    prompts = _all_prompts()
    if name not in prompts:
        raise KeyError(f"prompt not found: {name}. available={list(prompts)}")
    return prompts[name]


def all_versions() -> dict[str, str]:
    """全プロンプトの name → version 辞書 (AnalysisResult に埋め込む)。"""
    return {p.name: p.version for p in _all_prompts().values()}


def reset_cache() -> None:
    """テスト用: キャッシュをクリア。"""
    _all_prompts.cache_clear()
