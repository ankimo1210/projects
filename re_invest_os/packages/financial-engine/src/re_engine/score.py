"""100点スコア (仮配点 v0.1)。

仕様: docs/architecture/calculation_engine_spec.md §5.6

買い推奨ではなく、分析上の健全性・リスク耐性を示す。
市場コンテキスト (Cap rate相場・賃料相場) が未投入のときは、その配点は満点(または0)で計算する。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from re_engine.models import AnalysisResult


class MarketContext(BaseModel):
    """市場コンテキスト (近傍取引・公示地価から算出)。MVPでは外部入力。"""

    market_cap_rate: float | None = None  # 近傍平均Cap (NOI/価格)
    market_rent_per_sqm_yen: int | None = None  # ㎡賃料相場
    property_rent_per_sqm_yen: int | None = None  # 物件の㎡賃料
    appraisal_price_yen: int | None = None  # 積算価格 (オプション)
    model_config = ConfigDict(extra="forbid")


class DataQuality(BaseModel):
    """データ信頼度。0.0〜1.0。"""

    document_completeness: float = Field(default=1.0, ge=0.0, le=1.0)
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    user_confirmed: bool = False
    model_config = ConfigDict(extra="forbid")


class ScoreComponent(BaseModel):
    name: str
    score: float  # 配点 (0 〜 max)
    max_score: float
    detail: str
    model_config = ConfigDict(extra="forbid")


class ScoreResult(BaseModel):
    total: float  # 0〜100
    components: list[ScoreComponent]
    evaluation: str  # "健全" / "中立" / "要警戒"
    model_config = ConfigDict(extra="forbid")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _price_score(result: AnalysisResult, ctx: MarketContext) -> ScoreComponent:
    """価格妥当性 (20点)。NOI Cap が市場Cap以上で満点。"""
    max_score = 20.0
    cap = result.kpi.cap_rate
    if ctx.market_cap_rate is None:
        # 市場情報なし → Capが5%以上で満点、3%で半分、それ以下は0
        if cap >= 0.05:
            score = max_score
        elif cap <= 0.03:
            score = 0.0
        else:
            score = max_score * (cap - 0.03) / 0.02
        detail = f"Cap {cap * 100:.2f}% (市場情報未投入)"
    else:
        # Cap >= market: 満点
        # Cap < market: 線形減点 (-2pt未満で0点)
        delta = cap - ctx.market_cap_rate
        if delta >= 0:
            score = max_score
        elif delta <= -0.02:
            score = 0.0
        else:
            score = max_score * (delta + 0.02) / 0.02
        detail = (
            f"Cap {cap * 100:.2f}% vs 市場 {ctx.market_cap_rate * 100:.2f}% ({delta * 100:+.2f}pt)"
        )
    return ScoreComponent(name="price", score=score, max_score=max_score, detail=detail)


def _rent_score(ctx: MarketContext) -> ScoreComponent:
    """賃料妥当性 (15点)。"""
    max_score = 15.0
    if (
        ctx.market_rent_per_sqm_yen is None
        or ctx.property_rent_per_sqm_yen is None
        or ctx.market_rent_per_sqm_yen <= 0
    ):
        return ScoreComponent(
            name="rent",
            score=max_score,
            max_score=max_score,
            detail="賃料相場情報未投入 (満点扱い)",
        )
    ratio = ctx.property_rent_per_sqm_yen / ctx.market_rent_per_sqm_yen
    # 0.95〜1.05 範囲で満点、それ以上の乖離で減点
    if 0.95 <= ratio <= 1.05:
        score = max_score
    elif ratio > 1.05:
        # 過大評価: 1.20で0点
        score = max(0.0, max_score * (1.20 - ratio) / 0.15)
    else:
        # 過小評価 (実は上昇余地): 0.80で半分
        score = max(0.0, max_score * (ratio - 0.65) / 0.30)
    return ScoreComponent(
        name="rent",
        score=score,
        max_score=max_score,
        detail=f"物件㎡賃料 {ctx.property_rent_per_sqm_yen} vs 市場 "
        f"{ctx.market_rent_per_sqm_yen} (比 {ratio:.2f})",
    )


def _cf_score(result: AnalysisResult) -> ScoreComponent:
    """税前/税後CF (20点)。初年度ATCFが基準。"""
    max_score = 20.0
    atcf1 = result.kpi.atcf_first_year_yen
    price = result.assumptions.property.purchase_price_yen
    # ATCF / 価格 で正規化
    yield_ = atcf1 / price if price > 0 else 0.0
    if yield_ >= 0.03:
        score = max_score
    elif yield_ <= -0.02:
        score = 0.0
    else:
        score = max_score * (yield_ + 0.02) / 0.05
    return ScoreComponent(
        name="cashflow",
        score=score,
        max_score=max_score,
        detail=f"初年度ATCF ¥{atcf1:,} (対価格 {yield_ * 100:.2f}%)",
    )


def _financing_score(result: AnalysisResult) -> ScoreComponent:
    """融資耐性 (15点)。DSCR最小と金利+1%耐性。"""
    max_score = 15.0
    dscr_min = result.kpi.dscr_min
    if dscr_min >= 1.30:
        score = max_score
    elif dscr_min <= 1.00:
        score = 0.0
    else:
        score = max_score * (dscr_min - 1.00) / 0.30
    return ScoreComponent(
        name="financing",
        score=score,
        max_score=max_score,
        detail=f"DSCR最小 {dscr_min:.2f}",
    )


def _exit_score(result: AnalysisResult) -> ScoreComponent:
    """出口耐性 (15点)。net proceeds が equity 以上で満点。"""
    max_score = 15.0
    net = result.exit_.net_proceeds_yen
    equity = result.assumptions.acquisition.equity_yen
    if equity <= 0:
        return ScoreComponent(
            name="exit", score=max_score / 2, max_score=max_score, detail="自己資金情報なし"
        )
    ratio = net / equity
    if ratio >= 1.5:
        score = max_score
    elif ratio <= 0.5:
        score = 0.0
    else:
        score = max_score * (ratio - 0.5) / 1.0
    return ScoreComponent(
        name="exit",
        score=score,
        max_score=max_score,
        detail=f"売却税後手残り ¥{net:,} (自己資金比 {ratio:.2f}x)",
    )


def _capex_score(result: AnalysisResult) -> ScoreComponent:
    """修繕CAPEX耐性 (10点)。簡易版: 初年度OPEX/EGI比で評価。"""
    max_score = 10.0
    cf1 = result.yearly_cashflows[0]
    if cf1.egi_yen <= 0:
        return ScoreComponent(name="capex", score=0.0, max_score=max_score, detail="EGI=0")
    opex_ratio = cf1.opex_yen / cf1.egi_yen
    if opex_ratio <= 0.25:
        score = max_score
    elif opex_ratio >= 0.55:
        score = 0.0
    else:
        score = max_score * (0.55 - opex_ratio) / 0.30
    return ScoreComponent(
        name="capex",
        score=score,
        max_score=max_score,
        detail=f"OPEX/EGI = {opex_ratio * 100:.1f}%",
    )


def _data_quality_score(dq: DataQuality) -> ScoreComponent:
    """データ信頼度 (5点)。"""
    max_score = 5.0
    score = max_score * (dq.document_completeness * 0.5 + dq.extraction_confidence * 0.5)
    if dq.user_confirmed:
        score = min(max_score, score + 0.5)
    return ScoreComponent(
        name="data_quality",
        score=score,
        max_score=max_score,
        detail=f"資料充足 {dq.document_completeness * 100:.0f}% / "
        f"抽出信頼度 {dq.extraction_confidence * 100:.0f}%",
    )


def total_score(
    result: AnalysisResult,
    market_context: MarketContext | None = None,
    data_quality: DataQuality | None = None,
) -> ScoreResult:
    ctx = market_context or MarketContext()
    dq = data_quality or DataQuality()
    components = [
        _price_score(result, ctx),
        _rent_score(ctx),
        _cf_score(result),
        _financing_score(result),
        _exit_score(result),
        _capex_score(result),
        _data_quality_score(dq),
    ]
    total = sum(c.score for c in components)
    total = _clamp(total, 0.0, 100.0)
    if total >= 70:
        evaluation = "健全"
    elif total >= 50:
        evaluation = "中立"
    else:
        evaluation = "要警戒"
    return ScoreResult(total=total, components=components, evaluation=evaluation)
