"""A risk block in the shape ``risk.assemble`` returns, shared by the dashboard and mail tests."""

from __future__ import annotations

from typing import Any


def risk_block() -> dict[str, Any]:
    return {
        "as_of": "2026-09-11",
        "total": 46000000.0,
        "exposures": {
            "asset_class": [
                {"label": "日本株", "value": 15456000.0, "pct": 0.336},
                {"label": "米国株", "value": 12328000.0, "pct": 0.268},
                {"label": "現金", "value": 9430000.0, "pct": 0.205},
            ],
            "currency": [
                {"label": "JPY", "value": 31142000.0, "pct": 0.677},
                {"label": "USD", "value": 13570000.0, "pct": 0.295},
                {"label": "その他外貨", "value": 1288000.0, "pct": 0.028},
            ],
            "country": [
                {"label": "日本", "value": 31142000.0, "pct": 0.677},
                {"label": "米国", "value": 12650000.0, "pct": 0.275},
                {"label": "台湾", "value": 598000.0, "pct": 0.013},
            ],
            "region": [
                {"label": "日本", "value": 31142000.0, "pct": 0.677},
                {"label": "米国", "value": 12650000.0, "pct": 0.275},
                {"label": "新興国", "value": 973000.0, "pct": 0.021},
            ],
            "sector": [
                {"label": "債券・現金等", "value": 16192000.0, "pct": 0.352},
                {"label": "情報技術", "value": 15502000.0, "pct": 0.337},
                {"label": "エネルギー", "value": 5106000.0, "pct": 0.111},
            ],
            "issuers": [
                {
                    "label": "Advantest",
                    "value": 6716000.0,
                    "pct": 0.146,
                    "country": "日本",
                    "via": ["6857", "1329"],
                },
                {
                    "label": "Nvidia",
                    "value": 1472000.0,
                    "pct": 0.032,
                    "country": "米国",
                    "via": ["SMH", "QQQ"],
                },
            ],
            "coverage": {"issuer": 0.62},
        },
        "concentration": {
            "largest_position_ratio": 0.164,
            "top5_ratio": 0.605,
            "effective_positions": 7.3,
            "effective_sectors": 3.2,
            "effective_currencies": 1.8,
            "effective_countries": 1.9,
            "max_sector_ratio": 0.337,
            "max_sector": "情報技術",
            "largest_issuer_lookthrough_ratio": 0.146,
            "largest_issuer": "Advantest",
            "foreign_currency_ratio": 0.323,
            "largest_foreign_country_ratio": 0.275,
            "largest_foreign_country": "米国",
            "cash_ratio": 0.205,
        },
        "stats": {
            "window_days": 252,
            "vol_annual": 0.18,
            "var_1d_95": 0.015,
            "var_1d_99": 0.022,
            "es_1d_975": 0.02,
            "var_20d_95": 0.067,
            "var_1d_95_jpy": 690000.0,
            "var_1d_99_jpy": 1012000.0,
            "es_1d_975_jpy": 920000.0,
            "var_20d_95_jpy": 3082000.0,
            "worst_day": {"date": "2026-07-28", "pnl_jpy": -1144547.0, "pct": -0.0249},
            "beta": {"topix": 0.6, "sp500": 0.5, "usdjpy": 0.3},
            "prev": {
                "vol_annual": 0.17,
                "var_1d_95": 0.014,
                "es_1d_975": 0.019,
                "foreign_currency_ratio": 0.32,
                "largest_issuer_lookthrough_ratio": 0.15,
                "max_sector_ratio": 0.33,
                "beta_topix": 0.55,
                "beta_sp500": 0.5,
                "beta_usdjpy": 0.31,
                "policy_breaches": 2,
            },
        },
        "contributions": {
            "positions": [
                {
                    "ticker": "6857.T",
                    "sym": "6857",
                    "weight": 0.133,
                    "risk_share": 0.565,
                    "vol_annual": 0.74,
                },
                {
                    "ticker": "SMH",
                    "sym": "SMH",
                    "weight": 0.134,
                    "risk_share": 0.179,
                    "vol_annual": 0.39,
                },
            ],
            "currency": [
                {"label": "JPY", "risk_share": 0.784, "weight": 0.677},
                {"label": "USD", "risk_share": 0.209, "weight": 0.295},
            ],
            "sector": [{"label": "情報技術", "risk_share": 0.82, "weight": 0.337}],
            "country": [{"label": "台湾", "risk_share": 0.017, "weight": 0.013}],
            "region": [{"label": "新興国", "risk_share": 0.021, "weight": 0.021}],
        },
        "stress": {
            "scenarios": [
                {
                    "id": "historical_covid_crash_2020",
                    "label": "2020-03 コロナ暴落",
                    "kind": "historical",
                    "impact_jpy": -10764000.0,
                    "impact_pct": -0.234,
                },
                {
                    "id": "global_equity_down_10",
                    "label": "株式全体 -10%",
                    "kind": "hypothetical",
                    "impact_jpy": -3496000.0,
                    "impact_pct": -0.076,
                },
                {
                    "id": "compound_capex_acceleration",
                    "label": "AI capex 加速",
                    "kind": "compound",
                    "impact_jpy": 4692000.0,
                    "impact_pct": 0.102,
                },
            ],
            "episodes": [
                {
                    "id": "yen_carry_unwind_2024",
                    "label": "2024-08 円キャリー巻き戻し",
                    "start": "2024-07-31",
                    "end": "2024-08-05",
                    "impact_jpy": -4462000.0,
                    "impact_pct": -0.097,
                    "coverage": 1.0,
                }
            ],
        },
        "policy": [
            {
                "id": "single_position_max",
                "label": "単一銘柄は総資産の10%以下",
                "metric": "largest_position_ratio",
                "operator": "<=",
                "threshold": 0.1,
                "value": 0.164,
                "status": "breach",
                "note": "",
            },
            {
                "id": "effective_sector_min",
                "label": "実効セクター数は4以上",
                "metric": "sector_effective_count",
                "operator": ">=",
                "threshold": 4.0,
                "value": 3.2,
                "status": "breach",
                "note": "",
            },
            {
                "id": "foreign_currency_max",
                "label": "外貨エクスポージャーは総資産の40%以下",
                "metric": "foreign_currency_ratio",
                "operator": "<=",
                "threshold": 0.4,
                "value": 0.323,
                "status": "ok",
                "note": "暫定値",
            },
        ],
        "policy_breaches": 2,
        "history": {"vol_annual": 0.18, "policy_breaches": 2},
    }
