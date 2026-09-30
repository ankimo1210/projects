"""The portal exposes the four independently checked forward-start plots."""

from report_builder.figures import figures_for


def test_forward_start_cards_follow_gap_options_and_use_shared_figures():
    specs = figures_for("exotics")
    start = next(i for i, spec in enumerate(specs) if spec.id == "gap_premium") + 1
    selected = specs[start : start + 4]
    assert [spec.id for spec in selected] == [
        "forward_contract",
        "forward_homogeneity",
        "forward_start_delay",
        "forward_fixed_expiry",
    ]
    for spec in selected:
        assert spec.title and spec.blurb and spec.practice
        figure = spec.build()
        assert figure.layout.meta["section"] == "26.5"
        assert figure.layout.meta["figure"] == spec.id
