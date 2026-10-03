"""Chooser cards consume checked shared figures after compound options."""

from report_builder.figures import figures_for


def test_chooser_cards_follow_compound_and_use_shared_figures():
    specs = figures_for("exotics")
    start = next(i for i, s in enumerate(specs) if s.id == "compound_validation") + 1
    selected = specs[start : start + 4]
    assert [s.id for s in selected] == [
        "chooser_choice",
        "chooser_package",
        "chooser_timing",
        "chooser_validation",
    ]
    for s in selected:
        assert s.title and s.blurb and s.practice
        f = s.build()
        assert f.layout.meta["section"] == "26.8" and f.layout.meta["figure"] == s.id
