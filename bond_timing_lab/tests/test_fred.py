import os

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.fred import (
    URL,
    bey_to_cc,
    bill_bey,
    cash_returns,
    missing_months,
    month_end_last,
    parse_fred_csv,
)

CSV = (
    b"observation_date,DTB3\n2020-01-30,1.50\n2020-01-31,\n2020-02-27,1.40\n"
    b"2020-02-28,1.45\n2020-04-01,.\n2020-04-30,1.00\n"
)


def test_month_end_last_takes_the_last_valid_day_and_lists_gaps():
    month_end = month_end_last(parse_fred_csv(CSV))
    assert month_end[pd.Period("2020-01", "M")] == 1.50
    assert month_end[pd.Period("2020-02", "M")] == 1.45
    assert np.isnan(month_end[pd.Period("2020-03", "M")])
    assert month_end[pd.Period("2020-04", "M")] == 1.00
    assert missing_months(month_end) == ["2020-03"]


def test_bond_equivalent_yield_and_cash_alignment():
    index = pd.period_range("2020-01", periods=2, freq="M")
    bey = bill_bey(pd.Series([5.0, 4.0], index=index))
    assert bey.iloc[0] == pytest.approx(365 * 0.05 / (360 - 91 * 0.05))
    cash = cash_returns(bey)
    assert np.isnan(cash.iloc[0])
    assert cash.iloc[1] == pytest.approx(bey.iloc[0] / 12)


def test_bey_to_cc_matches_the_91_day_compounding():
    assert bey_to_cc(pd.Series([0.05])).iloc[0] == pytest.approx(
        np.log(1 + 0.05 * 91 / 365) * 365 / 91
    )


@pytest.mark.skipif(os.environ.get("BOND_TIMING_NETWORK") != "1", reason="network test")
def test_dtb3_endpoint_returns_the_expected_header():
    from bond_timing.data.store import fetch

    assert fetch(URL.format(series="DTB3")).startswith(b"observation_date,DTB3")
