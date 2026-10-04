"""§28.4 cards follow §28.3 and share checked Book figures."""

from report_builder.figures import figures_for


def test_numeraire_cards_follow_martingale_and_share_figures():
    specs = figures_for("exotics")
    start = next(i for i, s in enumerate(specs) if s.id == "martingale_pricing") + 1
    selected = specs[start : start + 4]
    assert [s.id for s in selected] == [
        "martingale_numeraire_pricing",
        "martingale_numeraire_forward",
        "martingale_numeraire_payment",
        "martingale_numeraire_annuity",
    ]
    for s in selected:
        assert s.title and s.blurb and s.practice
        f = s.build()
        assert f.layout.meta["section"] == "28.4" and f.layout.meta["figure"] == s.id
