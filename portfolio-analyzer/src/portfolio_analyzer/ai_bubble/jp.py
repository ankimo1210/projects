"""The summary page of a Japanese earnings release (決算短信) as point-in-time rows.

The Tokyo Stock Exchange template is stable across years and companies: a
results block (連結経営成績), a financial position block (連結財政状態) and, for
full years and some half years, a cash flow block (連結キャッシュ・フローの状況).
Each row starts with a period label (``2027年3月期第1四半期``, ``21年3月期`` under
Heisei, ``2026年3月期中間期`` for half years from April 2024) and carries the
current period first, then the comparative. Results are
year-to-date cumulative. ``△`` marks a negative number and ``―``/``-`` a blank;
a blank becomes an explained gap, never a zero. Before the 2010 template only
US-GAAP filers printed their basis (so an unmarked release is Japanese GAAP,
flagged ``basis_printed = False``), and per-share values sat in separate yen and
sen columns.

The release time is not on the page, so a row is usable from 00:00 JST on the
weekday after the printed release date (TDnet releases are mostly 15:00 JST).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
_ERA_BASE = {"平成": 1988, "令和": 2018, "昭和": 1925}
_LABEL = re.compile(
    r"^\s*(?P<era>平成|令和)?\s*(?P<year>\d{2,4})\s*年\s*(?P<month>\d{1,2})\s*月\s*期"
    r"(?:\s*第\s*(?P<quarter>\d)\s*四\s*半\s*期|\s*(?P<interim>中\s*間\s*期))?(?!\s*[（(]予想)"
)
_TOKEN = re.compile(r"△\s*[\d,]+(?:\.\d+)?|-?[\d,]+(?:\.\d+)?|[―\-－—]")
_DATE = re.compile(
    r"(?P<era>平成|令和)?\s*(?P<year>\d{2,4})\s*年\s*(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日"
)
_BASIS = tuple(
    (f"{left}{name}{right}", basis)
    for name, basis in (
        ("IFRS", "IFRS"),
        ("米国会計基準", "US-GAAP"),
        ("米国基準", "US-GAAP"),
        ("日本基準", "JP-GAAP"),
    )
    for left, right in (("〔", "〕"), ("(", ")"), ("[", "]"))
)
_SHARES = (
    ("期末発行済株式数", "shares_issued"),
    ("期末自己株式数", "treasury_shares"),
    ("期中平均株式数", "shares_average"),
)
# A share-count row starts with its title (after an optional ①②③, which NFKC
# turns into 1-3), so a footnote that mentions the title is not read as a row.
_SHARE_ROW = re.compile(r"^\s*[1-3]?\s*(期末発行済株式数|期末自己株式数|期中平均株式数)")
_SHARE_PAIR = re.compile(
    r"(?P<era>平成|令和)?\s*(?P<year>\d{2,4})\s*年\s*(?P<month>\d{1,2})\s*月\s*期"
    r"\s*(?:(?P<q>\d)\s*Q|第\s*(?P<q2>\d)\s*四\s*半\s*期|(?P<interim>中\s*間\s*期))?"
    r"\s*(?P<num>[\d,]+)\s*株"
)
_SEN = re.compile(r"\d{2}")
_YEN = re.compile(r"△?\s*[\d,]+")
_PARENT = ("当社株主に帰属", "親会社株主に帰属", "親会社の所有者に帰属")
_BLOCKS = (("pl", "連結経営成績"), ("bs", "連結財政状態"), ("cf", "連結キャッシュ・フロー"))

# Value columns (percent columns dropped) by basis and number of values.
_PL = {
    ("IFRS", 6): (
        "revenue",
        "operating_income",
        "pretax_income",
        "net_income",
        "net_income_parent",
        "comprehensive_income",
    ),
    ("US-GAAP", 4): ("revenue", "operating_income", "pretax_income", "net_income"),
    ("US-GAAP", 5): (
        "revenue",
        "operating_income",
        "pretax_income",
        "net_income",
        "net_income_parent",
    ),
    ("JP-GAAP", 4): ("revenue", "operating_income", "ordinary_income", "net_income"),
}
_WITH_PARENT = ("total_assets", "equity_total", "equity_parent", "equity_ratio_pct", "bps")
_WITHOUT_PARENT = ("total_assets", "equity_total", "equity_ratio_pct", "bps")
_CF = ("operating_cf", "investing_cf", "financing_cf", "cash_end")
_PER_SHARE = {"eps_basic", "eps_diluted", "bps"}
_RATIOS = {"equity_ratio_pct"}


def _year(era: str | None, digits: str, document_era: str | None) -> int:
    year = int(digits)
    if len(digits) == 4:
        return year
    era = era or document_era
    if era is None:
        return 2000 + year
    return _ERA_BASE[era] + year


def _number(token: str) -> float | None:
    token = token.strip()
    if token in {"―", "-", "－", "—"}:
        return None
    negative = token.startswith("△")
    value = float(token.lstrip("△").strip().replace(",", ""))
    return -value if negative else value


def _merge_sen(tokens: list[str]) -> list[str]:
    """Join a yen column and the two-digit sen column after it (``594 01`` -> ``594.01``)."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if _YEN.fullmatch(tokens[i]) and _SEN.fullmatch(nxt):
            out.append(f"{tokens[i]}.{nxt}")
            i += 2
        else:
            out.append(tokens[i])
            i += 1
    return out


def _month_end(year: int, month: int) -> date:
    first_next = date(year + (month == 12), month % 12 + 1, 1)
    return first_next - timedelta(days=1)


def _span(fy_end_year: int, fy_end_month: int, quarter: int | None) -> tuple[date, date]:
    end = _month_end(fy_end_year, fy_end_month)
    start = date(fy_end_year - 1 + (fy_end_month == 12), fy_end_month % 12 + 1, 1)
    if quarter:
        months = start.month - 1 + 3 * quarter
        end = _month_end(start.year + (months - 1) // 12, (months - 1) % 12 + 1)
    return start, end


def _next_weekday(day: date) -> date:
    nxt = day + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def _jst_midnight_utc(day: date) -> str:
    return datetime.combine(day, time(0), JST).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _blocks(lines: list[str]) -> dict[str, list[str]]:
    starts = []
    for index, line in enumerate(lines):
        for name, marker in _BLOCKS:
            if marker in line and not any(name == s[1] for s in starts):
                starts.append((index, name))
    stops = [i for i, line in enumerate(lines) if "配当の状況" in line]
    out = {}
    for pos, (index, name) in enumerate(starts):
        nxt = [i for i, _ in starts[pos + 1 :]] + [i for i in stops if i > index] + [len(lines)]
        out[name] = lines[index + 1 : min(nxt)]
    return out


def _header(body: list[str]) -> str:
    """The column titles of a block: its lines before the first period row, unspaced."""
    stop = next((i for i, line in enumerate(body) if _LABEL.match(line)), len(body))
    return "".join(body[:stop]).replace(" ", "")


def parse_summary(
    text: str, *, issuer_id: str, source_url: str, retrieved_at: str, notes: str = ""
) -> list[dict[str, Any]]:
    """Rows from the summary page; ``notes`` is the text of the pages after it,
    read only for the share counts (発行済株式数), which may sit there."""
    text = unicodedata.normalize("NFKC", text)
    notes = unicodedata.normalize("NFKC", notes)
    lines = text.splitlines()
    blocks = _blocks(lines)
    first_block = next(
        (i for i, line in enumerate(lines) if any(m in line for _, m in _BLOCKS)), len(lines)
    )
    head = "\n".join(lines[:first_block])
    if "決算短信" not in text and not re.search(r"財務\s*・\s*業績の概況", text):
        raise ValueError(
            "no 決算短信 title on the page (image only, or a font without a text mapping)"
        )
    if "pl" not in blocks:
        raise ValueError("連結経営成績 block not found")
    basis = next((b for marker, b in _BASIS if marker in head), None)
    basis_printed = basis is not None
    if basis is None:
        if "米国" in head or "IFRS" in head or "国際会計基準" in head:
            raise ValueError("accounting basis named in the header but not in a known marker")
        basis = "JP-GAAP"
    document_era = "平成" if "平成" in head else "令和" if "令和" in head else None
    printed = _DATE.search(head)
    if printed is None:
        raise ValueError("release date not found in the page header")
    released = date(
        _year(printed["era"], printed["year"], document_era),
        int(printed["month"]),
        int(printed["day"]),
    )
    pl_header = _header(blocks["pl"])
    parent_column = any(marker in pl_header for marker in _PARENT)
    # A parent-equity column (株主資本 / 親会社の所有者に帰属する持分) shifts the ratio
    # and per-share columns right; the column count alone cannot tell (a quarter
    # has no per-share column, a pre-2010 year has no parent column).
    bs_header = _header(blocks.get("bs", [])).replace("株主資本比率", "")
    bs_parent = basis == "IFRS" or "株主資本" in bs_header or "親会社" in bs_header
    common = {
        "issuer_id": issuer_id,
        "unit": "JPY",
        "published_at": _jst_midnight_utc(released),
        "available_at": _jst_midnight_utc(_next_weekday(released)),
        "retrieved_at": retrieved_at,
        "source_url": source_url,
        "document_id": source_url.rsplit("/", 1)[-1],
        "accounting_basis": basis,
        "basis_printed": basis_printed,
    }
    rows: list[dict[str, Any]] = []

    def emit(metric: str, raw: float | None, start: date, end: date) -> None:
        if metric in _PER_SHARE:
            unit, scale = "JPY/shares", 1.0
        elif metric.startswith("shares") or metric == "treasury_shares":
            unit, scale = "shares", 1.0
        elif metric in _RATIOS:
            unit, scale = "percent", 1.0
        else:
            unit, scale = "JPY", 1e6
        rows.append(
            {
                **common,
                "metric": metric,
                "unit": unit,
                "value": None if raw is None else raw * scale,
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "quality": "ok" if raw is not None else "missing:blank_in_release",
            }
        )

    for name, body in blocks.items():
        seen: dict[tuple[date, date], int] = {}
        sen_columns = "銭" in "".join(body)
        for line in body:
            label = _LABEL.match(line)
            if not label:
                continue
            fy_year = _year(label["era"], label["year"], document_era)
            quarter = int(label["quarter"]) if label["quarter"] else 2 if label["interim"] else None
            start, end = _span(fy_year, int(label["month"]), quarter)
            tokens = _TOKEN.findall(line[label.end() :])
            if not tokens:
                continue
            occurrence = seen.get((start, end), 0)
            seen[(start, end)] = occurrence + 1
            per_share_row = name == "bs" or (name == "pl" and occurrence > 0)
            if per_share_row and sen_columns:
                tokens = _merge_sen(tokens)
            values = [_number(t) for t in tokens]
            if name == "pl" and occurrence == 0:
                kept = values[0::2]
                columns = _PL.get((basis, len(kept)))
                if columns is None:
                    raise ValueError(
                        f"unexpected results row ({basis}, {len(kept)} values): {line.strip()}"
                    )
                if parent_column and basis != "IFRS" and len(kept) == 4:
                    columns = (*columns[:3], "net_income_parent")
                for metric, raw in zip(columns, kept, strict=True):
                    emit(metric, raw, start, end)
            elif name == "pl":
                for metric, raw in zip(("eps_basic", "eps_diluted"), values[:2], strict=False):
                    emit(metric, raw, start, end)
            elif name == "bs":
                columns = _WITH_PARENT if bs_parent else _WITHOUT_PARENT
                for metric, raw in zip(columns, values, strict=False):
                    emit(metric, raw, end, end)
            elif name == "cf":
                for metric, raw in zip(_CF, values, strict=False):
                    if metric == "cash_end":
                        emit(metric, raw, end, end)
                    else:
                        emit(metric, raw, start, end)
    seen_shares: set[tuple[str, date, date]] = set()
    for line in (text + "\n" + notes).splitlines():
        row = _SHARE_ROW.match(line)
        if not row:
            continue
        metric = dict(_SHARES)[row[1]]
        for pair in _SHARE_PAIR.finditer(line, row.end()):
            quarter = pair["q"] or pair["q2"] or ("2" if pair["interim"] else None)
            fy_year = _year(pair["era"], pair["year"], document_era)
            start, end = _span(fy_year, int(pair["month"]), int(quarter) if quarter else None)
            if metric != "shares_average":
                start = end
            if (metric, start, end) in seen_shares:
                continue
            seen_shares.add((metric, start, end))
            emit(metric, float(pair["num"].replace(",", "")), start, end)
    return rows


# The TDnet summary as inline XBRL (TSE taxonomy tse-ed-t). Tags name their
# basis (``SalesIFRS``) and contexts carry their own dates, so a company's own
# columns (Kioxia's Non-GAAP profit columns) cannot shift a value.
_IX = "{http://www.xbrl.org/2008/inlineXBRL}"
_XBRLI = "{http://www.xbrl.org/2003/instance}"
_XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
_IXBRL_CONSOLIDATED = {
    "SalesIFRS": "revenue",
    "OperatingIncomeIFRS": "operating_income",
    "ProfitBeforeTaxIFRS": "pretax_income",
    "ProfitIFRS": "net_income",
    "ProfitAttributableToOwnersOfParentIFRS": "net_income_parent",
    "TotalComprehensiveIncomeIFRS": "comprehensive_income",
    "BasicEarningsPerShareIFRS": "eps_basic",
    "DilutedEarningsPerShareIFRS": "eps_diluted",
    "TotalAssetsIFRS": "total_assets",
    "TotalEquityIFRS": "equity_total",
    "EquityAttributableToOwnersOfParentIFRS": "equity_parent",
    "CashFlowsFromOperatingActivitiesIFRS": "operating_cf",
    "CashFlowsFromInvestingActivitiesIFRS": "investing_cf",
    "CashFlowsFromFinancingActivitiesIFRS": "financing_cf",
    "CashAndCashEquivalentsAtEndOfPeriodIFRS": "cash_end",
}
_IXBRL_COMPANY = {
    "NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock": "shares_issued",
    "NumberOfTreasuryStockAtTheEndOfFiscalYear": "treasury_shares",
    "AverageNumberOfShares": "shares_average",
}


def _ixbrl_periods(root: ElementTree.Element) -> dict[str, tuple[str, str]]:
    periods = {}
    for context in root.iter(f"{_XBRLI}context"):
        period = context.find(f"{_XBRLI}period")
        instant = period.find(f"{_XBRLI}instant")
        if instant is not None:
            periods[context.get("id")] = (instant.text, instant.text)
        else:
            periods[context.get("id")] = (
                period.find(f"{_XBRLI}startDate").text,
                period.find(f"{_XBRLI}endDate").text,
            )
    return periods


def parse_summary_ixbrl(
    data: bytes, *, issuer_id: str, source_url: str, retrieved_at: str
) -> list[dict[str, Any]]:
    """Rows from a TDnet summary in inline XBRL: consolidated actuals (IFRS tags) and the
    company's share counts. Forecasts, parent-only figures and change rates are skipped."""
    root = ElementTree.fromstring(data)
    periods = _ixbrl_periods(root)
    filed = next(
        (
            "".join(e.itertext())
            for e in root.iter(f"{_IX}nonNumeric")
            if e.get("name", "").endswith(":FilingDate")
        ),
        None,
    )
    stamp = _DATE.search(unicodedata.normalize("NFKC", filed or ""))
    if stamp is None:
        raise ValueError("FilingDate not found in the inline XBRL")
    released = date(int(stamp["year"]), int(stamp["month"]), int(stamp["day"]))
    common = {
        "issuer_id": issuer_id,
        "published_at": _jst_midnight_utc(released),
        "available_at": _jst_midnight_utc(_next_weekday(released)),
        "retrieved_at": retrieved_at,
        "source_url": source_url,
        "document_id": source_url.rsplit("/", 1)[-1],
        "accounting_basis": "IFRS",
        "basis_printed": True,
    }
    rows = []
    for fact in root.iter(f"{_IX}nonFraction"):
        name = fact.get("name", "").split(":", 1)[-1]
        parts = fact.get("contextRef", "").split("_")
        if parts[-1] != "ResultMember":
            continue
        if "ConsolidatedMember" in parts and name in _IXBRL_CONSOLIDATED:
            metric = _IXBRL_CONSOLIDATED[name]
        elif "NonConsolidatedMember" in parts and name in _IXBRL_COMPANY:
            metric = _IXBRL_COMPANY[name]
        else:
            continue
        start, end = periods[fact.get("contextRef")]
        if metric.startswith("shares") or metric == "treasury_shares":
            unit = "shares"
        elif metric in _PER_SHARE:
            unit = "JPY/shares"
        else:
            unit = "JPY"
        if fact.get(_XSI_NIL) == "true":
            value, quality = None, "missing:nil_in_release"
        else:
            value = float("".join(fact.itertext()).replace(",", "")) * 10 ** int(
                fact.get("scale", "0")
            )
            value = -value if fact.get("sign") == "-" else value
            quality = "ok"
        rows.append(
            {
                **common,
                "metric": metric,
                "unit": unit,
                "value": value,
                "period_start": start,
                "period_end": end,
                "quality": quality,
                "concept": f"tse-ed-t:{name}",
            }
        )
    return rows
