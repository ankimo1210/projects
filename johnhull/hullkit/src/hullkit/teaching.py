"""hullkit.teaching — markdown scaffolds for the johnhull notebooks.

Build-time helpers (they return Markdown *source* strings) that give every
volume one consistent pedagogical frame, answering three questions for each
concept:

- **核心 (core)**     — the one-sentence idea, stripped of notation.
- **直感 (intuition)** — *why* it is true, in plain words.
- **実務 (practice)**  — who uses it, on which desk, for which decision, and
  what breaks if you get it wrong.

The returned strings are fed straight into the ``md()`` cell helper that each
``build_*_notebook.py`` defines, so the frame renders identically in the live
notebook and in the static Jupyter Book. Only plain Markdown is used
(blockquote + ``<br>``) — no MyST-only directives — so nothing depends on the
rendering engine.
"""

from __future__ import annotations


def scaffold(core: str, intuition: str, practice: str) -> str:
    """Three-line 核心 / 直感 / 実務 frame for the top of a section.

    Renders as a single blockquote with three labelled lines.
    """
    return f"> **核心** — {core}<br>\n> **直感** — {intuition}<br>\n> **実務** — {practice}"


def practice_box(title: str, body: str) -> str:
    """A deeper "where this shows up in the real world" callout.

    Use for the one or two flagship ideas of a volume — connect the concept to
    a concrete desk, decision, or market event (market making, risk limits,
    regulatory capital, 2008 CDOs, LTCM, ...).
    """
    return f"> **実務での出番 — {title}**\n>\n> {body}"


def caption(text: str) -> str:
    """A one-line "how to read this chart" caption to place after a figure."""
    return f"*図の読み方 — {text}*"
