"""
property_scraper.py
不動産物件ページ（楽待・健美家など）から投資情報を抽出する。

フロー:
1. fetch_property_html()  - requests でHTMLを取得
2. extract_property_data() - BeautifulSoup でテキスト化 → Ollama (gemma3) でJSON抽出
"""
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import get_logger

logger = get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

_STRUCTURE_MAP = {
    "木造": "wood",
    "木骨モルタル": "wood_mortar",
    "木造モルタル": "wood_mortar",
    "RC": "rc",
    "鉄筋コンクリート": "rc",
    "RC造": "rc",
    "SRC": "src",
    "鉄骨鉄筋コンクリート": "src",
    "SRC造": "src",
    "鉄骨": "steel",
    "鉄骨造": "steel",
    "S造": "steel",
    "軽量鉄骨": "steel",
    "ALC": "steel",
}

# 構造コード → 日本語表示
STRUCTURE_JP: dict[str, str] = {
    "wood":        "木造",
    "wood_mortar": "木骨モルタル",
    "rc":          "RC造",
    "src":         "SRC造",
    "steel":       "鉄骨造",
}

# 構造コード → 法定耐用年数（建物、住宅用）
LEGAL_LIFE_YEARS: dict[str, int] = {
    "wood":        22,
    "wood_mortar": 20,
    "rc":          47,
    "src":         47,
    "steel":       34,
}


def remaining_life(structure: Optional[str], age_years: Optional[int]) -> Optional[int]:
    """法定残存耐用年数を返す。耐用年数超過の場合は法定耐用年数×20%（最低1年）。"""
    if not structure or age_years is None:
        return None
    legal = LEGAL_LIFE_YEARS.get(structure)
    if legal is None:
        return None
    rem = legal - age_years
    return rem if rem > 0 else max(1, int(legal * 0.2))


_SYSTEM_PROMPT = (
    "You are a real estate data extraction specialist. "
    "Extract structured property investment data from Japanese real estate listing text. "
    "Return ONLY a valid JSON object. Use null for unavailable fields. "
    "Do not add explanation or markdown. Monetary values in integer yen. "
    "Percentages as float (7.5 means 7.5%, not 0.075)."
)

_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
_OLLAMA_MODEL    = "gemma3:12b"

_SCHEMA_DIR = Path(__file__).parent / "data" / "site_schemas"


def _load_site_schema(platform: str) -> str:
    """サイト固有スキーマMarkdownを読み込む。なければ空文字を返す。"""
    path = _SCHEMA_DIR / f"{platform}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

_USER_PROMPT_TEMPLATE = """\
Extract property data from the following Japanese real estate listing text.

LISTING TEXT:
{text_content}

Return a JSON object with EXACTLY these keys (use null if not found):
{{
  "property_name": <string|null>,
  "address": <string|null>,
  "asking_price_yen": <integer|null>,
  "gross_rent_monthly_yen": <integer|null>,
  "gross_rent_annual_yen": <integer|null>,
  "gross_yield_pct": <float|null>,
  "build_year_month": <"YYYY-MM"|null>,
  "age_years": <integer|null>,
  "structure": <"木造"|"RC"|"鉄骨"|"SRC"|"木骨モルタル"|"軽量鉄骨"|null>,
  "property_type": <"アパート"|"マンション"|"戸建て"|"土地"|"店舗"|"その他"|null>,
  "building_area_sqm": <float|null>,
  "land_area_sqm": <float|null>,
  "land_rights": <string|null>,
  "legal_far_pct": <float|null>,
  "bcr_pct": <float|null>,
  "num_units": <integer|null>,
  "nearest_station": <string|null>,
  "station_walk_min": <integer|null>,
  "floor_plan": <string|null>,
  "num_floors": <integer|null>,
  "land_category": <string|null>,
  "city_planning_area": <string|null>,
  "updated_date": <"YYYY-MM-DD"|null>,
  "transaction_type": <string|null>,
  "listing_date": <"YYYY-MM-DD"|null>,
  "extraction_confidence": <"high"|"partial"|"low">
}}

Rules:
- address: full prefecture+city+district format, e.g. "東京都新宿区西新宿2-8-1"
- asking_price_yen: total sale price as integer yen. "万円" = ×10,000. "7980万円" → 79800000, "1億2000万円" → 120000000. NEVER multiply by 10000 again if already in yen.
- gross_rent_monthly_yen: monthly rent as integer yen. "50万円/月" → 500000, "10.5万円/月" → 105000
- gross_rent_annual_yen: annual rent (想定年間収入) as integer yen. "600.4万円" → 6004000, "126万円" → 1260000
- gross_yield_pct: surface yield percentage (表面利回り). "7.52%" → 7.52
- build_year_month: use "YYYY-01" if only year is known; "1981年10月" → "1981-10"; if "築N年" compute from 2026
- age_years: "築45年" → 45, or compute as 2026 minus build year
- building_area_sqm: look for "建物面積" field. "476.33㎡" → 476.33, "476.33㎡ 公簿" → 476.33
- land_area_sqm: look for "土地面積" field. "416.88㎡ 公簿" → 416.88. Convert 坪 if needed (1坪=3.305785 m²)
- land_rights: look for "土地権利" field. e.g. "所有権", "借地権"
- legal_far_pct: 容積率 as float. "200%" → 200.0, "200/300%" → use lower (200.0)
- bcr_pct: 建蔽率/建ぺい率 as float. "60%" → 60.0
- num_floors: number of above-ground floors. "地上6階" → 6, "4階建て" → 4
- land_category: 地目 field value, e.g. "宅地", "田", "畑"
- city_planning_area: 都市計画区域 field value
- updated_date: 更新日 in YYYY-MM-DD. "2026/04/22" → "2026-04-22"
- nearest_station: use the FIRST station listed in 交通 section. Format example: "交通\n沖縄都市モノレール 浦添前田駅 徒歩32分" → nearest_station="沖縄都市モノレール 浦添前田駅", station_walk_min=32
- station_walk_min: integer minutes from nearest station. "徒歩32分" → 32
- transaction_type: 取引態様 e.g. "一般媒介", "専任媒介", "売主"
- listing_date: 情報登録日 in YYYY-MM-DD format
- extraction_confidence: "high" if 8+ fields found, "partial" if 4-7, "low" if fewer than 4
"""


class ScrapingError(Exception):
    pass


@dataclass
class PropertyData:
    property_name: Optional[str] = None
    address: Optional[str] = None
    asking_price_yen: Optional[int] = None
    gross_rent_monthly_yen: Optional[int] = None
    gross_rent_annual_yen: Optional[int] = None
    gross_yield_pct: Optional[float] = None
    build_year_month: Optional[str] = None
    age_years: Optional[int] = None
    structure: Optional[str] = None
    property_type: Optional[str] = None
    building_area_sqm: Optional[float] = None
    land_area_sqm: Optional[float] = None
    land_rights: Optional[str] = None
    legal_far_pct: Optional[float] = None   # 法定容積率 (%)
    bcr_pct: Optional[float] = None         # 建蔽率 (%)
    num_units: Optional[int] = None
    road_frontage: Optional[str] = None
    nearest_station: Optional[str] = None
    station_walk_min: Optional[int] = None
    floor_plan: Optional[str] = None
    num_floors: Optional[int] = None          # 地上階数
    land_category: Optional[str] = None       # 地目
    city_planning_area: Optional[str] = None  # 都市計画区域
    updated_date: Optional[str] = None        # 更新日
    transaction_type: Optional[str] = None
    listing_date: Optional[str] = None
    platform: str = "unknown"
    extraction_confidence: str = "low"
    raw_extraction: dict = field(default_factory=dict)
    llm_filled_fields: set = field(default_factory=set)  # LLMで補完されたフィールド名


def fetch_property_html(
    url: str,
    timeout: int = 15,
    session: Optional[requests.Session] = None,
    referer: Optional[str] = None,
) -> str:
    """
    物件ページのHTMLを取得する。

    Parameters
    ----------
    session : requests.Session, optional
        呼び出し元で生成・クッキー済みのセッション。省略時は都度新規作成。
    referer : str, optional
        Referer ヘッダー。検索結果ページのURLを渡すとボット判定を回避しやすい。

    Raises
    ------
    ScrapingError
        HTTP エラー・タイムアウト・ボット検知（403）時
    """
    own_session = session is None
    if own_session:
        session = requests.Session()
        session.headers.update(_HEADERS)
    try:
        headers = {"Referer": referer} if referer else {}
        resp = session.get(url, timeout=timeout, allow_redirects=True, headers=headers)
    except requests.exceptions.Timeout as exc:
        raise ScrapingError(f"タイムアウト: {exc}") from exc
    except requests.exceptions.ConnectionError as exc:
        raise ScrapingError(f"接続エラー: {exc}") from exc

    if resp.status_code == 403:
        raise ScrapingError(
            "アクセスが拒否されました (403)。サイトがボット対策を行っている可能性があります。"
            "以下のフォームから手動で物件情報を入力してください。"
        )
    if resp.status_code == 404:
        raise ScrapingError("物件ページが見つかりませんでした (404)。URLを確認してください。")
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        raise ScrapingError(f"HTTPエラー {resp.status_code}: {exc}") from exc

    return resp.text


# LLM補完が意味のあるフィールド（分類・自由記述系）
_LLM_FILLABLE = {
    "property_type", "floor_plan",
    "address", "property_name",
    "gross_yield_pct", "gross_rent_annual_yen", "gross_rent_monthly_yen",
    "build_year_month", "age_years", "structure",
    "building_area_sqm", "land_area_sqm", "land_rights",
    "legal_far_pct", "bcr_pct",
    "num_units", "nearest_station", "station_walk_min",
    "transaction_type", "listing_date",
    "land_category", "city_planning_area",
}


def extract_property_data(html: str, url: str) -> PropertyData:
    """
    HTMLから物件データを抽出して PropertyData を返す。

    Pass 1: regex で構造化フィールドを高速・確実に抽出
    Pass 2: Noneが残ったフィールドのみ Ollama (gemma3) で補完
    """
    platform = _detect_platform(url)
    text = _strip_html_to_text(html, platform=platform)

    # Pass 1: regex-only（raw={} を渡すことでLLM値はすべてNone扱い）
    prop = _build_property_data({}, platform, source_text=text)

    # Pass 2: Noneが残ったフィールドがあればLLMで補完
    none_fields = [
        f for f in _LLM_FILLABLE
        if getattr(prop, f, None) is None
    ]
    if none_fields:
        try:
            raw = _call_claude_extraction(text, platform=platform)
            prop = _fill_missing_from_llm(prop, raw, none_fields)
        except Exception as exc:
            logger.warning("LLM補完失敗: %s", exc)

    return prop


def _fill_missing_from_llm(prop: PropertyData, raw: dict, none_fields: list) -> PropertyData:
    """regexで取れなかったフィールドのみ LLM値で補完する。
    regex取得済みのフィールドは絶対に上書きしない。
    """
    # PropertyData を dict に変換して補完、再構築
    import dataclasses
    d = dataclasses.asdict(prop)
    filled: set = set(d.get("llm_filled_fields") or set())

    conversions = {
        "property_type":         lambda v: _opt_str(v),
        "floor_plan":            lambda v: _opt_str(v),
        "address":               lambda v: _opt_str(v),
        "property_name":         lambda v: _opt_str(v),
        "gross_yield_pct":       lambda v: _opt_float(v),
        "gross_rent_annual_yen": lambda v: _opt_int(v),
        "gross_rent_monthly_yen":lambda v: _opt_int(v),
        "build_year_month":      lambda v: _opt_str(v),
        "age_years":             lambda v: _opt_int(v),
        "structure":             lambda v: _map_structure(v),
        "building_area_sqm":     lambda v: _opt_float(v),
        "land_area_sqm":         lambda v: _opt_float(v),
        "land_rights":           lambda v: _opt_str(v),
        "legal_far_pct":         lambda v: _opt_float(v),
        "bcr_pct":               lambda v: _opt_float(v),
        "num_units":             lambda v: _opt_int(v),
        "nearest_station":       lambda v: _opt_str(v),
        "station_walk_min":      lambda v: _opt_int(v),
        "transaction_type":      lambda v: _opt_str(v),
        "listing_date":          lambda v: _opt_str(v),
        "land_category":         lambda v: _opt_str(v),
        "city_planning_area":    lambda v: _opt_str(v),
    }

    for field in none_fields:
        if field not in raw:
            continue
        conv = conversions.get(field)
        if conv is None:
            continue
        val = conv(raw[field])
        if val is not None:
            d[field] = val
            filled.add(field)  # LLMで補完されたフィールドを記録

    d["raw_extraction"] = raw
    d["llm_filled_fields"] = filled
    return PropertyData(**d)


def _detect_platform(url: str) -> str:
    if "rakumachi.jp" in url:
        return "rakumachi"
    if "kenbiya.com" in url:
        return "kenbiya"
    return "unknown"


def extract_source_property_id(url: str) -> str | None:
    """掲載URLからサイト内の安定した物件IDらしき値を抽出する。"""
    patterns = [
        r"/syuunyuubukken/[^/]+/(\d+)(?:[/?#]|$)",
        r"/detail/[^/]+/(\d+)(?:[/?#]|$)",
        r"[?&](?:property_id|id)=([0-9]+)(?:[&#]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    digit_runs = re.findall(r"(\d{5,})", url)
    if digit_runs:
        return max(digit_runs, key=len)
    return None


def _strip_html_to_text(html: str, max_chars: int = 8000, platform: str = "unknown") -> str:
    """不要タグを除去してテキストを抽出する。<main>/<article>を優先。"""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # メインコンテンツ優先
    main = soup.find("main") or soup.find("article") or soup.find(id="main") or soup.body
    if main is None:
        main = soup

    text = main.get_text(separator="\n")

    # \xa0（ノーブレークスペース）など特殊空白を通常スペースに統一
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    # 行内の余分なスペースを圧縮
    text = "\n".join(line.strip() for line in text.split("\n"))
    # 連続する空行を1行に圧縮
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if platform == "kenbiya":
        text = _preprocess_kenbiya(text)

    return text[:max_chars]


def _preprocess_kenbiya(text: str) -> str:
    """健美家テキストのプラットフォーム固有正規化。"""
    # 価格: 価格\n\n3\n億\n1,800\n万円 → 価格\n3億1800万円
    def _join_price_lines(m: re.Match) -> str:
        body = m.group(1)
        fragments = [l.strip() for l in body.split("\n") if l.strip()]
        return f"価格\n{''.join(fragments).replace(',', '')}\n"

    text = re.sub(
        r"価格[\n]+((?:[\d,]+[\n]+)*(?:億[\n]+)?(?:[\d,]+[\n]+)?万円)[\n]+",
        _join_price_lines,
        text,
    )

    # 満室時利回り: 数値が「6\n.35\n％」に分断される → 「満室時利回り6.35%」に結合
    def _join_yield_lines(m: re.Match) -> str:
        body = m.group(1)
        fragments = [l.strip() for l in body.split("\n") if l.strip()]
        val = "".join(fragments).replace("％", "%")
        return f"満室時利回り\n{val}\n"

    text = re.sub(
        r"満室時利回り[\n]+((?:[\d]+[\n]+)?(?:\.[\d]+[\n]+)?[%％])[\n]*",
        _join_yield_lines,
        text,
    )

    # 建物面積・土地面積ラベル後の余分な空行を除去
    text = re.sub(r"(建物面積|土地面積)\n\n", r"\1\n", text)

    return text


def _call_claude_extraction(text_content: str, platform: str = "unknown") -> dict:
    """Ollama (gemma3:12b) で物件データの JSON 抽出を行う。APIキー不要・完全ローカル。"""
    schema = _load_site_schema(platform)
    schema_section = f"\n\nSITE-SPECIFIC SCHEMA FOR {platform.upper()}:\n{schema}\n" if schema else ""

    prompt = f"{_SYSTEM_PROMPT}{schema_section}\n\n{_USER_PROMPT_TEMPLATE.format(text_content=text_content)}"

    resp = requests.post(
        f"{_OLLAMA_BASE_URL}/api/generate",
        json={
            "model": _OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
        timeout=120,
    )
    resp.raise_for_status()
    raw_text = resp.json().get("response", "{}")

    # コードフェンスがあれば除去
    raw_text = re.sub(r"^```(?:json)?\n?|```$", "", raw_text.strip())

    return json.loads(raw_text)


def _build_property_data(raw: dict, platform: str, source_text: str = "") -> PropertyData:
    """Ollama レスポンス dict を PropertyData に変換する。
    構造化テキストから取れるフィールドはすべてregex優先。LLMは補助。
    """

    def _regex(pattern: str, flags: int = 0) -> Optional[re.Match]:
        return re.search(pattern, source_text, flags) if source_text else None

    def _rx(pattern, group=1, flags=0):
        """マッチした場合にグループ文字列を返す小ヘルパー。"""
        m = _regex(pattern, flags)
        return m.group(group).strip() if m else None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # すべてregex優先。テキストに明示的に存在する値は必ずregexで取る。
    # LLMはregexが取れなかった場合の補助のみ。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── 物件名 ────────────────────────────────────────────────────────
    property_name = _rx(r"物件名\s*\n+\s*([^\n]+)")
    if property_name is None:
        property_name = _opt_str(raw.get("property_name"))

    # ── 住所 ─────────────────────────────────────────────────────────
    address = _rx(r"(?:所在地|住所)\s*\n+\s*([^\n]+地図を見る|[^\n]+[市区町村]\S*)")
    if address is None:
        address = _rx(r"(?:所在地|住所)\s*\n+\s*([^\n]+)")
    # LLM値は幻覚が多いため、テキスト内に実在する場合のみ採用
    if address is None:
        candidate = _opt_str(raw.get("address"))
        if candidate and source_text and candidate[:6] in source_text:
            address = candidate
    # 「地図を見る」などのゴミを除去
    if address:
        address = re.sub(r"\s*地図を見る.*", "", address).strip()

    # ── 最寄駅 + 徒歩分 ──────────────────────────────────────────────
    nearest_station: Optional[str] = None
    station_walk_min: Optional[int] = None
    m = _regex(r"([^\n　]+?(?:駅|停留所|バス停))\s+徒歩(\d+)分")
    if m:
        nearest_station = m.group(1).strip()
        station_walk_min = int(m.group(2))
    if nearest_station is None:
        m = _regex(r"([^\n]+?駅)\s+バス(\d+)分\s+徒歩(\d+)分")
        if m:
            nearest_station = f"{m.group(1).strip()} バス{m.group(2)}分"
            station_walk_min = int(m.group(3))
    if nearest_station is None:
        candidate = _opt_str(raw.get("nearest_station"))
        if candidate and source_text and candidate in source_text:
            nearest_station = candidate
    if station_walk_min is None:
        station_walk_min = _opt_int(raw.get("station_walk_min"))

    # ── 販売価格 ──────────────────────────────────────────────────────
    asking_price_yen = _parse_jp_price(source_text) if source_text else None
    if asking_price_yen is None:
        asking_price_yen = _opt_int(raw.get("asking_price_yen"))

    # ── 表面利回り ────────────────────────────────────────────────────
    gross_yield_pct: Optional[float] = None
    m = _regex(r"(?:表面利回り|満室時利回り)\s*\n+(?:(?:表面利回り|満室時利回り)\s*\n+)?([\d.]+)\s*[%％]")
    if m:
        gross_yield_pct = float(m.group(1))
    if gross_yield_pct is None:
        gross_yield_pct = _opt_float(raw.get("gross_yield_pct"))
    # 賃料と価格が揃っていれば自動計算（ページに表面利回り記載なし対策）
    # ※ この時点では asking_price_yen / gross_rent_annual_yen はまだ未確定なので
    #   _build_property_data の末尾で後計算する（computed フラグはつけない）

    # ── 年間賃料 ──────────────────────────────────────────────────────
    gross_rent_annual_yen: Optional[int] = None
    m = _regex(r"想定年間収入\s*\n+(?:想定年間収入\s*\n+)?([\d,]+)円")
    if m:
        gross_rent_annual_yen = int(m.group(1).replace(",", ""))
    if gross_rent_annual_yen is None:
        m = _regex(r"想定年間収入\s*\n+(?:想定年間収入\s*\n+)?([\d.]+)万円")
        if m:
            gross_rent_annual_yen = int(float(m.group(1)) * 10_000)
    if gross_rent_annual_yen is None:
        # 健美家形式: "満室時年収/月収\n\n1,070.4万円 / 89.2万円"
        m = _regex(r"満室時年収[/／]月収\s*\n+\s*([\d,]+\.?\d*)\s*万円\s*/\s*([\d,]+\.?\d*)\s*万円")
        if m:
            gross_rent_annual_yen = int(float(m.group(1).replace(",", "")) * 10_000)
    if gross_rent_annual_yen is None:
        gross_rent_annual_yen = _opt_int(raw.get("gross_rent_annual_yen"))

    # ── 月額賃料 ──────────────────────────────────────────────────────
    gross_rent_monthly_yen: Optional[int] = None
    m = _regex(r"\(([\d,]+)円/月\)")
    if m:
        gross_rent_monthly_yen = int(m.group(1).replace(",", ""))
    # 健美家形式から月収を直接取得
    if gross_rent_monthly_yen is None:
        m = _regex(r"満室時年収[/／]月収\s*\n+\s*[\d,]+\.?\d*\s*万円\s*/\s*([\d,]+\.?\d*)\s*万円")
        if m:
            gross_rent_monthly_yen = int(float(m.group(1).replace(",", "")) * 10_000)
    if gross_rent_monthly_yen is None and gross_rent_annual_yen:
        gross_rent_monthly_yen = gross_rent_annual_yen // 12
    if gross_rent_monthly_yen is None:
        gross_rent_monthly_yen = _opt_int(raw.get("gross_rent_monthly_yen"))

    # ── 築年月 ────────────────────────────────────────────────────────
    build_year_month: Optional[str] = None
    m = _regex(r"築年月\s*\n+\s*(\d{4})年(\d{1,2})月")
    if m:
        build_year_month = f"{m.group(1)}-{int(m.group(2)):02d}"
    if build_year_month is None:
        build_year_month = _opt_str(raw.get("build_year_month"))

    # ── 築年数 ────────────────────────────────────────────────────────
    age_years: Optional[int] = None
    m = _regex(r"築(\d+)年")
    if m:
        age_years = int(m.group(1))
    if age_years is None:
        age_years = _opt_int(raw.get("age_years"))

    # ── 建物構造 ──────────────────────────────────────────────────────
    structure: Optional[str] = None
    m = _regex(r"建物構造\s*\n+\s*(木造|RC造?|鉄骨造?|SRC造?|軽量鉄骨|鉄筋コンクリート|S造|ALC)[^\n]*")
    if m:
        structure = _map_structure(m.group(1))
    if structure is None:
        structure = _map_structure(raw.get("structure"))

    # ── 建物面積 ──────────────────────────────────────────────────────
    building_area_sqm: Optional[float] = None
    m = _regex(r"建物面積\s*\n+\s*([\d,]+\.?\d*)\s*[m㎡]")
    if m:
        building_area_sqm = float(m.group(1).replace(",", ""))
    if building_area_sqm is None:
        building_area_sqm = _opt_float(raw.get("building_area_sqm"))

    # ── 土地面積 ──────────────────────────────────────────────────────
    land_area_sqm: Optional[float] = None
    m = _regex(r"土地面積\s*\n+\s*([\d,]+\.?\d*)\s*[m㎡]")
    if m:
        land_area_sqm = float(m.group(1).replace(",", ""))
    if land_area_sqm is None:
        land_area_sqm = _opt_float(raw.get("land_area_sqm"))

    # ── 土地権利 ──────────────────────────────────────────────────────
    land_rights: Optional[str] = None
    m = _regex(r"土地権利\s*\n+\s*(\S+)")
    if m:
        land_rights = m.group(1).strip()
    if land_rights is None:
        land_rights = _opt_str(raw.get("land_rights"))

    # ── 法定容積率・建蔽率 ───────────────────────────────────────────
    # 健美家形式: "建ぺい/容積率\n\n60 ％ /\n150 ％"
    legal_far_pct: Optional[float] = None
    bcr_pct: Optional[float] = None
    m = _regex(r"建ぺい[/／]容積率\s*\n+\s*([\d.]+)\s*[％%][^\d\n]*/\s*\n+\s*([\d.]+)\s*[％%]")
    if m:
        bcr_pct = float(m.group(1))
        legal_far_pct = float(m.group(2))
    # 楽待などの独立ラベル形式
    if legal_far_pct is None:
        m = _regex(r"容積率\s*\n+\s*([\d.]+)\s*[％%]")
        if m:
            legal_far_pct = float(m.group(1))
        else:
            # "200/300%" 形式 → 小さい方を採用
            m = _regex(r"容積率\s*\n+\s*([\d.]+)\s*/\s*([\d.]+)\s*[％%]")
            if m:
                legal_far_pct = min(float(m.group(1)), float(m.group(2)))
    # ── 建蔽率（建ぺい率）──────────────────────────────────────────────
    if bcr_pct is None:
        # 楽待: "建ぺい率" (hiragana); 健美家: "建蔽率" (kanji) — 両方対応
        m = _regex(r"建[ぺ蔽]い?率\s*\n+(?:\s*建[ぺ蔽]い?率\s*\n+)?\s*([\d.]+)\s*[%％]")
        if m:
            bcr_pct = float(m.group(1))
    if legal_far_pct is None:
        legal_far_pct = _opt_float(raw.get("legal_far_pct"))
    if bcr_pct is None:
        bcr_pct = _opt_float(raw.get("bcr_pct"))

    # ── 総戸数 ────────────────────────────────────────────────────────
    num_units: Optional[int] = None
    m = _regex(r"総戸数\s*\n+\s*(\d+)戸")
    if m:
        num_units = int(m.group(1))
    if num_units is None:
        # 健美家形式: "木造3階建 総戸数9戸" が1行にまとまっている
        m = _regex(r"総戸数(\d+)戸")
        if m:
            num_units = int(m.group(1))
    if num_units is None:
        num_units = _opt_int(raw.get("num_units"))

    # ── 接道状況 ──────────────────────────────────────────────────────
    road_frontage: Optional[str] = None
    # ラベルが2回出現するパターン（楽待）でも値を正しく捕捉する
    m = _regex(r"接道状況\s*\n+\s*(?!接道状況)(.+)")
    if m:
        v = m.group(1).strip()
        # 健美家: 接道状況が空欄の場合、次のdtラベル（防火法/国土法 等）を誤取得するため除外
        _ROAD_INVALID = {"防火法/国土法", "防火法", "国土法"}
        if v and v not in _ROAD_INVALID and not re.match(r"^-{2,}", v):
            road_frontage = v

    # ── 取引態様 ──────────────────────────────────────────────────────
    transaction_type: Optional[str] = None
    m = _regex(r"取引態様\s*\n+\s*(\S+)")
    if m:
        v = m.group(1).strip()
        if v != "取引態様":
            transaction_type = v
    if transaction_type is None:
        transaction_type = _opt_str(raw.get("transaction_type"))

    # ── 情報登録日 ────────────────────────────────────────────────────
    listing_date: Optional[str] = None
    m = _regex(r"情報登録日\s*\n+\s*(\d{4})/(\d{2})/(\d{2})")
    if m:
        listing_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if listing_date is None:
        m = _regex(r"情報公開日\s*\n+\s*(\d{4})年\s*(\d+)月\s*(\d+)日")
        if m:
            listing_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if listing_date is None:
        listing_date = _opt_str(raw.get("listing_date"))

    # ── 物件種別 ──────────────────────────────────────────────────────
    property_type: Optional[str] = None
    m = _regex(r"物件種別\s*\n+\s*(?!物件種別)([^\n]+)")
    if m:
        v = m.group(1).strip()
        if v:
            property_type = v
    if property_type is None:
        # ページ上部カテゴリから推定（楽待など「物件種別」ラベルなし）
        # 健美家の「一棟マンション/一棟アパート」→「1棟マンション/1棟アパート」に正規化
        _PROP_TYPES = [
            ("1棟マンション", ["一棟マンション", "一棟売りマンション", "1棟マンション"]),
            ("1棟アパート",   ["一棟アパート",   "一棟売りアパート",   "1棟アパート"]),
            ("区分マンション", ["区分マンション"]),
            ("区分アパート",   ["区分アパート"]),
            ("戸建て",        ["戸建て"]),
            ("事務所・店舗",   ["事務所・店舗"]),
            ("その他",        ["その他"]),
        ]
        early = source_text[:3000] if source_text else ""
        for canonical, aliases in _PROP_TYPES:
            if any(alias in early for alias in aliases):
                property_type = canonical
                break
        # フォールバック: "土地" は単体ラベルとしてのみ（"土地権利"等を除外）
        if property_type is None and re.search(r"(?<![^\n])土地(?!権利|面積|の場合)", early):
            property_type = "土地"
    if property_type is None:
        property_type = _opt_str(raw.get("property_type"))

    # ── 間取り ────────────────────────────────────────────────────────
    floor_plan: Optional[str] = None
    m = _regex(r"間取り\s*\n+\s*(.+)")
    if m:
        v = m.group(1).strip()
        if v and v != "間取り":
            floor_plan = v
    if floor_plan is None:
        floor_plan = _opt_str(raw.get("floor_plan"))

    # ── 階数 ──────────────────────────────────────────────────────────
    num_floors: Optional[int] = None
    m = _regex(r"地上(\d+)階")
    if m:
        num_floors = int(m.group(1))
    if num_floors is None:
        # "4階建て" 形式（楽待: "階数\n4階建て"）
        m = _regex(r"階数(?:\s*\n+\s*階数)?\s*\n+\s*(\d+)階建")
        if m:
            num_floors = int(m.group(1))
    if num_floors is None:
        # 健美家: "RC造6階建 総戸数20戸" のように構造行に埋め込まれている
        m = _regex(r"(?:RC造?|鉄骨造?|SRC造?|木造|S造)(\d+)階建")
        if m:
            num_floors = int(m.group(1))
    if num_floors is None:
        # 健美家: "鉄筋コンクリートブロック造4階建" など、構造名が表記揺れする場合
        m = _regex(r"建物構造\s*\n+\s*[^\n]*?(\d+)階建")
        if m:
            num_floors = int(m.group(1))
    if num_floors is None:
        num_floors = _opt_int(raw.get("num_floors"))

    # ── 地目 ──────────────────────────────────────────────────────────
    land_category: Optional[str] = None
    m = _regex(r"地目\s*\n+\s*(?!地目)([^\n]+)")
    if m:
        v = m.group(1).strip()
        if v:
            land_category = v
    if land_category is None:
        land_category = _opt_str(raw.get("land_category"))

    # ── 都市計画区域 ──────────────────────────────────────────────────
    city_planning_area: Optional[str] = None
    m = _regex(r"都市計画区域\s*\n+\s*(?!都市計画|用途地域|国土法)([^\n]+)")
    if m:
        v = m.group(1).strip()
        if v:
            city_planning_area = v
    if city_planning_area is None:
        # 健美家: 「用途地域」ラベルで同等情報を提供
        m = _regex(r"用途地域\s*\n+\s*(?!用途地域|国土法)([^\n]+)")
        if m:
            v = m.group(1).strip()
            if v:
                city_planning_area = v
    if city_planning_area is None:
        city_planning_area = _opt_str(raw.get("city_planning_area"))

    # ── 更新日 ────────────────────────────────────────────────────────
    updated_date: Optional[str] = None
    # 楽待: "次回更新予定日\n更新日\n\n2026/07/21\n\n2026/04/22" → 2番目が更新日
    m = _regex(r"次回更新予定日\s*\n\s*更新日\s*\n+\s*\d{4}/\d{2}/\d{2}\s*\n+\s*(\d{4})/(\d{2})/(\d{2})")
    if m:
        updated_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if updated_date is None:
        m = _regex(r"更新日\s*\n+\s*(\d{4})/(\d{2})/(\d{2})")
        if m:
            updated_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if updated_date is None:
        # 健美家: "更新予定日\n\n2026年 5月 21日"
        m = _regex(r"更新予定日\s*\n+\s*(\d{4})年\s*(\d+)月\s*(\d+)日")
        if m:
            updated_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # ── 表面利回りフォールバック（ページ非掲載時に賃料・価格から算出）────
    if gross_yield_pct is None and asking_price_yen and asking_price_yen > 0:
        annual_for_yield = (
            gross_rent_annual_yen
            or (gross_rent_monthly_yen * 12 if gross_rent_monthly_yen else None)
        )
        if annual_for_yield:
            gross_yield_pct = round(annual_for_yield / asking_price_yen * 100, 2)

    # regex取得数でconfidenceを上書き
    found = sum(v is not None for v in [
        property_name, address, asking_price_yen, gross_yield_pct,
        gross_rent_annual_yen, build_year_month, structure,
        building_area_sqm, land_area_sqm, nearest_station,
    ])
    if found >= 8:
        confidence = "high"
    elif found >= 4:
        confidence = "partial"
    else:
        confidence = raw.get("extraction_confidence", "low")

    return PropertyData(
        property_name=property_name,
        address=address,
        asking_price_yen=asking_price_yen,
        gross_rent_monthly_yen=gross_rent_monthly_yen,
        gross_rent_annual_yen=gross_rent_annual_yen,
        gross_yield_pct=gross_yield_pct,
        build_year_month=build_year_month,
        age_years=age_years,
        structure=structure,
        property_type=property_type,
        building_area_sqm=building_area_sqm,
        land_area_sqm=land_area_sqm,
        land_rights=land_rights,
        legal_far_pct=legal_far_pct,
        bcr_pct=bcr_pct,
        num_units=num_units,
        road_frontage=road_frontage,
        nearest_station=nearest_station,
        station_walk_min=station_walk_min,
        floor_plan=floor_plan,
        num_floors=num_floors,
        land_category=land_category,
        city_planning_area=city_planning_area,
        updated_date=updated_date,
        transaction_type=transaction_type,
        listing_date=listing_date,
        platform=platform,
        extraction_confidence=confidence,
        raw_extraction=raw,
    )


def _parse_jp_price(text: str) -> Optional[int]:
    """楽待・健美家テキストから販売価格を正規表現でパースする。
    対応形式: N万円 / N億円 / N億M万円
    ラベル: 販売価格 / 価格
    """
    m = re.search(r"(?:販売価格|価格)\s*\n+\s*((?:\d+億)?\d[\d,]*万円|\d+億円?)", text)
    if not m:
        return None
    price_str = m.group(1).replace(",", "").replace(" ", "")
    total = 0
    bm = re.search(r"(\d+)億", price_str)
    if bm:
        total += int(bm.group(1)) * 100_000_000
    mm = re.search(r"(\d+)万", price_str)
    if mm:
        total += int(mm.group(1)) * 10_000
    return total if total > 0 else None


def _map_structure(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    for key, val in _STRUCTURE_MAP.items():
        if key in raw:
            return val
    return "rc"  # 不明時は保守的にRC


def _opt_str(v) -> Optional[str]:
    return str(v).strip() if v is not None and str(v).strip() else None


def _opt_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _opt_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
