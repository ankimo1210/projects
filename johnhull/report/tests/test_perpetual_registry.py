"""The §26.2 portal cards use the same figures as the Book lesson."""

from report_builder.figures import figures_for


def test_perpetual_cards_follow_packages_and_keep_shared_figure_identity():
    expected = [
        "perpetual_value",
        "perpetual_boundaries",
        "perpetual_zero_dividend",
        "perpetual_convergence",
    ]
    figures = figures_for("exotics")
    ids = [spec.id for spec in figures]
    start = ids.index("packages_risk") + 1
    assert ids[start : start + 4] == expected
    for spec in figures[start : start + 4]:
        assert spec.title and spec.blurb and spec.practice
        figure = spec.build()
        assert figure.layout.meta["section"] == "26.2"
        assert figure.layout.meta["figure"] == spec.id
