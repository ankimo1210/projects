"""人手不足の深刻度 × AI代替可能性 の4象限フレームワーク（日本の上場企業）.

右上象限 = 人手不足が深刻で、かつその労働をAIで代替できる
        = 供給制約を賃上げ以外の手段で外せるポテンシャルが最も大きい

Quick start
-----------
>>> from labor_ai_quadrant import sector_frame, company_frame, top_right
>>> sectors = sector_frame()
>>> top_right(sectors)[["shortage_score", "ai_score", "escape_potential"]]
"""

from .axes import ai_axis, sector_frame, shortage_axis
from .company import FINANCIAL_COLUMNS, company_frame, load_financials
from .config import SCENARIOS, Config
from .quadrant import assign_quadrants, escape_potential, quadrant_summary, thresholds, top_right
from .reference import ReferenceData, load_reference

__all__ = [
    "FINANCIAL_COLUMNS",
    "SCENARIOS",
    "Config",
    "ReferenceData",
    "ai_axis",
    "assign_quadrants",
    "company_frame",
    "escape_potential",
    "load_financials",
    "load_reference",
    "quadrant_summary",
    "sector_frame",
    "shortage_axis",
    "thresholds",
    "top_right",
]

__version__ = "0.1.0"
