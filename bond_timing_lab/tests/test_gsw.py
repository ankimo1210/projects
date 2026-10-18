from datetime import date

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.gsw import month_end_zeros, parse_curve, published_max_years

HEADER = "Date,BETA0,BETA1,BETA2,BETA3,SVENY01,SVENY02,SVENY03,SVENY08,SVENY10,TAU1,TAU2"
ROWS = (
    "1971-07-30,5,0,0,0,5,5,5,NA,NA,1,NA",
    "1971-08-31,6,-2,0,0,4.4,4.8,5.0,5.6,5.7,2,NA",
    "1971-09-10,5,0,0,0,5,5,5,5,5,1,NA",
)


def payload(rows=ROWS) -> bytes:
    return ("A note line\n\n" + HEADER + "\n" + "\n".join(rows) + "\n").encode()


def test_published_max_years_reads_the_longest_published_column():
    assert published_max_years(payload()) == {
        date(1971, 7, 30): 3,
        date(1971, 8, 31): 10,
        date(1971, 9, 10): 10,
    }


def test_month_end_zeros_cut_at_the_published_range_and_drop_a_month_in_progress():
    frame = month_end_zeros(parse_curve(payload()), [12, 36, 120])
    assert list(frame.index.astype(str)) == ["1971-07", "1971-08"]
    july, august = pd.Period("1971-07", "M"), pd.Period("1971-08", "M")
    assert frame.loc[july, 12] == pytest.approx(0.05)
    assert np.isnan(frame.loc[july, 120])
    # Nelson-Siegel day (TAU2 = NA): 6 - 2 (1 - e^{-1/2}) / (1/2) percent at one year, tau1 = 2
    assert frame.loc[august, 12] == pytest.approx((6 - 2 * (1 - np.exp(-0.5)) / 0.5) / 100)
    assert np.isfinite(frame.loc[august, 120])


def test_days_by_month_groups_every_observation():
    grouped = parse_curve(payload()).days_by_month()
    assert [len(v) for v in grouped.values()] == [1, 1, 1]
    assert pd.Period("1971-09", "M") in grouped
