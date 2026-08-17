"""Tunable parameters for the labor-shortage x AI-substitutability framework.

Every number that embodies a judgement call lives here rather than being
buried in the scoring code, so that sensitivity analysis is a one-liner.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

# Quadrant labels. The framework's payoff is the top-right cell.
Q_ESCAPE = "AI解放"  # high shortage x high AI substitutability
Q_MARGIN = "AI増益"  # low shortage x high AI substitutability
Q_CONSTRAINED = "人手依存"  # high shortage x low AI substitutability
Q_INSENSITIVE = "低感応"  # low shortage x low AI substitutability

QUADRANT_ORDER = (Q_ESCAPE, Q_CONSTRAINED, Q_MARGIN, Q_INSENSITIVE)

QUADRANT_MEANING = {
    Q_ESCAPE: "人手不足が深刻で、かつその労働をAIで置き換えられる。制約解除の期待値が最大。",
    Q_MARGIN: "人手不足ではないが労働のAI代替余地が大きい。成長ではなくマージン改善の話。",
    Q_CONSTRAINED: "人手不足は深刻だがAIでは解けない。賃上げ・自動化設備・価格転嫁・M&Aの世界。",
    Q_INSENSITIVE: "人手不足もAI感応度も低い。この枠組みでは論点にならない。",
}


@dataclass(frozen=True)
class Config:
    """Scoring parameters.

    Attributes
    ----------
    realization_rate:
        AI代替可能とされた労働のうち、実際に人員・人件費の削減または増員回避として
        実現する割合。技術的可能性と経営実装のギャップ。既定 0.30。
    tilt_points:
        企業属性 (labor_intensity / knowledge_tilt) が業種スコアを動かす最大幅（点）。
        既定 8.0 は、業種間のばらつきを超えない範囲に企業内差分を抑えるための設定。
    threshold_method:
        4象限の境界。"median" = ユニバースの中央値で分割（相対評価）。
        "fixed" = fixed_threshold で分割（絶対評価）。
    fixed_threshold:
        threshold_method="fixed" のときの境界値。
    """

    realization_rate: float = 0.30
    tilt_points: float = 8.0
    threshold_method: str = "median"
    fixed_threshold: float = 50.0

    def replace(self, **kwargs: float | str) -> Config:
        """Return a copy with fields overridden (for sensitivity runs)."""
        return replace(self, **kwargs)

    def validate(self) -> None:
        if not 0.0 <= self.realization_rate <= 1.0:
            raise ValueError(f"realization_rate must be in [0, 1], got {self.realization_rate}")
        if self.tilt_points < 0:
            raise ValueError(f"tilt_points must be >= 0, got {self.tilt_points}")
        if self.threshold_method not in ("median", "fixed"):
            raise ValueError(f"threshold_method must be 'median' or 'fixed', got {self.threshold_method!r}")


# Sensitivity scenarios shipped with the report.
SCENARIOS: dict[str, Config] = {
    "base": Config(),
    "aggressive_adoption": Config(realization_rate=0.50),
    "conservative_adoption": Config(realization_rate=0.15),
    "absolute_threshold": Config(threshold_method="fixed"),
    "flat_company_tilt": Config(tilt_points=0.0),
}
