"""Private tooling for the JohnHull paper corpus.

The package is intentionally separate from :mod:`hullkit`: document-model and OCR
dependencies must never enter the pricing library's runtime dependency graph.
"""

from .schema import CORPUS_SCHEMA_VERSION, P0_PAPER_IDS, REQUIRED_SEMANTIC_SOURCES

__all__ = ["CORPUS_SCHEMA_VERSION", "P0_PAPER_IDS", "REQUIRED_SEMANTIC_SOURCES"]
