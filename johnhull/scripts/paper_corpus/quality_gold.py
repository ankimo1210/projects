"""Reviewed page-level exceptions for corpus-v2 quality gates.

These entries are not synthetic transcriptions.  They record pages whose low
text ratio is explained by source-page layout (figures, tables, or vertical
Japanese) and whose source image was visually reviewed.  The converter still
retains record-level ``auto``/``unverified`` status for extracted content.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

REVIEWER: Final = "codex-source-page-visual-audit-2026-07-23"


@dataclass(frozen=True)
class ReviewedPageException:
    """Immutable evidence for one resolved page-level quality exception."""

    reason: str
    coverage_scope: str
    reviewer: str = REVIEWER
    reviewed_excerpt: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Return a deterministic JSON-ready representation."""

        return asdict(self)


def _asset_dominant(*pages: int) -> dict[int, ReviewedPageException]:
    return {
        page: ReviewedPageException(
            reason="asset_dominant_source_page",
            coverage_scope="full source page plus retained table/figure assets",
        )
        for page in pages
    }


REVIEWED_LOW_TEXT_PAGES: Final[dict[str, dict[int, ReviewedPageException]]] = {
    "1973-merton-corporate-debt-working-paper": _asset_dominant(21),
    "1979-cox-ross-rubinstein-option-pricing": _asset_dominant(30),
    "1995-kupiec-var-model-verification": _asset_dominant(33, 34, 35, 36),
    "1996-broadie-glasserman-security-price-derivatives": _asset_dominant(13, 15, 16),
    "2000-mcneil-frey-tail-risk-evt": _asset_dominant(23),
    "2008-tasche-capital-allocation-kernel-estimators": _asset_dominant(17, 19, 21),
    "2010-lord-koekkoek-van-dijk-heston-simulation": _asset_dominant(19),
    "2013-wu-inflation-rate-derivatives": _asset_dominant(26, 29),
    "2018-gatheral-jaisson-rosenbaum-volatility-is-rough": _asset_dominant(34),
    "2019-buehler-et-al-deep-hedging": _asset_dominant(29),
    "2020-huge-savine-differential-machine-learning": _asset_dominant(7),
    "2021-mof-jgbi-indexation-notice": {
        2: ReviewedPageException(
            reason="vertical_japanese_source_page",
            coverage_scope="source-page visual review; excerpt is not a full transcription",
            reviewed_excerpt=(
                "令和3年9月11日以降に発行された物価連動国債であって、令和3年9月10日以前に"
                "発行されている物価連動国債と同一の記号として発行されたものの場合及び"
                "平成28年9月11日以降令和3年9月10日以前に発行された物価連動国債の場合"
            ),
        ),
        6: ReviewedPageException(
            reason="vertical_japanese_formula_page",
            coverage_scope="source-page visual review; excerpt is not a full transcription",
            reviewed_excerpt=(
                "n<10の場合、(m-1)月10日に適用される消費者物価指数＋［m月10日に適用される"
                "消費者物価指数－(m-1)月10日に適用される消費者物価指数］×"
                "［(m-1)月11日からm月n日までの日数／(m-1)月11日からm月10日までの日数］"
            ),
        ),
    },
    "2025-francois-et-al-deep-hedging-iv-surface": _asset_dominant(32, 52),
    "2025-serafini-bormetti-carbon-options": _asset_dominant(11, 18, 32),
    "2026-brini-volatility-foundation-models": _asset_dominant(19, 25, 27, 38),
}


def _layout_pages(reason: str, *pages: int) -> dict[int, ReviewedPageException]:
    return {
        page: ReviewedPageException(
            reason=reason,
            coverage_scope="full source-page visual reading-order review",
        )
        for page in pages
    }


REVIEWED_LAYOUT_PAGES: Final[dict[str, dict[int, ReviewedPageException]]] = {
    "2021-mof-jgbi-indexation-notice": _layout_pages(
        "vertical_japanese_reading_order_reviewed", *range(1, 7)
    ),
    "2024-mof-jgbi-bei-guide": _layout_pages(
        "japanese_two_column_reading_order_reviewed", *range(1, 11)
    ),
}
