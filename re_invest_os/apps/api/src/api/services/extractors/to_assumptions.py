"""ExtractedProperty → Assumptions マッパー。

抽出結果には欠けがある。AssumptionDefaultsPolicy を一箇所に集めて、
「どこからユーザーに確認させるべきか」を warnings で返す。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from re_engine.models import (
    AcquisitionAssumptions,
    Assumptions,
    ExitAssumptions,
    IncomeAssumptions,
    LoanAssumptions,
    OpexAssumptions,
    PropertyAssumptions,
    TaxAssumptions,
)

from api.services.extractors.property_brochure import PropertyBrochureExtraction


@dataclass(frozen=True)
class MappingResult:
    assumptions: Assumptions
    needs_confirmation: list[str] = field(default_factory=list)  # ユーザー確認が必要な field
    derived: list[str] = field(default_factory=list)  # デフォルトから補完した field


_DEFAULTS = {
    "vacancy_rate": 0.05,
    "rent_growth_rate": -0.005,
    "management_fee_rate": 0.05,
    "interest_rate": 0.020,
    "term_years": 30,
    "ltv_ratio": 0.70,
    "exit_cap_rate_premium": 0.005,  # 取得時 cap + 0.5pt を出口 cap デフォルトに
    "hold_period_years": 10,
    "acquisition_cost_rate": 0.07,
    "selling_cost_rate": 0.04,
    "income_tax_rate": 0.20,
}


def _build_year_month(raw: str | None) -> str | None:
    """'2011-04' / '2011/4' / '2011年4月' → 'YYYY-MM'"""
    if not raw:
        return None
    s = raw.replace("年", "-").replace("月", "").replace("/", "-").strip("-").strip()
    parts = s.split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}"
    return None


def _land_building_split(price: int) -> tuple[int, int]:
    """土地建物の按分が抽出にない場合の暫定: 区分マンションは 20:80。"""
    land = int(price * 0.20)
    building = price - land
    return land, building


def _gpi_monthly(brochure: PropertyBrochureExtraction) -> int | None:
    """月額賃料の推定。明示値 → なければ price * yield / 12。"""
    if brochure.estimated_full_rent_monthly_yen:
        return int(brochure.estimated_full_rent_monthly_yen)
    if brochure.asking_price_yen and brochure.gross_yield_pct:
        annual = brochure.asking_price_yen * (brochure.gross_yield_pct / 100.0)
        return int(annual / 12.0)
    return None


def _location_pref(address: str | None) -> str:
    """住所から都道府県コードを推定。粗くてよい (v1)。

    フルマッチで決まらないなら "13" (東京) を仮置き。
    """
    if not address:
        return "13"
    # 簡易マッピング (主要のみ; 拡張は data に切り出す)
    table = {
        "北海道": "01",
        "青森": "02",
        "岩手": "03",
        "宮城": "04",
        "秋田": "05",
        "山形": "06",
        "福島": "07",
        "茨城": "08",
        "栃木": "09",
        "群馬": "10",
        "埼玉": "11",
        "千葉": "12",
        "東京": "13",
        "神奈川": "14",
        "新潟": "15",
        "富山": "16",
        "石川": "17",
        "福井": "18",
        "山梨": "19",
        "長野": "20",
        "岐阜": "21",
        "静岡": "22",
        "愛知": "23",
        "三重": "24",
        "滋賀": "25",
        "京都": "26",
        "大阪": "27",
        "兵庫": "28",
        "奈良": "29",
        "和歌山": "30",
        "鳥取": "31",
        "島根": "32",
        "岡山": "33",
        "広島": "34",
        "山口": "35",
        "徳島": "36",
        "香川": "37",
        "愛媛": "38",
        "高知": "39",
        "福岡": "40",
        "佐賀": "41",
        "長崎": "42",
        "熊本": "43",
        "大分": "44",
        "宮崎": "45",
        "鹿児島": "46",
        "沖縄": "47",
    }
    for key, code in table.items():
        if key in address:
            return code
    return "13"


def to_assumptions(
    brochure: PropertyBrochureExtraction,
    *,
    acquisition_year: int,
    equity_yen: int | None = None,
) -> MappingResult:
    """抽出結果から Assumptions を組み立てる。

    欠けている入力は安全側のデフォルトで埋め、needs_confirmation に列挙する。
    """
    needs: list[str] = []
    derived: list[str] = []

    # --- 必須項目チェック ---
    if not brochure.asking_price_yen:
        raise ValueError("asking_price_yen が抽出できていません。ユーザー入力が必要")
    if not brochure.structure:
        needs.append("structure")
        structure = "rc"  # 区分の最頻値
        derived.append("structure=rc (default)")
    else:
        structure = brochure.structure

    build_ym = _build_year_month(brochure.build_year_month)
    if not build_ym:
        needs.append("build_year_month")
        build_ym = f"{acquisition_year - 15:04d}-04"  # 仮の築15年
        derived.append("build_year_month=15年前 (default)")

    # 面積: 区分は exclusive、一棟は building を採用
    area = brochure.exclusive_area_sqm or brochure.building_area_sqm
    if not area:
        needs.append("building_area_sqm")
        area = 40.0
        derived.append("building_area_sqm=40㎡ (default)")

    property_type = "kuubun"  # v1 は区分前提
    if brochure.num_units and brochure.num_units > 1:
        property_type = "ittou_apt"

    land, building = _land_building_split(brochure.asking_price_yen)

    # --- 賃料 ---
    gpi = _gpi_monthly(brochure)
    if not gpi:
        needs.append("gpi_monthly_yen")
        gpi = max(50_000, int(brochure.asking_price_yen * 0.05 / 12))
        derived.append("gpi_monthly_yen=価格*5%/12 (default)")

    # --- 自己資金 ---
    if equity_yen is None:
        equity_yen = int(brochure.asking_price_yen * (1 - _DEFAULTS["ltv_ratio"]))
        derived.append(f"equity_yen={equity_yen} (LTV70% default)")

    loan_amount = brochure.asking_price_yen - equity_yen

    # --- 出口 cap ---
    if brochure.gross_yield_pct:
        exit_cap = max(0.045, brochure.gross_yield_pct / 100.0 + _DEFAULTS["exit_cap_rate_premium"])
    else:
        exit_cap = 0.060
        derived.append("exit_cap_rate=6.0% (default)")

    assumptions = Assumptions(
        property=PropertyAssumptions(
            property_type=property_type,  # type: ignore[arg-type]
            purchase_price_yen=brochure.asking_price_yen,
            land_value_yen=land,
            building_value_yen=building,
            structure=structure,  # type: ignore[arg-type]
            building_completion_ym=build_ym,
            acquisition_year=acquisition_year,
            building_area_sqm=area,
            land_area_sqm=brochure.land_area_sqm,
            num_units=brochure.num_units,
            location_pref=_location_pref(brochure.address),
        ),
        income=IncomeAssumptions(
            gpi_monthly_yen=gpi,
            vacancy_rate=_DEFAULTS["vacancy_rate"],
            rent_growth_rate=_DEFAULTS["rent_growth_rate"],
        ),
        opex=OpexAssumptions(
            management_fee_rate=_DEFAULTS["management_fee_rate"],
            building_mgmt_yen=(brochure.management_fee_monthly_yen or 0) * 12
            + (brochure.repair_reserve_monthly_yen or 0) * 12,
            fixed_property_tax_yen=int(brochure.asking_price_yen * 0.003),  # 粗目
            insurance_yen=20_000,
        ),
        loan=LoanAssumptions(
            loan_amount_yen=loan_amount,
            interest_rate=_DEFAULTS["interest_rate"],
            term_years=_DEFAULTS["term_years"],
        ),
        tax=TaxAssumptions(),
        exit_=ExitAssumptions(
            hold_period_years=_DEFAULTS["hold_period_years"],
            exit_cap_rate=exit_cap,
        ),
        acquisition=AcquisitionAssumptions(
            equity_yen=equity_yen,
            acquisition_cost_rate=_DEFAULTS["acquisition_cost_rate"],
        ),
    )

    if brochure.management_fee_monthly_yen is None:
        needs.append("management_fee_monthly_yen")
    if brochure.repair_reserve_monthly_yen is None:
        needs.append("repair_reserve_monthly_yen")

    return MappingResult(assumptions=assumptions, needs_confirmation=needs, derived=derived)
