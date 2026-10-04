"""Four multi-factor cards follow the accepted numeraire cards."""

from report_builder.figures import figures_for


def test_multifactor_cards_follow_numeraire_and_use_checked_figures():
    specs = figures_for("exotics")
    start = next(i for i, s in enumerate(specs) if s.id == "martingale_numeraire_annuity") + 1
    selected = specs[start : start + 4]
    assert [s.id for s in selected] == [
        "factor_ratio_ito",
        "factor_ratio_conditional",
        "factor_basis_covariance",
        "factor_measure_price",
    ]
    for s in selected:
        f = s.build()
        assert s.title and s.blurb and s.practice
        assert f.layout.meta["section"] == "28.5" and f.layout.meta["figure"] == s.id
