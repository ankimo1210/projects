"""AI サマリー生成 + 仲介確認質問生成。

summary_3line_v1 / inquiry_questions_v1 のプロンプトを使う。
NG ワードを含む場合は最大 2 回再生成。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from api.services import prompts
from api.services.llm_client import chat_json
from api.services.ng_filter import has_ng as _has_ng

# ─────────────────────────────────────────────────────────
# 3行サマリー
# ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SummaryResult:
    lines: list[str]  # 必ず 3 行
    ng_filtered: bool  # リジェネ発動したか
    latency_ms: int
    model: str


def _build_summary_user(
    analysis_result: dict[str, Any],
    score_result: dict[str, Any],
) -> str:
    kpi = analysis_result.get("kpi", {})
    exit_ = analysis_result.get("exit", {})
    cap_pct = f"{kpi.get('cap_rate', 0) * 100:.2f}%"
    dscr_min = kpi.get("dscr_min", "—")
    dscr_y1 = kpi.get("dscr_year1", "—")
    irr = kpi.get("equity_irr")
    irr_str = f"{irr * 100:.1f}%" if irr else "算出不能"
    atcf = kpi.get("atcf_first_year_yen", 0)
    net_proc = exit_.get("net_proceeds_yen", 0)
    score = score_result.get("total", 0)
    evaluation = score_result.get("evaluation", "—")

    analysis_json = (
        f'{{"score": {score}, "evaluation": "{evaluation}", '
        f'"cap_rate_pct": "{cap_pct}", "dscr_min": {dscr_min}, "dscr_y1": {dscr_y1}, '
        f'"equity_irr": "{irr_str}", "atcf_y1_yen": {atcf}, '
        f'"exit_net_proceeds_yen": {net_proc}}}'
    )

    prompt = prompts.load("summary_3line")
    return prompt.render_user(analysis_json=analysis_json)


def generate_summary(
    analysis_result: dict[str, Any],
    score_result: dict[str, Any],
) -> SummaryResult:
    prompt = prompts.load("summary_3line")
    ng_filtered = False
    latency_ms = 0
    model = ""
    lines: list[str] = []

    for _ in range(3):
        user_msg = _build_summary_user(analysis_result, score_result)
        r = chat_json(
            prompt.__class__(
                name=prompt.name,
                version=prompt.version,
                system=prompt.system,
                user_template=user_msg,
                output_schema=None,
                raw_path=prompt.raw_path,
            ),
        )
        latency_ms += r.meta.latency_ms
        model = r.meta.model
        raw = r.data

        lines = []
        if isinstance(raw.get("lines"), list):
            lines = [str(s) for s in raw["lines"]]
        elif isinstance(raw, dict):
            # fallback: キーや値から文字列を探す
            for v in raw.values():
                if isinstance(v, list):
                    lines = [str(s) for s in v[:3]]
                    break
                if isinstance(v, str) and len(v) > 20:
                    lines = [s.strip() for s in v.split("\n") if s.strip()]
                    break

        # プレフィックス除去: "1行目: ..." → "..."
        _prefix = re.compile(r"^(?:\d行目|line \d+)\s*[:：]\s*", re.IGNORECASE)
        lines = [_prefix.sub("", s).strip() for s in lines]

        # 3行に正規化
        while len(lines) < 3:
            lines.append("")
        lines = lines[:3]

        if not _has_ng("\n".join(lines)):
            return SummaryResult(
                lines=lines, ng_filtered=ng_filtered, latency_ms=latency_ms, model=model
            )
        ng_filtered = True

    return SummaryResult(lines=lines, ng_filtered=True, latency_ms=latency_ms, model=model)


# ─────────────────────────────────────────────────────────
# 確認質問リスト
# ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InquiryQuestion:
    category: str  # "essential" | "precision" | "pre_purchase"
    question: str
    rationale: str


@dataclass(frozen=True)
class InquiryResult:
    questions: list[InquiryQuestion]
    latency_ms: int
    model: str


def generate_inquiry(
    score_result: dict[str, Any],
    analysis_result: dict[str, Any],
    needs_confirmation: list[str] | None = None,
) -> InquiryResult:
    kpi = analysis_result.get("kpi", {})
    prompt = prompts.load("inquiry_questions")

    # v2: テンプレート埋め込み方式
    score_total = score_result.get("total", 0)
    evaluation = score_result.get("evaluation", "—")
    dscr_min = kpi.get("dscr_min", "—")
    atcf_y1 = kpi.get("atcf_first_year_yen", 0)
    atcf_str = f"¥{atcf_y1:,}" if isinstance(atcf_y1, int) else str(atcf_y1)
    missing = ", ".join(needs_confirmation or []) or "なし"

    analysis_summary = (
        f"スコア: {score_total}/100 ({evaluation})\n"
        f"DSCR最小: {dscr_min}\n"
        f"ATCF Y1: {atcf_str}\n"
        f"資料不足: {missing}"
    )
    user_msg = prompt.render_user(analysis_summary=analysis_summary)

    r = chat_json(
        prompt.__class__(
            name=prompt.name,
            version=prompt.version,
            system=prompt.system,
            user_template=user_msg,
            output_schema=None,
            raw_path=prompt.raw_path,
        ),
    )

    raw = r.data
    # 3パターンに対応:
    # A) {"questions": [...]}
    # B) [{"category":...}, ...]  (list at root)
    # C) {"category":..., "question":...} (single object)
    if isinstance(raw.get("questions"), list):
        raw_questions = raw["questions"]
    elif isinstance(raw, list):
        raw_questions = raw
    elif "question" in raw:
        raw_questions = [raw]
    else:
        raw_questions = []

    questions = []
    for q in raw_questions[:8]:
        if not isinstance(q, dict):
            continue
        questions.append(
            InquiryQuestion(
                category=str(q.get("category", "essential")),
                question=str(q.get("question", "")),
                rationale=str(q.get("rationale", "")),
            )
        )

    return InquiryResult(questions=questions, latency_ms=r.meta.latency_ms, model=r.meta.model)


# ─────────────────────────────────────────────────────────
# 前提甘さ検出 (assumption critique)
# ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CritiqueItem:
    flag_type: str
    severity: str
    explanation: str
    verification: str


@dataclass(frozen=True)
class CritiqueResult:
    critiques: list[CritiqueItem]
    rule_flags: list[str]  # ルールベースで検出したフラグ
    latency_ms: int
    model: str


def _detect_rule_flags(
    analysis_result: dict[str, Any],
    assumptions: dict[str, Any],
) -> list[str]:
    """数値ルールで前提甘さフラグを検出。LLM を使わない。"""
    flags: list[str] = []
    kpi = analysis_result.get("kpi", {})
    prop = assumptions.get("property", {})
    opex = assumptions.get("opex", {})
    income = assumptions.get("income", {})
    exit_ = assumptions.get("exit", {})

    # 表面利回りのみ (NOI Cap と乖離が大きい)
    if kpi.get("cap_rate") and prop.get("purchase_price_yen") and income.get("gpi_monthly_yen"):
        gpi = income["gpi_monthly_yen"]
        price = prop["purchase_price_yen"]
        surface = (gpi * 12) / price
        cap = kpi["cap_rate"]
        if surface - cap > 0.025:
            flags.append("gross_yield_only")

    # 修繕費なし
    if not opex.get("repair_reserve_monthly_yen") and not opex.get("building_mgmt_yen"):
        flags.append("repair_missing")

    # 固都税なし
    if not opex.get("fixed_property_tax_yen"):
        flags.append("property_tax_missing")

    # 出口 Cap が取得時と同じ (楽観的)
    if exit_.get("exit_cap_rate") and kpi.get("cap_rate"):
        if abs(exit_["exit_cap_rate"] - kpi["cap_rate"]) < 0.002:
            flags.append("exit_cap_unrealistic")

    # LTV が 90% 超
    if kpi.get("ltv") and kpi["ltv"] > 0.9:
        flags.append("ltv_aggressive")

    # DSCR が低い → 空室率の甘さ疑い
    if kpi.get("dscr_min") and kpi["dscr_min"] < 1.0:
        vr = income.get("vacancy_rate", 0.05)
        if vr < 0.05:
            flags.append("vacancy_understated")

    return flags


def generate_critique(
    analysis_result: dict[str, Any],
    score_result: dict[str, Any],
    assumptions: dict[str, Any],
) -> CritiqueResult:
    rule_flags = _detect_rule_flags(analysis_result, assumptions)
    prompt = prompts.load("assumption_critique")

    kpi = analysis_result.get("kpi", {})
    summary = (
        f"スコア: {score_result.get('total', 0)}/100 ({score_result.get('evaluation', '—')})\n"
        f"DSCR最小: {kpi.get('dscr_min', '—')}  Cap: {kpi.get('cap_rate', '—'):.3f}"
        if isinstance(kpi.get("cap_rate"), float)
        else f"スコア: {score_result.get('total', 0)}/100"
    )
    flags_json = str(rule_flags) if rule_flags else "[]"

    user_msg = prompt.render_user(
        analysis_result_summary=summary,
        warning_flags_json=flags_json,
    )

    r = chat_json(
        prompt.__class__(
            name=prompt.name,
            version=prompt.version,
            system=prompt.system,
            user_template=user_msg,
            output_schema=None,
            raw_path=prompt.raw_path,
        ),
    )

    raw = r.data
    raw_critiques = raw.get("critiques", [])
    if not isinstance(raw_critiques, list):
        raw_critiques = []

    critiques = []
    for c in raw_critiques[:6]:
        if not isinstance(c, dict):
            continue
        critiques.append(
            CritiqueItem(
                flag_type=str(c.get("flag_type", "unknown")),
                severity=str(c.get("severity", "info")),
                explanation=str(c.get("explanation", "")),
                verification=str(c.get("verification", "")),
            )
        )

    return CritiqueResult(
        critiques=critiques,
        rule_flags=rule_flags,
        latency_ms=r.meta.latency_ms,
        model=r.meta.model,
    )
