"""The §26.3 portal cards follow §26.2 and reuse the Book figures."""

from report_builder.figures import figures_for


def test_nonstandard_cards_follow_perpetual_and_share_figure_identity():
    ids = [spec.id for spec in figures_for("exotics")]
    start = ids.index("perpetual_convergence") + 1
    expected = [
        "scheduled_ordering",
        "scheduled_exercise",
        "scheduled_warrant",
        "scheduled_frequency",
    ]
    assert ids[start : start + 4] == expected
    for spec in figures_for("exotics")[start : start + 4]:
        assert spec.title and spec.blurb and spec.practice
        figure = spec.build()
        assert figure.layout.meta["section"] == "26.3"
        assert figure.layout.meta["figure"] == spec.id
