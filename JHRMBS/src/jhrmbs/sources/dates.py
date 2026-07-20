from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta

import pandas as pd

ERA_BASE_YEAR = {"M": 1867, "T": 1911, "S": 1925, "H": 1988, "R": 2018}


def normalize_japanese_date_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).split())


def parse_japanese_date(value: object) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return value.normalize()
    if isinstance(value, datetime):
        return pd.Timestamp(value.date())
    if isinstance(value, date):
        return pd.Timestamp(value)
    if isinstance(value, int | float) and not isinstance(value, bool):
        if 1.0 <= float(value) <= 100_000.0:
            return pd.Timestamp(date(1899, 12, 30) + timedelta(days=int(float(value))))
    text = normalize_japanese_date_text(value)
    western = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?", text)
    if western:
        year, month, day = western.groups()
        return pd.Timestamp(int(year), int(month), int(day or 1))
    era = re.search(
        r"([MTSHR])\s*(\d{1,2}|元)\s*(?:年|\.)?\s*(\d{1,2})\s*(?:月|\.)?\s*(\d{1,2})?",
        text,
        flags=re.IGNORECASE,
    )
    if era:
        era_name, era_year_text, month, day = era.groups()
        era_year = 1 if era_year_text == "元" else int(era_year_text)
        year = ERA_BASE_YEAR[era_name.upper()] + era_year
        return pd.Timestamp(year, int(month), int(day or 1))
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"unsupported Japanese date: {value!r}")
    return pd.Timestamp(parsed).normalize()


def parse_japanese_month(value: object) -> pd.Timestamp:
    return parse_japanese_date(value).to_period("M").to_timestamp()
