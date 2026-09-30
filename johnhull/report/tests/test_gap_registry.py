"""The §26.4 portal cards follow §26.3 and reuse the Book figures."""

from report_builder.figures import figures_for


def test_gap_cards_follow_nonstandard_and_share_figure_identity():
    ids = [spec.id for spec in figures_for("exotics")]
    start = ids.index("scheduled_frequency") + 1
    expected = ["gap_payoff", "gap_settlement_line", "gap_insurance", "gap_transfer_cost"]
    assert ids[start : start + 4] == expected
    for spec in figures_for("exotics")[start : start + 4]:
        assert spec.title and spec.blurb and spec.practice
        figure = spec.build()
        assert figure.layout.meta["section"] == "26.4"
        assert figure.layout.meta["figure"] == spec.id
