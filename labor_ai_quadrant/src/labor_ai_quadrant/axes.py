"""The two axes of the framework, computed at 東証33業種 level.

Axis X — 人手不足深刻度 (labour shortage severity)
    公表労働統計の6指標を業種横断で z 化し、重み付き合成する。

Axis Y — 生成AI代替可能性 (generative-AI substitutability)
    業種の職業構成比 (労働力調査 産業×職業) と職業別 AI 代替ポテンシャル
    (ILO WP140 の GenAI exposure) の内積。「その業種の労働の何%が生成AIに
    晒されているか」という解釈可能な水準を持つ。物理的自動化 (ロボティクス・
    自動運転) は ILO の指数が測っていないので、この軸の外にある。

両軸とも、4象限マップ用には 33業種内の min-max で 0-100 に相対化した
``*_score`` を使う。P/L への換算には相対化前の生の水準を使うこと
(``ai_substitutable_share_pct``)。混同すると桁が壊れる。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config
from .reference import SHORTAGE_INDICATORS, ReferenceData, load_reference

#: z 値のクリップ幅。単一業種の極端値（建設業の有効求人倍率など）が
#: 合成スコア全体を支配しないようにする。
Z_CLIP = 2.5


def _zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    if sd == 0:
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / sd


def rescale_0_100(s: pd.Series) -> pd.Series:
    """Min-max rescale to 0-100. A degenerate (constant) series maps to 50."""
    lo, hi = s.min(), s.max()
    if np.isclose(hi, lo):
        return pd.Series(50.0, index=s.index)
    return (s - lo) / (hi - lo) * 100.0


def shortage_axis(ref: ReferenceData | None = None) -> pd.DataFrame:
    """人手不足深刻度。

    Returns a frame indexed by sector name with the per-indicator z values,
    the weighted composite, and the 0-100 relative score.
    """
    ref = ref or load_reference()
    raw = ref.shortage[list(SHORTAGE_INDICATORS)].astype(float)

    z = raw.apply(_zscore).clip(-Z_CLIP, Z_CLIP)
    composite = z.mul(ref.shortage_weights, axis=1).sum(axis=1)

    out = z.add_prefix("z_")
    out["shortage_composite"] = composite
    out["shortage_score"] = rescale_0_100(composite)
    return out


def ai_axis(cfg: Config | None = None, ref: ReferenceData | None = None) -> pd.DataFrame:
    """AI代替可能性。

    ``ai_substitutable_share_pct`` は「業種の労働のうちAIで代替しうる割合(%)」
    という解釈を持つ水準値。``ai_score`` はそれを33業種内で 0-100 に相対化した
    象限マップ用の指標。
    """
    cfg = cfg or Config()
    cfg.validate()
    ref = ref or load_reference()

    potential = ref.occupations["ai_potential"]

    # 内積: 業種ごとの職業構成比 (行和1) × 職業別ポテンシャル(0-100)
    gross = ref.mix.mul(potential, axis=1).sum(axis=1)
    effective = gross * (1.0 - ref.regulation_drag)

    out = pd.DataFrame(
        {
            "ai_gross_share_pct": gross,
            "regulation_drag": ref.regulation_drag,
            "ai_substitutable_share_pct": effective,
            "ai_score": rescale_0_100(effective),
        }
    )
    out["top_ai_occupation"] = _top_contributor(ref.mix, potential)
    return out


def _top_contributor(mix: pd.DataFrame, potential: pd.Series) -> pd.Series:
    """For each sector, the occupation contributing the most AI-substitutable labour."""
    contribution = mix.mul(potential, axis=1)
    return contribution.idxmax(axis=1)


def sector_frame(cfg: Config | None = None, ref: ReferenceData | None = None) -> pd.DataFrame:
    """Both axes joined at sector level, with quadrant assignment.

    Columns of interest: ``shortage_score``, ``ai_score`` (0-100 relative,
    used for the quadrant map), ``ai_substitutable_share_pct`` (raw level,
    used for P/L translation) and ``escape_potential``.
    """
    cfg = cfg or Config()
    ref = ref or load_reference()

    from .quadrant import assign_quadrants, escape_potential  # local: avoids a cycle

    shortage = shortage_axis(ref)
    ai = ai_axis(cfg, ref)

    df = pd.concat([shortage, ai], axis=1)
    df.index.name = "sector33"
    df["escape_potential"] = escape_potential(df["shortage_score"], df["ai_score"])
    df["quadrant"] = assign_quadrants(df["shortage_score"], df["ai_score"], cfg)
    df = df.join(relief_columns(cfg, ref))
    return df.sort_values("escape_potential", ascending=False)


def relief_columns(cfg: Config, ref: ReferenceData) -> pd.DataFrame:
    """人手不足の緩和量を、従業員数に対する比率(%)で出す。

    P/L 換算の起点になる3つの量（`docs/METHODOLOGY.md` の「6. P/L への換算」）。
    どれも「常用労働者数に対する%」で揃えてあるので直接比較・比較可能。

    * ``vacancy_rate_pct``     欠員率。埋まっていない求人 ÷ 常用労働者数。
      「本来の人員に対して何%足りないか」＝ 供給制約で取り逃している労働。
    * ``ai_freed_labor_pct``   AI が空ける労働。代替可能割合 × 実現率。
      人を増やさずに増員したのと同じ効果を持つ労働量。
    * ``closable_gap_pct``     上の2つの小さいほう。空いた労働は、足りていない
      ぶんを超えては「不足の緩和」にならない（超えた部分は需要側の話になる）。
    * ``gap_coverage_x``       空く労働 ÷ 欠員。既定設定では全33業種で 1 を超える
      ＝ AI 側が上限になることはない。だから P/L に効く量は欠員率で決まり、
      AI 軸は「そもそも埋められるのか」という関門として働く。この倍率が、
      関門にどれだけ余裕があるかを示す。
    """
    ai_share = ai_axis(cfg, ref)["ai_substitutable_share_pct"]
    gap = ref.shortage["vacancy_rate_pct"].astype(float)
    freed = ai_share * cfg.realization_rate
    return pd.DataFrame(
        {
            "vacancy_rate_pct": gap,
            "ai_freed_labor_pct": freed,
            "closable_gap_pct": pd.concat([freed, gap], axis=1).min(axis=1),
            "gap_coverage_x": freed / gap.where(gap > 0),
        }
    )
