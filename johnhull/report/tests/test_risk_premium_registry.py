"""Market risk cards share evidence-checked figures after chooser."""

from report_builder.figures import figures_for


def test_market_risk_cards_follow_chooser_and_use_shared_figures():
    specs = figures_for("exotics")
    start = next(i for i, s in enumerate(specs) if s.id == "chooser_validation") + 1
    selected = specs[start : start + 4]
    assert [s.id for s in selected] == [
        "risk_premium_loading",
        "risk_premium_hedge",
        "risk_premium_density",
        "risk_premium_validation",
    ]
    for s in selected:
        assert s.title and s.blurb and s.practice
        f = s.build()
        assert f.layout.meta["section"] == "28.1" and f.layout.meta["figure"] == s.id
