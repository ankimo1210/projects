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
        4象限の境界。"median" = 33業種の中央値で分割（相対評価、企業にも投影）。
        "fixed" = fixed_threshold で分割（絶対評価）。
    fixed_threshold:
        threshold_method="fixed" のときの境界値。
    labor_output_elasticity:
        空いた労働1単位が生む産出。1.0 は「既存従業員と同じ生産性で売上に変わる」。
        既定1.0 は上限側の仮定で、推定値ではない。
    demand_capture_rate:
        取り逃していた需要のうち、いま回収できる割合。1.0 は「需要は消えずに残っている」。
    pass_through_retained:
        増えた粗利のうち自社に残る割合。1.0 は「単価下落として顧客に移転しない」。
        受託型（SI・人材・警備）では 1.0 を割ると考えるのが自然。
    implementation_cost_pct_of_revenue:
        AI導入コスト（ライセンス・実装・再教育）の売上比%。既定0.0＝引いていない。

    後半4つは 2026-08-17 のレビュー（F-04）を受けて明示した仮定である。既定値は
    **すべて中立（何も割り引かない）** なので、既定の数字は仮定を置いた上限側の
    シナリオだと分かる。値を振るのは呼び出し側の判断。
    """

    realization_rate: float = 0.30
    tilt_points: float = 8.0
    threshold_method: str = "median"
    fixed_threshold: float = 50.0
    labor_output_elasticity: float = 1.0
    demand_capture_rate: float = 1.0
    pass_through_retained: float = 1.0
    implementation_cost_pct_of_revenue: float = 0.0

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
        for name in ("labor_output_elasticity", "demand_capture_rate", "pass_through_retained"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")
        if not 0.0 <= self.implementation_cost_pct_of_revenue <= 100.0:
            raise ValueError(
                "implementation_cost_pct_of_revenue must be in [0, 100], "
                f"got {self.implementation_cost_pct_of_revenue}"
            )


# Sensitivity scenarios shipped with the report.
SCENARIOS: dict[str, Config] = {
    "base": Config(),
    "aggressive_adoption": Config(realization_rate=0.50),
    "conservative_adoption": Config(realization_rate=0.15),
    "absolute_threshold": Config(threshold_method="fixed"),
    "flat_company_tilt": Config(tilt_points=0.0),
    # 売上回復の経路に「そこまで都合よくは進まない」側の仮定を入れたケース。
    # 数字は例示であって推定ではない（弾力性0.7・需要回収0.6・自社残存0.7・導入費 売上比0.2%）。
    "tempered_recovery": Config(
        labor_output_elasticity=0.7,
        demand_capture_rate=0.6,
        pass_through_retained=0.7,
        implementation_cost_pct_of_revenue=0.2,
    ),
}
