from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from quant_textbook.treasury_data import (
    DEFAULT_TENORS,
    TREASURY_METHOD_BREAK,
    audit_treasury_data,
    load_treasury_snapshot,
    parse_treasury_xml,
)

FIXTURES = Path(__file__).with_name("fixtures")


def _tiny_xml() -> bytes:
    return b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
 xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
 xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
 <entry><content type="application/xml"><m:properties>
  <d:NEW_DATE m:type="Edm.DateTime">2024-01-03T00:00:00</d:NEW_DATE>
  <d:BC_3MONTH m:type="Edm.Double">5.40</d:BC_3MONTH>
  <d:BC_2YEAR m:type="Edm.Double">4.33</d:BC_2YEAR>
  <d:BC_5YEAR m:type="Edm.Double">3.97</d:BC_5YEAR>
  <d:BC_10YEAR m:type="Edm.Double">3.91</d:BC_10YEAR>
  <d:BC_30YEAR m:type="Edm.Double">4.05</d:BC_30YEAR>
 </m:properties></content></entry>
</feed>"""


def test_parse_treasury_xml_preserves_date_tenor_grain_and_units() -> None:
    frame = parse_treasury_xml(_tiny_xml())
    assert frame.columns.tolist() == ["date", *DEFAULT_TENORS]
    assert frame.loc[0, "date"] == pd.Timestamp("2024-01-03")
    assert frame.loc[0, "10y"] == pytest.approx(3.91)


def test_parse_treasury_xml_ignores_display_only_phantom_rows() -> None:
    frame = parse_treasury_xml((FIXTURES / "treasury_phantom_row.xml").read_bytes())
    assert frame["date"].tolist() == [pd.Timestamp("2010-10-12")]
    assert frame.loc[0, "30y"] == pytest.approx(3.93)


def test_parse_treasury_xml_rejects_a_feed_with_only_phantom_rows() -> None:
    payload = (FIXTURES / "treasury_phantom_row.xml").read_bytes()
    start = payload.index(b"<entry>", payload.index(b"</entry>") + len(b"</entry>"))
    end = payload.index(b"</entry>", start) + len(b"</entry>")
    real_entry = payload[start:end]
    with pytest.raises(ValueError, match="no usable tenor observations"):
        parse_treasury_xml(payload.replace(real_entry, b""))


def test_bundled_snapshot_has_fixed_provenance_and_clean_required_tenors() -> None:
    dataset = load_treasury_snapshot()
    assert dataset.metadata.start_date == "2015-01-02"
    assert dataset.metadata.end_date == "2025-12-31"
    assert dataset.metadata.row_count == 2750
    assert dataset.metadata.tenors == DEFAULT_TENORS
    assert (
        dataset.metadata.snapshot_sha256
        == "6ddef9605abbf02c6a4526a51f098135b41da1a437915623af672b1c7bcbd295"
    )
    assert dataset.metadata.terms_reviewed_at == "2026-08-10"
    assert "source attribution" in dataset.metadata.redistribution_decision
    assert dataset.quality.accepted
    assert dataset.quality.duplicate_dates == 0
    assert sum(dataset.quality.missing_by_tenor.values()) == 0
    assert dataset.quality.methodology_break_present
    assert dataset.frame["date"].is_monotonic_increasing


def test_quality_audit_rejects_duplicate_dates_and_missing_required_values() -> None:
    frame = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-02")],
            "3m": [5.4, 5.4],
            "2y": [4.3, 4.3],
            "5y": [4.0, None],
            "10y": [3.9, 3.9],
            "30y": [4.1, 4.1],
        }
    )
    quality = audit_treasury_data(frame)
    assert not quality.accepted
    assert quality.duplicate_dates == 1
    assert quality.missing_by_tenor["5y"] == 1


def test_quality_audit_records_methodology_break_as_a_warning_not_missing_data() -> None:
    frame = pd.DataFrame(
        {
            "date": [TREASURY_METHOD_BREAK - pd.Timedelta(days=1), TREASURY_METHOD_BREAK],
            **{tenor: [1.0, 1.1] for tenor in DEFAULT_TENORS},
        }
    )
    quality = audit_treasury_data(frame)
    assert quality.accepted
    assert quality.methodology_break_present
    assert "methodology" in quality.warnings[0]


@pytest.mark.parametrize("payload", [b"", b"not xml", b"<feed></feed>"])
def test_parse_treasury_xml_rejects_empty_malformed_or_dataless_payloads(
    payload: bytes,
) -> None:
    with pytest.raises(ValueError):
        parse_treasury_xml(payload)
