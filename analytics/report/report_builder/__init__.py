"""report_builder — generate the offline, interactive analytics portal.

This package imports the three textbook packages (``la_book``, ``nn_textbook``,
``bayes_textbook``) and calls their ``plotly_*`` figure builders to assemble a
self-contained static site. The figure logic lives in the books, so the portal
always stays in sync with the textbooks (single source of truth).
"""

__version__ = "0.1.0"
