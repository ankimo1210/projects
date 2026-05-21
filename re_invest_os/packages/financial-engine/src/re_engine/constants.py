"""定数: 法定耐用年数・構造区分・税率テーブル。"""

from typing import Final, Literal

Structure = Literal["wood", "steel", "rc", "src"]
PropertyType = Literal["kuubun", "ittou_apt", "ittou_mansion", "kodate", "land"]
RepaymentType = Literal["amortized", "principal_equal"]

# 法定耐用年数 (居住用)
LEGAL_LIFE_YEARS: Final[dict[Structure, int]] = {
    "wood": 22,
    "steel": 27,  # 厚さ3-4mm。簡略化のため代表値
    "rc": 47,
    "src": 47,
}

# 譲渡所得税率 (個人、長期=5年超 / 短期=5年以下)
CAPITAL_GAIN_LONG_RATE: Final[float] = 0.20
CAPITAL_GAIN_SHORT_RATE: Final[float] = 0.39

# 構造表示用日本語
STRUCTURE_JP: Final[dict[Structure, str]] = {
    "wood": "木造",
    "steel": "鉄骨造",
    "rc": "RC造",
    "src": "SRC造",
}


def remaining_life_years(structure: Structure, completion_year: int, evaluation_year: int) -> int:
    """中古資産の簡便法による残存耐用年数。

    - 全部経過: legal_life * 0.2 (最低2年)
    - 一部経過: (legal_life - elapsed) + elapsed * 0.2
    """
    legal = LEGAL_LIFE_YEARS[structure]
    elapsed = max(0, evaluation_year - completion_year)
    if elapsed >= legal:
        return max(2, int(legal * 0.2))
    return int((legal - elapsed) + elapsed * 0.2)


def depreciation_rate(years: int) -> float:
    """定額法償却率 (小数3位)。"""
    if years <= 0:
        return 0.0
    return round(1.0 / years, 3)
