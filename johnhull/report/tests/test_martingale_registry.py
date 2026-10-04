"""Conditional martingale cards share evidence-checked Book figures."""

from report_builder.figures import figures_for


def test_martingale_cards_follow_factor_risk_and_share_four_figures():
    specs = figures_for("exotics")
    start = next(i for i, s in enumerate(specs) if s.id == "factor_risk_validation") + 1
    selected = specs[start : start + 4]
    assert [s.id for s in selected] == [
        "martingale_ito",
        "martingale_conditional",
        "martingale_conditional_mc",
        "martingale_pricing",
    ]
    for s in selected:
        assert s.title and s.blurb and s.practice
        f = s.build()
        assert f.layout.meta["section"] == "28.3" and f.layout.meta["figure"] == s.id
