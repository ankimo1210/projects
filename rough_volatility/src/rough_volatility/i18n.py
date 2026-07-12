"""Structured English/Japanese report localization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LOCALE_DIR = Path(__file__).resolve().parents[2] / "locales"
SUPPORTED_LOCALES = ("en", "ja")

# Literal copy of the 26 `Section.anchor` values from `rough_volatility.notebook.SECTIONS`.
# Kept as a literal tuple (not imported) so i18n.py stays free of imports from
# report.py/notebook.py.
_SECTION_ANCHORS = (
    "executive-summary",
    "conceptual-map",
    "mathematical-definitions",
    "configuration",
    "fbm-path-comparison",
    "local-zoom",
    "fgn-increments",
    "increment-acf",
    "structure-functions",
    "hurst-recovery",
    "estimator-bias",
    "ou-versus-fou",
    "rough-bergomi-paths",
    "heston-comparison",
    "terminal-distributions",
    "iv-smiles",
    "iv-surface",
    "atm-skew-term",
    "skew-scaling",
    "hawkes-events",
    "order-flow-price",
    "volatility-proxy",
    "noise-bias",
    "establishes",
    "does-not-establish",
    "limitations-next-steps",
)

REQUIRED_KEYS = {
    "document_title",
    "brand",
    "report_title",
    "report_subtitle",
    "badge",
    "footer",
    *(f"section.{anchor}" for anchor in _SECTION_ANCHORS),
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
