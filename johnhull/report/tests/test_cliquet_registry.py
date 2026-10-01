"""The portal exposes the four independently checked cliquet plots."""

from report_builder.figures import figures_for


def test_cliquet_cards_follow_forward_start_and_use_shared_figures():
    specs = figures_for("exotics")
    start = next(i for i, spec in enumerate(specs) if spec.id == "forward_fixed_expiry") + 1
    selected = specs[start : start + 4]
    assert [spec.id for spec in selected] == [
        "cliquet_reset",
        "cliquet_components",
        "cliquet_frequency",
        "cliquet_limits",
    ]
    for spec in selected:
        assert spec.title and spec.blurb and spec.practice
        figure = spec.build()
        assert figure.layout.meta["section"] == "26.6"
        assert figure.layout.meta["figure"] == spec.id
