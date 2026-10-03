"""Market-price-of-risk cards consume checked shared figures after the chooser."""

from report_builder.figures import figures_for


def test_market_price_of_risk_cards_follow_chooser_and_use_shared_figures():
    specs = figures_for("exotics")
    start = next(i for i, s in enumerate(specs) if s.id == "chooser_validation") + 1
    selected = specs[start : start + 4]
    assert [s.id for s in selected] == [
        "mpr_line",
        "mpr_riskless",
        "mpr_worlds",
        "mpr_validation",
    ]
    for s in selected:
        assert s.title and s.blurb and s.practice
        f = s.build()
        assert f.layout.meta["section"] == "28.1" and f.layout.meta["figure"] == s.id
