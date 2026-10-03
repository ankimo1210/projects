"""Factor risk cards use the same evidence-checked lesson after one-factor risk."""

from report_builder.figures import figures_for


def test_factor_risk_cards_follow_one_factor_and_share_four_figures():
    specs = figures_for("exotics")
    start = next(i for i, s in enumerate(specs) if s.id == "risk_premium_validation") + 1
    selected = specs[start : start + 4]
    assert [s.id for s in selected] == [
        "factor_risk_contributions",
        "factor_risk_loading",
        "factor_risk_hedge",
        "factor_risk_validation",
    ]
    for s in selected:
        assert s.title and s.blurb and s.practice
        f = s.build()
        assert f.layout.meta["section"] == "28.2" and f.layout.meta["figure"] == s.id
