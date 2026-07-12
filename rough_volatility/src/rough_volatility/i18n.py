"""Structured English/Japanese report localization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LOCALE_DIR = Path(__file__).resolve().parents[2] / "locales"
SUPPORTED_LOCALES = ("en", "ja")

REQUIRED_KEYS = {
    "document_title",
    "brand",
    "report_title",
    "report_subtitle",
    "badge",
    "footer",
}


def load_locale(locale: str) -> dict[str, str]:
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(f"unsupported locale {locale!r}; choose from {SUPPORTED_LOCALES}")
    path = LOCALE_DIR / f"{locale}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in payload.items()
    ):
        raise ValueError(f"locale file must be a flat string mapping: {path}")
    missing = REQUIRED_KEYS - payload.keys()
    if missing:
        raise KeyError(f"locale {locale} is missing keys: {sorted(missing)}")
    return payload


def validate_locales() -> None:
    payloads = {locale: load_locale(locale) for locale in SUPPORTED_LOCALES}
    reference = set(payloads[SUPPORTED_LOCALES[0]])
    for locale, payload in payloads.items():
        keys = set(payload)
        if keys != reference:
            missing = sorted(reference - keys)
            extra = sorted(keys - reference)
            raise ValueError(f"locale key mismatch for {locale}: missing={missing}, extra={extra}")


class Translator:
    def __init__(self, locale: str):
        self.locale = locale
        self.messages = load_locale(locale)

    def __call__(self, key: str, **values: Any) -> str:
        try:
            text = self.messages[key]
        except KeyError as exc:
            raise KeyError(f"missing translation {key!r} for {self.locale}") from exc
        return text.format(**values) if values else text
