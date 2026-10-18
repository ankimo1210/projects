import io
import zipfile

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.fredmd import (
    FinalMacro,
    PanelMacro,
    RealTimeMacro,
    member_vintage,
    parse_vintage,
    transform,
    zip_vintages,
)
from bond_timing.pit import LookaheadError

VINTAGE = b"""sasdate,AAA,BBB,CCC,DDD,EEE,FFF,GGG
Transform:,1,2,4,5,6,7,3
1/1/2000,1,10,100,100,100,100,1
2/1/2000,2,12,110,110,121,110,4
3/1/2000,4,15,121,121,144,132,9
4/1/2000,,19,133.1,,169,,16
"""
LATER = b"""sasdate,BBB
Transform:,2
1/1/2000,10
2/1/2000,12
3/1/2000,15
4/1/2000,19
5/1/2000,
"""


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def test_parse_reads_codes_dates_and_blanks():
    v = parse_vintage(month("2000-05"), VINTAGE)
    assert v.tcodes == {"AAA": 1, "BBB": 2, "CCC": 4, "DDD": 5, "EEE": 6, "FFF": 7, "GGG": 3}
    assert list(v.levels.index.astype(str)) == ["2000-01", "2000-02", "2000-03", "2000-04"]
    assert np.isnan(v.levels.loc[month("2000-04"), "AAA"])


def test_every_tcode_matches_a_hand_calculation():
    t = parse_vintage(month("2000-05"), VINTAGE).transformed
    np.testing.assert_allclose(t["AAA"], [1, 2, 4, np.nan])
    np.testing.assert_allclose(t["BBB"], [np.nan, 2, 3, 4])
    np.testing.assert_allclose(t["CCC"], np.log([100, 110, 121, 133.1]))
    np.testing.assert_allclose(t["DDD"], [np.nan, np.log(1.1), np.log(1.1), np.nan])
    second = [
        np.nan,
        np.nan,
        np.log(144 / 121) - np.log(1.21),
        np.log(169 / 144) - np.log(144 / 121),
    ]
    np.testing.assert_allclose(t["EEE"], second)
    np.testing.assert_allclose(t["FFF"], [np.nan, np.nan, 0.1, np.nan])
    np.testing.assert_allclose(t["GGG"], [np.nan, np.nan, 2, 2])
    with pytest.raises(ValueError):
        transform(pd.Series([1.0]), 9)


def test_member_names_from_both_archives():
    assert member_vintage("Historical FRED-MD Vintages Final/1999-08.csv") == month("1999-08")
    assert member_vintage("FRED-MD_2024m03.csv") == month("2024-03")
    assert member_vintage("FRED-MD-2025m05.csv") == month("2025-05")
    assert member_vintage("2017-02.csv") == month("2017-02")
    assert member_vintage("Historical FRED-MD Vintages Final/ReadMe.pdf") is None


def test_zip_vintages_keys_every_csv_member():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Final/2000-05.csv", VINTAGE)
        archive.writestr("FRED-MD_2024m03.csv", LATER)
        archive.writestr("Final/ReadMe.pdf", b"%PDF")
    assert sorted(zip_vintages(buffer.getvalue())) == [month("2000-05"), month("2024-03")]


def test_real_time_view_keeps_each_series_lag():
    source = RealTimeMacro({month("2000-05"): parse_vintage(month("2000-05"), VINTAGE)}.__getitem__)
    view = source.view(month("2000-06"))
    lags = dict(zip(view.names, view.lags, strict=True))
    assert lags == {"AAA": 3, "BBB": 2, "CCC": 2, "DDD": 3, "EEE": 2, "FFF": 3, "GGG": 2}
    rows = pd.PeriodIndex([month("2000-05"), month("2000-06")])
    history = source.history(month("2000-06"), view, rows)
    np.testing.assert_allclose(history[:, view.names.index("BBB")], [3, 4])
    assert source.edge(month("2000-06"), view)[view.names.index("AAA")] == 4


def test_series_lagging_more_than_six_months_are_left_out():
    source = RealTimeMacro({month("2000-09"): parse_vintage(month("2000-09"), VINTAGE)}.__getitem__)
    assert source.view(month("2000-10")).names == ("BBB", "CCC", "EEE", "GGG")  # lag 6 kept, 7 not
    source = RealTimeMacro({month("2000-10"): parse_vintage(month("2000-10"), VINTAGE)}.__getitem__)
    assert source.view(month("2000-11")).names == ()


def test_edge_falls_back_and_marks_missing_series():
    vintages = {
        month("2000-05"): parse_vintage(month("2000-05"), VINTAGE),
        month("2000-06"): parse_vintage(month("2000-06"), LATER),
    }
    source = RealTimeMacro(vintages.__getitem__)
    view = source.view(month("2000-06"))
    edge = source.edge(month("2000-07"), view)
    assert np.isnan(edge[view.names.index("AAA")])
    assert edge[view.names.index("BBB")] == 4  # 2000-05 is blank; 2000-04 is the latest
    assert edge.shape == (len(view.names),)


def test_real_time_source_never_reads_the_decision_month_vintage():
    source = RealTimeMacro({}.__getitem__)
    with pytest.raises(KeyError):
        source.view(month("2000-06"))
    with pytest.raises(LookaheadError):
        source._frame_at(month("2000-06"), month("2000-06"))


def test_final_and_panel_sources():
    final = FinalMacro(parse_vintage(month("2019-02"), VINTAGE))
    view = final.view(month("2000-03"))
    assert set(view.lags) == {0}
    assert final.edge(month("2000-03"), view)[view.names.index("BBB")] == 3
    panel = PanelMacro(
        pd.DataFrame({"x": [1.0, 2.0, 3.0]}, index=pd.period_range("2000-01", periods=3, freq="M"))
    )
    pview = panel.view(month("2000-03"))
    assert pview.lags == (2,)
    assert panel.edge(month("2000-03"), pview)[0] == 1.0
