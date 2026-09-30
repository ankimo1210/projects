"""The §26.4 portal exposes the same four audited plots as the notebook."""

from report_builder.figures import figures_for


def test_gap_cards_follow_nonstandard_contracts_and_use_shared_figures():
    specs = figures_for("exotics")
    start = next(i for i, spec in enumerate(specs) if spec.id == "scheduled_frequency") + 1
    selected = specs[start : start + 4]
    assert [spec.id for spec in selected] == [
        "gap_payoff",
        "gap_decomposition",
        "gap_insurance",
        "gap_premium",
    ]
    for spec in selected:
        assert spec.title and spec.blurb and spec.practice
        figure = spec.build()
        assert figure.layout.meta["section"] == "26.4"
        assert figure.layout.meta["figure"] == spec.id
