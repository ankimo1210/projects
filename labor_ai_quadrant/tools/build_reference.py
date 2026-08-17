"""Rebuild the curated reference tables from published statistics.

Every cell this writes traces back to a published number. The mapping tables
below are the only judgement calls, and they are declared here rather than
buried in the values, so a reviewer can check "is 東証 X the same thing as
government category Y?" without re-deriving the arithmetic.

Run from the repo root::

    uv run python labor_ai_quadrant/tools/build_reference.py

Inputs live in ``_data/sources/`` (trimmed snapshots; see SOURCES for the
download URL of each original). Outputs are the three TOML files under
``src/labor_ai_quadrant/reference/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PKG = Path(__file__).resolve().parents[1]
SRC = PKG / "_data" / "sources"
OUT = PKG / "src" / "labor_ai_quadrant" / "reference"

SOURCES = {
    "vacancy_separation": (
        "厚生労働省「雇用動向調査」令和7年上半期 図表 (表7 産業別未充足求人の状況 / "
        "表4-2 産業、就業形態別入職率・離職率) "
        "https://www.mhlw.go.jp/toukei/itiran/roudou/koyou/doukou/26-1/dl/zuhyo.xlsx"
    ),
    "tankan": (
        "日本銀行「全国企業短期経済観測調査」2026年6月調査 雇用人員判断DI (項目コード608) "
        "https://www.stat-search.boj.or.jp/info/co.zip"
    ),
    "job_openings": (
        "厚生労働省「一般職業紹介状況」長期時系列表21 職業別労働市場関係指標 "
        "(有効求人・有効求職、パート含む常用、2025年計) "
        "https://www.e-stat.go.jp/stat-search/file-download?&statInfId=000040478179&fileKind=0"
    ),
    "overtime": (
        "厚生労働省「毎月勤労統計調査」全国調査 実数 2025年 一般労働者・事業所規模5人以上 "
        "所定外労働時間 "
        "https://www.e-stat.go.jp/stat-search/file-download?&statInfId=000032189776&fileKind=1"
    ),
    "age_industry": (
        "総務省「労働力調査」基本集計 年次 2025年 年齢階級，産業別就業者数 (e-Stat 0003007108)"
    ),
    "mix": (
        "総務省「労働力調査」基本集計 年次 2025年 産業，職業別就業者数 表2-5-1 (e-Stat 0003024266)"
    ),
    "ilo": (
        "Gmyrek et al. (2025) ILO Working Paper 140, Final_Scores_ISCO08 "
        "https://github.com/pgmyrek/2025_GenAI_scores_ISCO08"
    ),
}

# --------------------------------------------------------------------------
# 東証33業種マスタ。各列がその業種を「どの公表区分で代表させるか」を宣言する。
#   lfs      : 労働力調査の産業コード (0003024266 / 0003007108 共通、複数なら合算)
#   koyou    : 雇用動向調査の産業大分類ラベル (複数なら常用労働者数で加重平均)
#   mkt      : 毎月勤労統計の産業大分類コード (複数なら労働者数で加重平均)
#   tankan   : 日銀短観の業種コード (複数なら単純平均)
# --------------------------------------------------------------------------
MFG_KOYOU = ("製造業",)
SERVICE_KOYOU = (
    "学術研究,\n専門・技術サービス業",
    "宿泊業，\n飲食\nサービス業",
    "生活関連サービス業,\n娯楽業",
    "教育，\n学習\n支援業",
    "サービス業\n(他に分類\nされない\nもの)",
)
SERVICE_MKT = ("L", "M", "N", "O", "R")

SECTORS: list[dict] = [
    dict(code="0050", name="水産・農林業", lfs=["01", "05"], koyou=("計",), mkt=("TL",), tankan=["0000"]),
    dict(code="1050", name="鉱業", lfs=["08"], koyou=("鉱業，\n採石業，\n砂利採取業",), mkt=("C",), tankan=["2500"]),
    dict(code="2050", name="建設業", lfs=["09"], koyou=("建設業",), mkt=("D",), tankan=["2011"]),
    dict(code="3050", name="食料品", lfs=["11", "12"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1010"]),
    dict(code="3100", name="繊維製品", lfs=["13"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1020"]),
    dict(code="3150", name="パルプ・紙", lfs=["16"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1050"]),
    dict(code="3200", name="化学", lfs=["18", "20"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1060"]),
    dict(code="3250", name="医薬品", lfs=["18"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1060"]),
    dict(code="3300", name="石油・石炭製品", lfs=["19"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1070"]),
    dict(code="3350", name="ゴム製品", lfs=["21"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1500"]),
    dict(code="3400", name="ガラス・土石製品", lfs=["23"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1100"]),
    dict(code="3450", name="鉄鋼", lfs=["24"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1110"]),
    dict(code="3500", name="非鉄金属", lfs=["25"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1120"]),
    dict(code="3550", name="金属製品", lfs=["26"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1130"]),
    dict(code="3600", name="機械", lfs=["27", "28"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1141", "1142"]),
    dict(code="3650", name="電気機器", lfs=["30", "31", "32"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1150"]),
    dict(code="3700", name="輸送用機器", lfs=["33"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1160"]),
    dict(code="3750", name="精密機器", lfs=["29"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1143"]),
    dict(code="3800", name="その他製品", lfs=["15", "17", "34"], koyou=MFG_KOYOU, mkt=("E",), tankan=["1500"]),
    dict(code="4050", name="電気・ガス業", lfs=["35"], koyou=("電気・ガス・熱供給・\n水道業",), mkt=("F",), tankan=["2060"]),
    dict(code="5050", name="陸運業", lfs=["43", "44", "45"], koyou=("運輸業，\n郵便業",), mkt=("H",), tankan=["2040"]),
    dict(code="5100", name="海運業", lfs=["46"], koyou=("運輸業，\n郵便業",), mkt=("H",), tankan=["2040"]),
    dict(code="5150", name="空運業", lfs=["47"], koyou=("運輸業，\n郵便業",), mkt=("H",), tankan=["2040"]),
    dict(code="5200", name="倉庫・運輸関連業", lfs=["48", "49"], koyou=("運輸業，\n郵便業",), mkt=("H",), tankan=["2040"]),
    dict(code="5250", name="情報・通信業", lfs=["37", "38", "39", "40", "41"], koyou=("情報\n通信業",), mkt=("G",), tankan=["2059"]),
    dict(code="6050", name="卸売業", lfs=["52"], koyou=("卸売業，\n小売業",), mkt=("I",), tankan=["2021"]),
    dict(code="6100", name="小売業", lfs=["53", "54", "55", "56", "57"], koyou=("卸売業，\n小売業",), mkt=("I",), tankan=["2024"]),
    dict(code="7050", name="銀行業", lfs=["58"], koyou=("金融業，\n保険業",), mkt=("J",), tankan=["5100"]),
    dict(code="7100", name="証券、商品先物取引業", lfs=["58"], koyou=("金融業，\n保険業",), mkt=("J",), tankan=["5400"]),
    dict(code="7150", name="保険業", lfs=["58"], koyou=("金融業，\n保険業",), mkt=("J",), tankan=["5500"]),
    dict(code="7200", name="その他金融業", lfs=["58"], koyou=("金融業，\n保険業",), mkt=("J",), tankan=["5600"]),
    dict(code="8050", name="不動産業", lfs=["60"], koyou=("不動産業, 物品\n賃貸業",), mkt=("K",), tankan=["2012"]),
    dict(code="9050", name="サービス業", lfs=["62", "67", "71", "75", "85"], koyou=SERVICE_KOYOU, mkt=SERVICE_MKT, tankan=["2081", "2082"]),
]

# --------------------------------------------------------------------------
# 職業区分。労働力調査「職業（平成21年12月改定）」の区分をそのまま採り、
# 大分類のうち AI感応度が内部で大きく割れる 3 つ（専門的・技術的 / 事務 / 販売）
# だけ中分類まで割った 18 区分。この 18 区分は元表の完全な分割になっている。
#   lfs   : 労働力調査 cat02 コード
#   isco  : ILO WP140 のスコアを平均する ISCO-08 コード接頭辞
#   drop  : isco から除く接頭辞（他区分に割り当てたもの）
#   mhlw  : 一般職業紹介状況（厚生労働省編職業分類）の行ラベル
# --------------------------------------------------------------------------
OCCUPATIONS: list[dict] = [
    dict(key="mgmt", lfs="001", name="管理的職業従事者", isco=["11", "12", "13", "14"], drop=[],
         mhlw=["管理的職業従事者"]),
    dict(key="tech", lfs="003", name="技術者", isco=["21", "25", "31", "35"], drop=[],
         mhlw=["製造技術者（開発）", "製造技術者（開発を除く）", "建築・土木・測量技術者",
               "情報処理・通信技術者", "その他の技術者"]),
    dict(key="health_prof", lfs="004", name="保健医療従事者", isco=["22", "32"], drop=[],
         mhlw=["医師，歯科医師，獣医師，薬剤師", "保健師，助産師，看護師", "医療技術者",
               "その他の保健医療従事者"]),
    dict(key="teacher", lfs="005", name="教員", isco=["23"], drop=[],
         mhlw=["その他の専門的職業"]),
    dict(key="other_prof", lfs="006", name="その他の専門的・技術的職業従事者",
         isco=["24", "26", "33", "34"], drop=["243", "3321", "3322", "3324", "3334"],
         mhlw=["社会福祉専門職業従事者", "美術家，デザイナー，写真家，映像撮影者", "その他の専門的職業"]),
    dict(key="clerk_general", lfs="008", name="一般事務従事者", isco=["41", "44"], drop=[],
         mhlw=["一般事務従事者", "事務用機器操作員"]),
    dict(key="clerk_accounting", lfs="009", name="会計事務従事者", isco=["43"], drop=[],
         mhlw=["会計事務従事者"]),
    dict(key="clerk_other", lfs="010", name="その他の事務従事者", isco=["42"], drop=[],
         mhlw=["生産関連事務従事者", "営業・販売事務従事者", "外勤事務従事者", "運輸・郵便事務従事者"]),
    dict(key="sales_retail", lfs="012", name="商品販売従事者", isco=["52"], drop=["5244"],
         mhlw=["商品販売従事者"]),
    dict(key="sales_broker", lfs="013", name="販売類似職業従事者", isco=["3321", "3324", "3334"], drop=[],
         mhlw=["販売類似職業従事者"]),
    dict(key="sales_field", lfs="014", name="営業職業従事者", isco=["243", "3322", "5244"], drop=[],
         mhlw=["営業職業従事者"]),
    dict(key="service", lfs="015", name="サービス職業従事者", isco=["51", "53"], drop=[],
         mhlw=["家庭生活支援サービス職業従事者", "介護サービス職業従事者", "保健医療サービス職業従事者",
               "生活衛生サービス職業従事者", "飲食物調理従事者", "接客・給仕職業従事者",
               "居住施設・ビル等管理人", "その他のサービス職業従事者"]),
    dict(key="security", lfs="021", name="保安職業従事者", isco=["54"], drop=[],
         mhlw=["保安職業従事者"]),
    dict(key="agri", lfs="022", name="農林漁業従事者", isco=["6", "92"], drop=[],
         mhlw=["農林漁業従事者"]),
    dict(key="production", lfs="023", name="生産工程従事者",
         isco=["72", "73", "74", "75", "81", "82"], drop=["811"],
         mhlw=["生産設備制御・監視従事者（金属製品）", "生産設備制御・監視従事者（金属製品を除く）",
               "機械組立設備制御・監視従事者", "製品製造・加工処理従事者（金属製品）",
               "製品製造・加工処理従事者（金属製品を除く）", "機械組立従事者", "機械整備・修理従事者",
               "製品検査従事者（金属製品）", "製品検査従事者（金属製品を除く）", "機械検査従事者",
               "生産関連・生産類似作業従事者"]),
    dict(key="transport", lfs="031", name="輸送・機械運転従事者", isco=["83"], drop=[],
         mhlw=["鉄道運転従事者", "自動車運転従事者", "船舶・航空機運転従事者", "その他の輸送従事者",
               "定置・建設機械運転従事者"]),
    dict(key="construction", lfs="032", name="建設・採掘従事者", isco=["71", "811"], drop=[],
         mhlw=["建設躯体工事従事者", "建設従事者（建設躯体工事従事者を除く）", "電気工事従事者",
               "土木作業従事者", "採掘従事者"]),
    dict(key="manual", lfs="033", name="運搬・清掃・包装等従事者",
         isco=["91", "93", "94", "95", "96"], drop=[],
         mhlw=["運搬従事者", "清掃従事者", "包装従事者", "その他の運搬・清掃・包装等従事者"]),
]

# 規制・免許・説明責任によって AI 実装が遅れる度合い。実効の掛け目は (1 - drag)。
# 出典のある数値ではない analyst 判断。根拠は docs/METHODOLOGY.md の一覧を参照。
REGULATION_DRAG: dict[str, float] = {
    "水産・農林業": 0.05, "鉱業": 0.08, "建設業": 0.10, "食料品": 0.08, "繊維製品": 0.03,
    "パルプ・紙": 0.03, "化学": 0.08, "医薬品": 0.18, "石油・石炭製品": 0.12, "ゴム製品": 0.03,
    "ガラス・土石製品": 0.03, "鉄鋼": 0.05, "非鉄金属": 0.05, "金属製品": 0.03, "機械": 0.05,
    "電気機器": 0.05, "輸送用機器": 0.08, "精密機器": 0.10, "その他製品": 0.03,
    "電気・ガス業": 0.18, "陸運業": 0.15, "海運業": 0.12, "空運業": 0.18,
    "倉庫・運輸関連業": 0.08, "情報・通信業": 0.03, "卸売業": 0.03, "小売業": 0.03,
    "銀行業": 0.15, "証券、商品先物取引業": 0.15, "保険業": 0.15, "その他金融業": 0.12,
    "不動産業": 0.08, "サービス業": 0.08,
}

# 労働力調査の産業細分 → それを含む日本標準産業分類の大分類。
# 元表は万人単位の整数なので、小さい産業では職業別の内訳がほとんど 0 に丸められ、
# 残った 1 セルが 100% になってしまう。観測できたセルはそのまま使い、
# 「産業合計 - 内訳の合計」の残差を大分類の職業構成で按分して埋める。
LFS_PARENT: dict[str, str] = {
    "01": "01", "05": "05", "08": "00", "09": "09",
    **{c: "10" for c in ("11", "12", "13", "15", "16", "17", "18", "19", "20", "21",
                         "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34")},
    "35": "35",
    **{c: "36" for c in ("37", "38", "39", "40", "41")},
    **{c: "42" for c in ("43", "44", "45", "46", "47", "48", "49", "50")},
    **{c: "51" for c in ("52", "53", "54", "55", "56", "57")},
    "58": "58", "60": "59", "61": "59",
    **{c: "62" for c in ("62", "63", "64", "65", "66")},
    **{c: "67" for c in ("67", "68", "69", "70")},
    **{c: "71" for c in ("71", "72", "73", "74")},
    **{c: "75" for c in ("75", "76", "77")},
    **{c: "85" for c in ("85", "86", "87", "88", "89", "90", "91", "92", "93")},
}

#: 55歳以上比率で産業細分の内訳が使えないと判断する就業者数（万人）の下限。
AGE_MIN_BASE = 20.0

WEIGHTS = {
    "vacancy_rate_pct": 0.30,
    "employment_di_shortage": 0.30,
    "job_openings_ratio": 0.20,
    "age55_share_pct": 0.10,
    "separation_rate_pct": 0.05,
    "overtime_hours_month": 0.05,
}


# ---------------------------------------------------------------- loaders --
def load_koyou() -> tuple[pd.Series, pd.Series]:
    """欠員率 (2025年6月末) と離職率 (令和7年上半期) を産業大分類で返す。"""
    path = SRC / "koyou_doukou_r7_zuhyo.xlsx"
    v = pd.read_excel(path, sheet_name="表７産業別未充足求人の状況", header=None)
    labels = v.iloc[3, 6:23].tolist()
    vacancy = pd.Series(v.iloc[13, 6:23].astype(float).tolist(), index=labels)

    s = pd.read_excel(path, sheet_name="表4-2産業、就業形態別入職率・離職率・入職超過率", header=None)
    body = s.iloc[6:23]
    names = body[1].fillna(body[2])
    separation = pd.Series(body[5].astype(float).tolist(), index=names.tolist())
    return vacancy, separation


def load_tankan() -> pd.Series:
    """短観 雇用人員判断DI (2026年6月調査、単純集計・全規模・最近)。"""
    rows = pd.read_csv(SRC / "boj_tankan_co.csv", header=None,
                       names=["code", "freq", "period", "value"], dtype=str)
    rows = rows[rows["period"] == "202602"]
    sel = rows[rows["code"].str.match(r"TK99F\d{4}608GCQ00000")].copy()
    sel["industry"] = sel["code"].str[5:9]
    return pd.Series(sel["value"].astype(float).values, index=sel["industry"].values)


def load_job_openings() -> pd.Series:
    """職業別 有効求人倍率。求人・求職の実数から区分を組み替えて計算する。

    集計後の倍率を平均すると分母が壊れるので、Σ有効求人 / Σ有効求職 で出す。
    """
    path = SRC / "mhlw_occupation_market_r8_06.xlsx"
    xl = pd.ExcelFile(path)

    def annual(keyword: str) -> pd.Series:
        sheet = next(s for s in xl.sheet_names if keyword in s and "パート含む" in s)
        df = xl.parse(sheet, header=None)
        body = df.iloc[5:].dropna(subset=[0])
        return pd.Series(pd.to_numeric(body[3], errors="coerce").values,
                         index=body[0].astype(str).str.strip().values)

    openings, seekers = annual("有効求人（"), annual("有効求職（")
    out = {}
    for occ in OCCUPATIONS:
        labels = [lab for lab in occ["mhlw"] if lab in openings.index and lab in seekers.index]
        if not labels:
            raise ValueError(f"job openings: no 職業安定業務統計 label matched for {occ['key']}")
        num = openings[labels].sum()
        den = seekers[labels].sum()
        out[occ["key"]] = float(num / den)
    return pd.Series(out)


def load_overtime() -> pd.Series:
    """所定外労働時間 (2025年平均、一般労働者、事業所規模5人以上) と労働者数。"""
    df = pd.read_csv(SRC / "mkt_jissu.csv", encoding="cp932",
                     dtype={"産業分類": str, "月": str, "規模": str})
    cur = df[(df["年"] == 2025) & (df["月"] == "CY") & (df["規模"] == "0") & (df["就業形態"] == 1)]
    cur = cur.assign(ind=cur["産業分類"].str.strip())
    return cur.set_index("ind")[["所定外労働時間", "本月末労働者数"]]


def load_age_share() -> pd.Series:
    """産業別 55歳以上就業者比率 (2025年、労働力調査)。"""
    d = json.loads((SRC / "estat_lfs_age_industry_2025.json").read_text())["STATISTICAL_DATA"]
    vals = d["DATA_INF"]["VALUE"]
    frame = pd.DataFrame([{"ind": v["@cat01"], "age": v["@cat03"], "n": pd.to_numeric(v["$"], errors="coerce")}
                          for v in vals])
    piv = frame.pivot_table(index="ind", columns="age", values="n", aggfunc="first")
    return piv


def load_mix() -> pd.DataFrame:
    """産業 × 職業 の就業者数 (2025年、労働力調査 表2-5-1)。"""
    d = json.loads((SRC / "estat_lfs_2_5_1_2025.json").read_text())["STATISTICAL_DATA"]
    vals = d["DATA_INF"]["VALUE"]
    frame = pd.DataFrame([{"ind": v["@cat04"], "occ": v["@cat02"], "n": pd.to_numeric(v["$"], errors="coerce")}
                          for v in vals])
    return frame.pivot_table(index="ind", columns="occ", values="n", aggfunc="first")


def load_ilo_potentials() -> pd.Series:
    """ILO WP140 の GenAI exposure を 18 職業区分に集約する (0-100 に換算)。"""
    df = pd.read_excel(SRC / "ilo_wp140_scores.xlsx",
                       usecols=["ISCO_08", "Title", "mean_score_2025"])
    occ = df.groupby("ISCO_08", as_index=False)["mean_score_2025"].first()
    occ["ISCO_08"] = occ["ISCO_08"].astype(int).astype(str).str.zfill(4)

    out = {}
    for spec in OCCUPATIONS:
        keep = occ[occ["ISCO_08"].str.startswith(tuple(spec["isco"]))]
        if spec["drop"]:
            keep = keep[~keep["ISCO_08"].str.startswith(tuple(spec["drop"]))]
        if keep.empty:
            raise ValueError(f"ILO: no ISCO code matched {spec['key']}")
        out[spec["key"]] = round(float(keep["mean_score_2025"].mean()) * 100.0, 1)
    return pd.Series(out)


# ------------------------------------------------------------- assembling --
def weighted(values: pd.Series, weights: pd.Series, keys: tuple[str, ...]) -> float:
    keys = [k for k in keys if k in values.index and pd.notna(values[k])]
    if not keys:
        raise ValueError(f"no data for {keys}")
    w = weights.reindex(keys).fillna(0.0)
    if w.sum() <= 0:
        return float(values[keys].mean())
    return float((values[keys] * w).sum() / w.sum())


def older_share(age: pd.DataFrame, codes: list[str]) -> float:
    """55歳以上比率。

    元表は産業によって「55～64歳」を1セルで持つか「55～59 + 60～64」で持つかが
    分かれるので両方を見る。就業者数の小さい産業では階級別が全部 0 に丸められて
    比率が 0 になってしまうため、その場合は大分類の比率で代える。
    """

    def compute(idx: list[str]) -> tuple[float, float]:
        rows = age.reindex(idx)
        total = float(rows["00"].sum())
        mid = float(rows["15"].sum())
        if mid == 0.0:
            mid = float(rows["16"].sum()) + float(rows["17"].sum())
        return mid + float(rows["18"].sum()), total

    older, total = compute(codes)
    if total >= AGE_MIN_BASE and older > 0:
        return older / total
    parents = sorted({LFS_PARENT[c] for c in codes})
    older, total = compute(parents)
    if total > 0 and older > 0:
        return older / total
    older, total = compute(["00"])
    return older / total


def build_shortage(mix_counts: pd.DataFrame) -> pd.DataFrame:
    vacancy, separation = load_koyou()
    di = load_tankan()
    jar_occ = load_job_openings()
    overtime = load_overtime()
    age = load_age_share()

    # 東証サービス業の 5 大分類を束ねる重みは毎月勤労統計の労働者数
    mkt_weights = overtime["本月末労働者数"]
    koyou_weights = pd.Series(
        {
            "計": 1.0,
            "鉱業，\n採石業，\n砂利採取業": mkt_weights.get("C", 1.0),
            "建設業": mkt_weights.get("D", 1.0),
            "製造業": mkt_weights.get("E", 1.0),
            "電気・ガス・熱供給・\n水道業": mkt_weights.get("F", 1.0),
            "情報\n通信業": mkt_weights.get("G", 1.0),
            "運輸業，\n郵便業": mkt_weights.get("H", 1.0),
            "卸売業，\n小売業": mkt_weights.get("I", 1.0),
            "金融業，\n保険業": mkt_weights.get("J", 1.0),
            "不動産業, 物品\n賃貸業": mkt_weights.get("K", 1.0),
            "学術研究,\n専門・技術サービス業": mkt_weights.get("L", 1.0),
            "宿泊業，\n飲食\nサービス業": mkt_weights.get("M", 1.0),
            "生活関連サービス業,\n娯楽業": mkt_weights.get("N", 1.0),
            "教育，\n学習\n支援業": mkt_weights.get("O", 1.0),
            "医療，\n福祉": mkt_weights.get("P", 1.0),
            "複合\nサービス\n事業": mkt_weights.get("Q", 1.0),
            "サービス業\n(他に分類\nされない\nもの)": mkt_weights.get("R", 1.0),
        }
    )
    # 離職率シートは同じ産業を改行なしで持つので別名で引く
    sep_alias = {
        "計": "産業計", "鉱業，\n採石業，\n砂利採取業": "鉱業，採石業，砂利採取業",
        "建設業": "建設業", "製造業": "製造業",
        "電気・ガス・熱供給・\n水道業": "電気・ガス・熱供給・水道業", "情報\n通信業": "情報通信業",
        "運輸業，\n郵便業": "運輸業，郵便業", "卸売業，\n小売業": "卸売業，小売業",
        "金融業，\n保険業": "金融業，保険業", "不動産業, 物品\n賃貸業": "不動産業，物品賃貸業",
        "学術研究,\n専門・技術サービス業": "学術研究，専門・技術サービス業",
        "宿泊業，\n飲食\nサービス業": "宿泊業，飲食サービス業",
        "生活関連サービス業,\n娯楽業": "生活関連サービス業，娯楽業",
        "教育，\n学習\n支援業": "教育，学習支援業", "医療，\n福祉": "医療，福祉",
        "複合\nサービス\n事業": "複合サービス事業",
        "サービス業\n(他に分類\nされない\nもの)": "サービス業（他に分類されないもの）",
    }

    rows = []
    for spec in SECTORS:
        name = spec["name"]
        # 有効求人倍率: その業種の職業構成で職業別倍率を加重平均する
        share = mix_counts.loc[name]
        jar = float((share * jar_occ.reindex(share.index)).sum() / share.sum())

        age_share = older_share(age, spec["lfs"])

        rows.append(
            {
                "code": spec["code"],
                "name": name,
                "vacancy_rate_pct": round(weighted(vacancy, koyou_weights, spec["koyou"]), 2),
                "employment_di_shortage": round(-float(di.reindex(spec["tankan"]).mean()), 1),
                "job_openings_ratio": round(jar, 3),
                "age55_share_pct": round(age_share * 100.0, 1),
                "separation_rate_pct": round(
                    weighted(
                        separation,
                        pd.Series({sep_alias[k]: koyou_weights[k] for k in koyou_weights.index}),
                        tuple(sep_alias[k] for k in spec["koyou"]),
                    ),
                    2,
                ),
                "overtime_hours_month": round(
                    weighted(overtime["所定外労働時間"], mkt_weights, spec["mkt"]), 2
                ),
            }
        )
    return pd.DataFrame(rows).set_index("name", drop=False)


def build_mix_counts() -> pd.DataFrame:
    """東証33業種 × 18職業区分 の就業者数 (万人)。

    丸めで消えた分（産業合計 - 職業内訳の合計）は、その産業を含む大分類の
    職業構成で按分して戻す。これをやらないと、就業者数の小さい業種で
    残った1セルが 100% になる（鉱業が「輸送・機械運転 100%」になる等）。
    """
    raw = load_mix()
    keys = [o["key"] for o in OCCUPATIONS]
    codes = [o["lfs"] for o in OCCUPATIONS]

    def shape(industry_codes: list[str]) -> pd.Series:
        block = raw.reindex(industry_codes)[codes].sum(axis=0, min_count=1).fillna(0.0)
        block.index = keys
        total = block.sum()
        return block / total if total > 0 else block

    rows, imputed = {}, {}
    for spec in SECTORS:
        block = raw.reindex(spec["lfs"])
        detail = block[codes].sum(axis=0, min_count=1).fillna(0.0)
        detail.index = keys
        total = float(block["000"].sum())
        residual = max(0.0, total - float(detail.sum()))
        parents = sorted({LFS_PARENT[c] for c in spec["lfs"]})
        rows[spec["name"]] = detail + residual * shape(parents)
        imputed[spec["name"]] = residual / total if total > 0 else 0.0

    out = pd.DataFrame(rows).T
    out.attrs["imputed_share"] = pd.Series(imputed)
    return out


# ----------------------------------------------------------------- output --
def fmt(v: float, nd: int) -> str:
    return f"{v:.{nd}f}"


def write_shortage(short: pd.DataFrame) -> None:
    lines = [
        "# 東証33業種別 人手不足指標（公表統計から機械的に生成 / generated, do not hand-edit）",
        "#",
        "# tools/build_reference.py が出力する。すべて「高いほど人手不足が深刻」の向き。",
        "#",
        "# 出典 (sources):",
    ]
    for key in ("vacancy_separation", "tankan", "job_openings", "age_industry", "overtime"):
        lines.append(f"#   {SOURCES[key]}")
    lines += [
        "#",
        "# 指標の定義:",
        "#   vacancy_rate_pct        欠員率 = 未充足求人数 ÷ 常用労働者数（2025年6月末日現在。全産業 2.6%）",
        "#   employment_di_shortage  短観 雇用人員判断DI の符号反転（DIは「過剰」-「不足」なので",
        "#                           不足が深刻なほど負。反転して「高いほど不足」に揃えている。全産業 +37）",
        "#   job_openings_ratio      職業別有効求人倍率をその業種の職業構成比で加重平均した値",
        "#                           （Σ有効求人 ÷ Σ有効求職。2025年平均、パート含む常用）",
        "#   age55_share_pct         就業者に占める55歳以上比率（2025年平均）",
        "#   separation_rate_pct     離職率（令和7年上半期）",
        "#   overtime_hours_month    所定外労働時間（2025年平均、一般労働者、事業所規模5人以上、時間/月）",
        "#",
        "# 粒度の但し書き（公表区分がそこまで割れていないため同値になる組）:",
        "#   欠員率・離職率・所定外労働時間 … 製造業16業種はすべて「製造業」の値。",
        "#     陸運/海運/空運/倉庫運輸は「運輸業，郵便業」、銀行/証券/保険/その他金融は「金融業，保険業」、",
        "#     卸売/小売は「卸売業，小売業」の値。水産・農林業は調査対象外なので産業計を当てている。",
        "#   短観DI … 医薬品は化学、ゴム製品とその他製品はその他製造業。水産・農林業は全産業。",
        "#   サービス業 … 学術研究/宿泊飲食/生活関連娯楽/教育/サービス業(他) を労働者数で加重平均。",
        "",
        "# NOTE: TOML はテーブルヘッダ以降のキーをそのテーブルに属させるため、",
        "#       トップレベルの配列 (sector) を先に、[meta] / [weights] を末尾に置いている。",
        "",
        "sector = [",
    ]
    width = max(len(s["name"]) * 2 for s in SECTORS)
    for spec in SECTORS:
        r = short.loc[spec["name"]]
        pad = " " * (width - len(spec["name"]) * 2)
        lines.append(
            f'  {{ code = "{r["code"]}", name = "{r["name"]}",{pad} '
            f'vacancy_rate_pct = {fmt(r["vacancy_rate_pct"], 2)}, '
            f'employment_di_shortage = {fmt(r["employment_di_shortage"], 1)}, '
            f'job_openings_ratio = {fmt(r["job_openings_ratio"], 3)}, '
            f'age55_share_pct = {fmt(r["age55_share_pct"], 1)}, '
            f'separation_rate_pct = {fmt(r["separation_rate_pct"], 2)}, '
            f'overtime_hours_month = {fmt(r["overtime_hours_month"], 2)} }},'
        )
    lines += [
        "]",
        "",
        "[meta]",
        'vintage = "2026-08"',
        'basis = "published statistics, mechanically mapped to the 33 TSE sectors"',
        "overall_anchor = { vacancy_rate_pct = 2.6, vacancy_asof = \"2025-06-30\", "
        "employment_di_shortage = 37.0, employment_di_asof = \"2026-06\", "
        "job_openings_ratio = 1.12, job_openings_asof = \"2025\" }",
        "",
        "# 合成スコアの重み。欠員率と短観DIが「いま採れていない」ことの最も直接的な測度なので重い。",
        "# 有効求人倍率はハローワーク経由の求人・求職しか映さない（大卒総合職・中途エージェント経由が",
        "# 抜ける）ため 0.20 に抑えている。年齢構成・離職率・残業時間は不足の帰結ないし将来圧力。",
        "[weights]",
    ]
    lines += [f"{k} = {v:.2f}" for k, v in WEIGHTS.items()]
    (OUT / "sector_labor_shortage.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_occupations(pot: pd.Series) -> None:
    lines = [
        "# 職業別 生成AI代替ポテンシャル（公表データから機械的に生成 / generated, do not hand-edit）",
        "#",
        f"# 出典: {SOURCES['ilo']}",
        "#",
        "# ai_potential は ILO WP140 の occupation-level GenAI exposure score（0-1）を",
        "# 100倍したもの。ILO の指数は「その職業のタスクのうち生成AIに晒されている割合」という",
        "# 単一の数値であり、物理的自動化（ロボティクス・自動運転）は測っていない。",
        "# したがってこの軸は『生成AIで代替しうる労働の割合』であって、",
        "# 『自動化全般で代替しうる労働の割合』ではない。倉庫AMRや自動運転はこの軸の外にある。",
        "#",
        "# 職業区分は労働力調査「職業（平成21年12月改定）」に合わせた18区分。",
        "# ISCO-08 の該当グループに属する4桁職業のスコアを単純平均している",
        "# （ISCO 4桁ごとの日本国内就業者数が無いため、加重平均はできない）。",
        "",
        "# NOTE: トップレベル配列を先に、[meta] を末尾に置いている（TOML のテーブル解釈のため）。",
        "",
        "occupation = [",
    ]
    width = max(len(o["name"]) * 2 for o in OCCUPATIONS)
    for spec in OCCUPATIONS:
        pad = " " * (width - len(spec["name"]) * 2)
        isco = " ".join(spec["isco"])
        drop = f" 除く {' '.join(spec['drop'])}" if spec["drop"] else ""
        lines.append(
            f'  {{ key = "{spec["key"]}", lfs_code = "{spec["lfs"]}", name = "{spec["name"]}",{pad} '
            f'ai_potential = {fmt(pot[spec["key"]], 1)}, isco = "{isco}{drop}" }},'
        )
    lines += [
        "]",
        "",
        "[meta]",
        'vintage = "2025-05"',
        'basis = "ILO WP140 (Gmyrek et al. 2025) occupation-level GenAI exposure, ISCO-08"',
        'scale = "0-100"',
    ]
    (OUT / "occupation_ai_exposure.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_mix(counts: pd.DataFrame) -> None:
    shares = counts.div(counts.sum(axis=1), axis=0) * 100.0
    keys = [o["key"] for o in OCCUPATIONS]
    lines = [
        "# 東証33業種 × 職業18区分 の就業者構成比（%）（公表データから生成 / generated, do not hand-edit）",
        "#",
        f"# 出典: {SOURCES['mix']}",
        "#",
        "# AI代替可能性軸の実質的なエンジン:",
        "#   sector_ai_potential = Σ_o ( share[sector][o] × ai_potential[o] ) × (1 - regulation_drag[sector])",
        "#",
        "# 元表は万人単位の整数なので、小さい業種（空運・海運など）は構成比が粗い。",
        "# 労働力調査に無い切り分けはそのまま同値になる:",
        "#   銀行業/証券、商品先物取引業/保険業/その他金融業 … すべて「金融業，保険業」の職業構成。",
        "#   医薬品 … 化学工業に含まれるため化学と同じ。",
        "# regulation_drag は公表統計ではなく analyst 判断（docs/METHODOLOGY.md に一覧と根拠）。",
        "",
        "# NOTE: トップレベル配列を先に、[meta] を末尾に置いている（TOML のテーブル解釈のため）。",
        "",
        "sector = [",
    ]
    width = max(len(s["name"]) * 2 for s in SECTORS)
    for spec in SECTORS:
        name = spec["name"]
        pad = " " * (width - len(name) * 2)
        cells = ", ".join(f"{k} = {shares.loc[name, k]:.2f}" for k in keys)
        lines.append(
            f'  {{ code = "{spec["code"]}", name = "{name}",{pad} '
            f'regulation_drag = {REGULATION_DRAG[name]:.2f}, {cells} }},'
        )
    lines += [
        "]",
        "",
        "[meta]",
        'vintage = "2025"',
        'basis = "総務省 労働力調査 基本集計 2025年 産業，職業別就業者数 (表2-5-1)"',
        f"occupation_keys = {json.dumps(keys)}",
    ]
    (OUT / "sector_occupation_mix.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    counts = build_mix_counts()
    pot = load_ilo_potentials()
    short = build_shortage(counts)

    write_occupations(pot)
    write_mix(counts)
    write_shortage(short)

    print("=== ai_potential (ILO WP140, 0-100) ===")
    for spec in OCCUPATIONS:
        print(f"  {spec['name']:<22} {pot[spec['key']]:>5.1f}   ISCO {' '.join(spec['isco'])}")
    imputed = counts.attrs["imputed_share"].sort_values(ascending=False)
    print("\n=== 職業構成のうち丸め残差を大分類の形で埋めた割合 (上位) ===")
    print((imputed[imputed > 0.02] * 100).round(1).to_string())

    print("\n=== shortage indicators ===")
    print(short.drop(columns=["name"]).to_string())
    print("\nwrote 3 TOML files to", OUT)


if __name__ == "__main__":
    main()
