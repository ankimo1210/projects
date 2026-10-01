"""Four compound cards reuse the checked figures immediately after cliquets."""

from report_builder.figures import figures_for


def test_compound_cards_follow_cliquet_and_use_shared_figures():
    specs = figures_for("exotics")
    start = next(i for i, spec in enumerate(specs) if spec.id == "cliquet_limits") + 1
    selected = specs[start : start + 4]
    assert [spec.id for spec in selected] == [
        "compound_threshold",
        "compound_strikes",
        "compound_timing",
        "compound_validation",
    ]
    for spec in selected:
        assert spec.title and spec.blurb and spec.practice
        figure = spec.build()
        assert figure.layout.meta["section"] == "26.7"
        assert figure.layout.meta["figure"] == spec.id
