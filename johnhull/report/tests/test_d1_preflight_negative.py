"""Mutation helpers used by the D1-preflight negative controls."""

from __future__ import annotations

import pytest

from johnhull.scripts.d1_preflight_negative import (
    bump_first_y,
    insert_unrelated_notebook_section,
    renumber_auto_ids,
    replace_once,
)
from johnhull.scripts.evidence_fingerprint import notebook_slice

UUID = "d94c3fe7-836c-4d93-85b7-ec59c746b1fc"


def test_replace_once_requires_exactly_one_match():
    assert replace_once("a b a", "b", "c") == "a c a"
    with pytest.raises(ValueError, match="exactly one"):
        replace_once("a b a", "a", "c")


def test_renumber_auto_ids_shifts_ids_and_links_only():
    html = '<section id="id3"><a href="#id3">x</a><div id="ivf-27-3"></div></section>'
    assert renumber_auto_ids(html, 1) == (
        '<section id="id4"><a href="#id4">x</a><div id="ivf-27-3"></div></section>'
    )


def test_bump_first_y_changes_only_the_named_figure():
    html = (
        'Plotly.newPlot(                        "fig-a", [{"y":[1.0, 2.0]}]);'
        'Plotly.newPlot(                        "fig-b", [{"y":[5.0]}]);'
    )
    bumped = bump_first_y(html, "b", 0.5)
    assert '"fig-a", [{"y":[1.0, 2.0]}]' in bumped
    assert '"fig-b", [{"y":[5.5]}]' in bumped


def _notebook():
    return {
        "cells": [
            {"cell_type": "markdown", "id": "cell-000", "metadata": {}, "source": ["# T"]},
            {
                "cell_type": "code",
                "id": "cell-001",
                "execution_count": 1,
                "metadata": {},
                "source": ["a()"],
                "outputs": [],
            },
            {"cell_type": "markdown", "id": "cell-002", "metadata": {}, "source": ["## 9. IVF"]},
            {
                "cell_type": "code",
                "id": "cell-003",
                "execution_count": 2,
                "metadata": {},
                "source": ["plot()"],
                "outputs": [
                    {
                        "output_type": "display_data",
                        "data": {"text/html": [f'<div id="{UUID}"></div>']},
                        "metadata": {},
                    }
                ],
            },
        ],
        "metadata": {},
    }


def test_inserted_section_renumbers_ids_counts_and_plot_ids():
    notebook = insert_unrelated_notebook_section(_notebook(), "## 9. IVF")
    ids = [cell["id"] for cell in notebook["cells"]]
    assert ids == [f"cell-{i:03d}" for i in range(6)]
    target = notebook["cells"][5]
    assert target["execution_count"] == 3
    assert UUID not in target["outputs"][0]["data"]["text/html"][0]


def test_inserted_section_keeps_the_target_slice_fingerprint():
    before, _ = notebook_slice(_notebook(), "9. IVF")
    after, _ = notebook_slice(insert_unrelated_notebook_section(_notebook(), "## 9. IVF"), "9. IVF")
    assert before == after
