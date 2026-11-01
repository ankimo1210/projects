"""Conservative extraction: amounts are never annualized or silently labelled hourly."""

import re
from html.parser import HTMLParser


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "br", "div", "li"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        if tag in ("p", "div", "li"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def text_from_html(value: str) -> str:
    parser = _Text()
    parser.feed(value or "")
    return " ".join(" ".join(parser.parts).split())


NUMBER = r"\d+(?:,\d+)*(?:\.\d+)?[Kk]?"
RANGE = re.compile(
    r"\$?\s*(" + NUMBER + r")\s*(?:-|–|—|to|and)\s*(?:per\s*)?\$?\s*(" + NUMBER + r")", re.I
)
AMOUNT = re.compile(r"(?<![\d.])\$?\s*(" + NUMBER + r")")
DOLLAR_AMOUNT = re.compile(r"\$\s*(" + NUMBER + r")")
CUE = re.compile(r"base\s+(?:pay|salary|compensation)|salary\s+range", re.I)
# BofA states each range after the pay-transparency locations it applies to.
BOFA_PAY = re.compile(
    r"Pay Transparency details\s+(?P<region>.+?)\s+Pay and benefits information\s+(?P<clause>Pay range\s.{0,200})",
    re.I,
)


def _period(text):
    for value, pattern in (
        ("hour", r"\b(?:per\s+hour|hourly|an?\s+hour|/\s*hr)\b"),
        ("year", r"\b(?:per\s+year|per\s+annum|annually|annual(?:ized)?|a\s+year|/\s*yr)\b"),
        ("month", r"\b(?:per\s+month|monthly)\b"),
        ("week", r"\b(?:per\s+week|weekly)\b"),
    ):
        if re.search(pattern, text, re.I):
            return value
    return "unspecified"


def _row(match, evidence, region, context):
    amounts = [
        float(v.rstrip("Kk").replace(",", "")) * (1000 if v.lower().endswith("k") else 1)
        for v in match.groups()
    ]
    low, high = amounts[0], amounts[-1]
    grouped_correctly = all(
        "," not in v or re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?[Kk]?", v)
        for v in match.groups()
    )
    return {
        "minimum": low,
        "maximum": high,
        "currency": "USD",
        "period": _period(context),
        "region": region.strip(),
        "pay_type": "base",
        "evidence": evidence.strip(),
        "parse_status": "parsed"
        if 0 < low <= high
        and grouped_correctly
        and not re.search(r"per\s*\$", match.group(0), re.I)
        else "review",
    }


def extract_salary(company: str, description: str, fields: list[dict]) -> list[dict]:
    """Return separately evidenced base pay ranges; missing period remains unspecified."""
    rows = []
    if company == "GS":
        limits = {}
        labels = {}
        for field in fields or []:
            if not isinstance(field, dict):
                continue
            prompt, value = field.get("Prompt") or "", field.get("Value")
            for side in ("lower", "upper"):
                if re.search(r"salary.*" + side + r"\s+limit", prompt, re.I) and value is not None:
                    limits[side], labels[side] = str(value).strip(), prompt.strip()
        if set(limits) == {"lower", "upper"} and all(
            re.fullmatch(NUMBER, v) for v in limits.values()
        ):
            match = RANGE.fullmatch(limits["lower"] + "-" + limits["upper"])
            evidence = "; ".join(labels[s] + ": " + limits[s] for s in ("lower", "upper"))
            row = _row(match, evidence, "", "")
            row["pay_type"] = "salary_unspecified"
            rows.append(row)
    values = [
        f.get("Value") or ""
        for f in (fields or [])
        if isinstance(f, dict) and re.search(r"base\s*pay|salary", f.get("Prompt") or "", re.I)
    ]
    for value in values:
        if not isinstance(value, str):
            continue
        for part in value.split(";"):
            cursor = 0
            while first := DOLLAR_AMOUNT.search(part, cursor):
                region = part[cursor : first.start()].strip(" ,\t\r\n")
                if re.search(r"\b(?:bonus|assets|commission)\b", region, re.I):
                    break
                match = RANGE.match(part, first.start()) or first
                tail = part[match.end() :]
                unit = re.match(
                    r"\s*(?:(?:per|an?)\s+(?:year|hour|month|week)|annually|hourly)\b", tail, re.I
                )
                end = match.end() + (unit.end() if unit else 0)
                evidence = part[cursor:end].strip()
                rows.append(_row(match, evidence, region, evidence))
                cursor = end
    text = " ".join((description or "").split())
    if company == "BOFA":
        for block in BOFA_PAY.finditer(text):
            clause = block.group("clause")
            match = RANGE.search(clause)
            if not match:
                continue
            unit = re.match(r"\s*(?:annualized salary|hourly pay)", clause[match.end() :], re.I)
            evidence = clause[: match.end() + (unit.end() if unit else 0)]
            rows.append(_row(match, evidence, block.group("region"), evidence))
    if rows:
        return rows

    cues = list(CUE.finditer(text))
    for index, cue in enumerate(cues):
        end = cues[index + 1].start() if index + 1 < len(cues) else len(text)
        clause = text[cue.start() : min(end, cue.end() + 500)]
        first = AMOUNT.search(clause)
        if not first:
            continue
        prefix = clause[: first.start()]
        if "$" not in first.group(0) and not re.search(
            r"(?:is|are|be|between|from|of)\s*$|salary\s+range\s*[:\-]?\s*$", prefix, re.I
        ):
            continue
        if re.search(
            r"\.(?:\s|$)|\b(?:bonus|assets|revenue|AUM|managing|commission)\b", prefix, re.I
        ):
            continue
        match = RANGE.match(clause, first.start()) or first
        # Only the amount directly associated with this base-pay cue is eligible.
        after = clause[match.end() : match.end() + 180]
        after = re.split(
            r"\.(?:\s|$)|[,;]|\b(?:and|with|plus|including|excluding|in addition|for advisers|for advisors|managing|employees|eligible|but|however)\b",
            after,
            maxsplit=1,
            flags=re.I,
        )[0]
        annual_prefix = text[max(0, cue.start() - 15) : cue.start()]
        evidence = prefix + match.group(0) + after
        context = (
            "annual " if re.search(r"annual(?:ized)?\s*$", annual_prefix, re.I) else ""
        ) + evidence
        location = re.search(
            r"(?:for this|for the)\s+(.+?)(?:-based| based)\s+position", prefix, re.I
        )
        region = location.group(1) if location else ""
        # Citi gives one range, for the posting's primary location only.
        primary = re.search(r"Primary Location:\s*(.+?)\s*-{3,}", text)
        if (
            company == "CITI"
            and primary
            and re.search(r"Primary Location\s+(?:Full|Part) Time\s*$", text[: cue.start()], re.I)
        ):
            region = primary.group(1)
        rows.append(_row(match, evidence, region, context))
        # Explicit fixed amounts for different grades in the same base-pay statement.
        for extra in AMOUNT.finditer(clause, match.end()):
            middle = clause[match.end() : extra.start()]
            tail = clause[extra.end() : extra.end() + 140]
            if not re.search(r"\band\s*$", middle, re.I) or re.search(
                r"\b(?:bonus|assets|commission)\b", middle, re.I
            ):
                continue
            if not re.match(
                r"\s*per\s+(?:year|hour)\s+for\s+(?:Vice President|Executive Director|Managing Director|Director|Analyst|Associate)\b",
                tail,
                re.I,
            ):
                continue
            tail = re.split(r"[,;]|\.(?:\s|$)", tail, maxsplit=1)[0]
            extra_evidence = extra.group(0) + tail
            rows.append(_row(extra, extra_evidence, region, extra_evidence))
    unique = {}
    for row in rows:
        key = tuple(
            row[k] for k in ("minimum", "maximum", "currency", "period", "region", "evidence")
        )
        unique[key] = row
    return list(unique.values())
