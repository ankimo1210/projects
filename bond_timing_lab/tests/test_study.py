import io
import zipfile

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.fredmd import Vintage
from bond_timing.data.store import store_bytes
from bond_timing.study import load_vintage_payloads, macro_pc1


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def archive(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        for name, content in members.items():
            handle.writestr(name, content)
    return buffer.getvalue()


def test_vintage_payloads_merge_both_archives_and_monthly_files(tmp_path):
    store_bytes(
        tmp_path,
        "fredmd",
        "hist_1999_2014",
        archive({"Final/1999-08.csv": b"a"}),
        url="u",
        filename="a.zip",
    )
    store_bytes(
        tmp_path,
        "fredmd",
        "hist_2015_2025",
        archive({"FRED-MD_2024m03.csv": b"b"}),
        url="u",
        filename="b.zip",
    )
    store_bytes(tmp_path, "fredmd", "monthly_2026-01", b"c", url="u", filename="c.csv")
    payloads = load_vintage_payloads(tmp_path)
    assert list(payloads) == [month("1999-08"), month("2024-03"), month("2026-01")]
    assert payloads[month("2026-01")] == b"c"


def test_macro_pc1_is_lagged_signed_and_scaled():
    index = pd.period_range("1990-01", periods=60, freq="M")
    rng = np.random.default_rng(0)
    common = rng.normal(size=60)
    levels = pd.DataFrame(
        {
            "INDPRO": common + rng.normal(0, 0.1, 60),
            **{f"S{j}": -common + rng.normal(0, 0.3, 60) for j in range(9)},
        },
        index=index,
    )
    vintage = Vintage(month("1995-01"), levels, {name: 1 for name in levels.columns})
    z = macro_pc1(vintage, index[2], index[-1])
    assert z.index[0] == index[2] and z.index[-1] == index[-1]
    lead = z.shift(-2).dropna()
    assert np.corrcoef(lead, levels["INDPRO"].reindex(lead.index))[0, 1] > 0.9
    assert z.std() == pytest.approx(1.0, abs=0.1)
