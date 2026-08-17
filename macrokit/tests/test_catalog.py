from pathlib import Path

import pytest

from macrokit.catalog import CatalogError, Indicator, load_catalog

FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_every_indicator_across_country_directories():
    catalog = load_catalog(FIXTURES / "catalog_ok")
    assert set(catalog) == {"us_core_pce", "us_core_pce_yoy", "jp_scheduled_earnings"}
    assert isinstance(catalog["us_core_pce"], Indicator)


def test_keeps_source_specific_fields_verbatim():
    # source_ref is deliberately untyped: each source has its own identifier
    # shape (series_id vs stats_id vs tenor), and the adapter owns that meaning.
    catalog = load_catalog(FIXTURES / "catalog_ok")
    assert catalog["us_core_pce"].source_ref == {"series_id": "PCEPILFE"}
    assert catalog["jp_scheduled_earnings"].source_ref == {"stats_id": "0003084821"}


def test_japanese_indicators_declare_snapshot_vintage():
    catalog = load_catalog(FIXTURES / "catalog_ok")
    assert catalog["jp_scheduled_earnings"].vintage == "snapshot"
    assert catalog["us_core_pce"].vintage == "alfred"


def test_release_rule_is_parsed_when_present_and_none_when_absent():
    catalog = load_catalog(FIXTURES / "catalog_ok")
    rule = catalog["jp_scheduled_earnings"].release_rule
    assert rule is not None
    assert rule.kind == "nth_business_day"
    assert rule.n == 5
    assert rule.tz == "Asia/Tokyo"
    # US indicators get their calendar from the FRED releases API, not a rule.
    assert catalog["us_core_pce"].release_rule is None


def test_rejects_duplicate_names(tmp_path):
    (tmp_path / "us").mkdir()
    (tmp_path / "us" / "a.yaml").write_text(
        "- {name: dup, country: US, block: prices, title_ja: A, source: alfred,\n"
        "   source_ref: {series_id: X}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred}\n",
        encoding="utf-8",
    )
    (tmp_path / "us" / "b.yaml").write_text(
        "- {name: dup, country: US, block: prices, title_ja: B, source: alfred,\n"
        "   source_ref: {series_id: Y}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="duplicate indicator name: dup"):
        load_catalog(tmp_path)


def test_rejects_chain_reference_to_a_missing_indicator(tmp_path):
    (tmp_path / "us").mkdir()
    (tmp_path / "us" / "a.yaml").write_text(
        "- {name: real, country: US, block: prices, title_ja: A, source: alfred,\n"
        "   source_ref: {series_id: X}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred,\n"
        "   chain: {downstream: [ghost]}}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match=r"real.downstream refers to unknown indicator: ghost"):
        load_catalog(tmp_path)


def test_rejects_a_cycle_in_the_chain_graph(tmp_path):
    (tmp_path / "jp").mkdir()
    (tmp_path / "jp" / "a.yaml").write_text(
        "- {name: a, country: JP, block: prices, title_ja: A, source: estat,\n"
        "   source_ref: {stats_id: '1'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {downstream: [b]}}\n"
        "- {name: b, country: JP, block: prices, title_ja: B, source: estat,\n"
        "   source_ref: {stats_id: '2'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {downstream: [a]}}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="cycle in chain graph"):
        load_catalog(tmp_path)


def test_diamond_shaped_chain_is_not_a_cycle(tmp_path):
    # a -> b -> d and a -> c -> d: d is reached twice via two different
    # paths. That is convergence, not a cycle, and must load cleanly.
    (tmp_path / "jp").mkdir()
    (tmp_path / "jp" / "a.yaml").write_text(
        "- {name: a, country: JP, block: prices, title_ja: A, source: estat,\n"
        "   source_ref: {stats_id: '1'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {downstream: [b, c]}}\n"
        "- {name: b, country: JP, block: prices, title_ja: B, source: estat,\n"
        "   source_ref: {stats_id: '2'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {downstream: [d]}}\n"
        "- {name: c, country: JP, block: prices, title_ja: C, source: estat,\n"
        "   source_ref: {stats_id: '3'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {downstream: [d]}}\n"
        "- {name: d, country: JP, block: prices, title_ja: D, source: estat,\n"
        "   source_ref: {stats_id: '4'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot}\n",
        encoding="utf-8",
    )
    catalog = load_catalog(tmp_path)
    assert set(catalog) == {"a", "b", "c", "d"}


def test_rejects_a_cycle_declared_only_through_upstream(tmp_path):
    # No downstream edge exists anywhere here; the cycle is only visible if
    # upstream declarations are normalised into the same edge set.
    (tmp_path / "jp").mkdir()
    (tmp_path / "jp" / "a.yaml").write_text(
        "- {name: a, country: JP, block: prices, title_ja: A, source: estat,\n"
        "   source_ref: {stats_id: '1'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {upstream: [b]}}\n"
        "- {name: b, country: JP, block: prices, title_ja: B, source: estat,\n"
        "   source_ref: {stats_id: '2'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {upstream: [a]}}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match=r"cycle in chain graph"):
        load_catalog(tmp_path)


def test_rejects_an_unknown_field_so_typos_do_not_pass_silently(tmp_path):
    (tmp_path / "us").mkdir()
    (tmp_path / "us" / "a.yaml").write_text(
        "- {name: a, country: US, block: prices, title_ja: A, source: alfred,\n"
        "   source_ref: {series_id: X}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred, viantge: typo}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="viantge"):
        load_catalog(tmp_path)
