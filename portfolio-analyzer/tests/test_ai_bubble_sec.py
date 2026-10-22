"""Parse SEC companyfacts into point-in-time long rows (no network)."""

from __future__ import annotations

import hashlib
import io

from portfolio_analyzer.ai_bubble.inputs import audit_inputs
from portfolio_analyzer.ai_bubble.sec import (
    USER_AGENT,
    accepted_times,
    choose_concepts,
    companyfacts_url,
    fetch_json,
    parse_companyfacts,
    submissions_url,
)

RAW = {
    "cik": 1045810,
    "entityName": "TEST CORP",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {
                            "start": "2025-01-27",
                            "end": "2025-04-27",
                            "val": 44062000000,
                            "accn": "0001045810-25-000116",
                            "fy": 2026,
                            "fp": "Q1",
                            "form": "10-Q",
                            "filed": "2025-05-28",
                        },
                        {
                            "start": "2025-01-27",
                            "end": "2025-04-27",
                            "val": 44062000000,
                            "accn": "0001045810-26-000010",
                            "fy": 2027,
                            "fp": "Q1",
                            "form": "10-Q",
                            "filed": "2026-05-29",
                        },
                        {
                            "start": "2025-01-27",
                            "end": "2025-04-27",
                            "val": 1,
                            "accn": "0001045810-25-000099",
                            "form": "8-K",
                            "filed": "2025-05-28",
                        },
                    ]
                }
            },
            "CashAndCashEquivalentsAtCarryingValue": {
                "units": {
                    "USD": [
                        {
                            "end": "2025-04-27",
                            "val": 15234000000,
                            "accn": "0001045810-25-000116",
                            "fy": 2026,
                            "fp": "Q1",
                            "form": "10-Q",
                            "filed": "2025-05-28",
                        }
                    ]
                }
            },
        },
        "ifrs-full": {
            "Revenue": {
                "units": {
                    "TWD": [
                        {
                            "start": "2025-01-01",
                            "end": "2025-12-31",
                            "val": 3800000000000,
                            "accn": "0001046179-26-000005",
                            "form": "20-F",
                            "filed": "2026-04-10",
                        }
                    ]
                }
            }
        },
    },
}

ACCEPTED = {"0001045810-25-000116": "2025-05-28T16:21:03.000Z"}


def parse(concepts):
    return parse_companyfacts(RAW, "NVDA", ACCEPTED, concepts, retrieved_at="2026-10-21T01:00:00Z")


def by_document(rows, accn):
    return next(r for r in rows if r["document_id"] == accn)


def test_available_at_waits_for_the_weekday_after_the_filing_date():
    # SEC's acceptanceDateTime runs ahead of true UTC by the Eastern offset, so
    # only the filing date is trusted: filed Wed 2025-05-28 -> Thu 00:00 EDT.
    row = by_document(parse({"revenue": "us-gaap:Revenues"}), "0001045810-25-000116")
    assert row["published_at"] == "2025-05-28T04:00:00Z"
    assert row["available_at"] == "2025-05-29T04:00:00Z"


def test_friday_filings_become_available_on_monday():
    row = by_document(parse({"revenue": "us-gaap:Revenues"}), "0001045810-26-000010")
    assert row["available_at"] == "2026-06-01T04:00:00Z"


def test_winter_filings_use_eastern_standard_time():
    row = parse({"revenue": "ifrs-full:Revenue"})[0]
    # filed Fri 2026-04-10 (EDT) -> Mon 2026-04-13 00:00 EDT
    assert row["available_at"] == "2026-04-13T04:00:00Z"
    feb = dict(RAW["facts"]["ifrs-full"]["Revenue"]["units"]["TWD"][0], filed="2026-02-25")
    raw = {"cik": 1, "facts": {"ifrs-full": {"Revenue": {"units": {"TWD": [feb]}}}}}
    rows = parse_companyfacts(
        raw, "TSM", {}, {"revenue": "ifrs-full:Revenue"}, retrieved_at="2026-10-21T01:00:00Z"
    )
    assert rows[0]["available_at"] == "2026-02-26T05:00:00Z"


def test_raw_acceptance_time_is_kept_for_audit_only():
    rows = parse({"revenue": "us-gaap:Revenues"})
    assert (
        by_document(rows, "0001045810-25-000116")["sec_acceptance_raw"]
        == "2025-05-28T16:21:03.000Z"
    )
    assert by_document(rows, "0001045810-26-000010")["sec_acceptance_raw"] is None


def test_only_periodic_report_forms_are_kept():
    rows = parse({"revenue": "us-gaap:Revenues"})
    assert sorted(r["document_id"] for r in rows) == [
        "0001045810-25-000116",
        "0001045810-26-000010",
    ]


def test_rows_carry_the_contract_fields_and_pass_audit():
    rows = parse(
        {"revenue": "us-gaap:Revenues", "cash": "us-gaap:CashAndCashEquivalentsAtCarryingValue"}
    )
    assert audit_inputs(rows)["ok"] is True
    cash = next(r for r in rows if r["metric"] == "cash")
    assert (cash["period_start"], cash["period_end"]) == ("2025-04-27", "2025-04-27")
    assert cash["unit"] == "USD"
    assert cash["accounting_basis"] == "US-GAAP"
    assert cash["source_url"] == (
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000116/"
    )


def test_ifrs_concepts_are_labelled_ifrs_and_keep_their_currency():
    rows = parse({"revenue": "ifrs-full:Revenue"})
    assert [(r["accounting_basis"], r["unit"], r["value"]) for r in rows] == [
        ("IFRS", "TWD", 3800000000000.0)
    ]


def test_absent_concept_yields_no_rows():
    assert parse({"capex": "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"}) == []


def test_accepted_times_reads_recent_and_older_submission_pages():
    recent = {
        "filings": {
            "recent": {
                "accessionNumber": ["a-1", "a-2"],
                "acceptanceDateTime": ["2026-05-29T16:05:01.000Z", "2025-05-28T16:21:03.000Z"],
            }
        }
    }
    older = {"accessionNumber": ["a-0"], "acceptanceDateTime": ["2019-01-02T17:00:00.000Z"]}
    assert accepted_times([recent, older]) == {
        "a-1": "2026-05-29T16:05:01.000Z",
        "a-2": "2025-05-28T16:21:03.000Z",
        "a-0": "2019-01-02T17:00:00.000Z",
    }


def test_concept_choice_takes_the_first_candidate_with_periodic_facts():
    candidates = {
        "revenue": [
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:Revenues",
        ],
        "capex": ["us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"],
    }
    assert choose_concepts(RAW, candidates) == {"revenue": "us-gaap:Revenues"}


def test_fetch_uses_data_sec_gov_and_a_user_agent_without_an_email():
    seen = []

    def opener(request, timeout):
        seen.append((request.full_url, dict(request.header_items()), timeout))
        return io.BytesIO(b'{"cik": 1}')

    assert fetch_json(companyfacts_url(1045810), opener=opener) == (
        {"cik": 1},
        hashlib.sha256(b'{"cik": 1}').hexdigest(),
        b'{"cik": 1}',
    )
    url, headers, _ = seen[0]
    assert url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json"
    assert headers["User-agent"] == USER_AGENT
    assert "@" not in USER_AGENT
    assert submissions_url(1045810) == "https://data.sec.gov/submissions/CIK0001045810.json"


def test_priority_list_fills_history_without_colliding_on_the_same_filing():
    asc606 = {
        "units": {
            "USD": [
                {
                    "start": "2025-01-27",
                    "end": "2025-04-27",
                    "val": 44000000000,
                    "accn": "0001045810-25-000116",
                    "form": "10-Q",
                    "filed": "2025-05-28",
                },
            ]
        }
    }
    older = {
        "units": {
            "USD": [
                {
                    "start": "2017-01-30",
                    "end": "2017-04-30",
                    "val": 1937000000,
                    "accn": "0001045810-17-000101",
                    "form": "10-Q",
                    "filed": "2017-05-23",
                },
            ]
        }
    }
    raw = {
        "cik": 1045810,
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": asc606,
                "Revenues": {
                    "units": {
                        "USD": RAW["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
                        + older["units"]["USD"]
                    }
                },
            }
        },
    }
    rows = parse_companyfacts(
        raw,
        "NVDA",
        {},
        {
            "revenue": [
                "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                "us-gaap:Revenues",
            ]
        },
        retrieved_at="2026-10-21T01:00:00Z",
    )
    picked = {(r["period_end"], r["document_id"]): (r["value"], r["concept"]) for r in rows}
    assert picked[("2025-04-27", "0001045810-25-000116")] == (
        44000000000.0,
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    )
    assert picked[("2017-04-30", "0001045810-17-000101")] == (1937000000.0, "us-gaap:Revenues")
    assert picked[("2025-04-27", "0001045810-26-000010")][1] == "us-gaap:Revenues"


def _cash_fact(val, accn, form, fp, fy):
    return {
        "end": "2012-12-31",
        "val": val,
        "accn": accn,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": "2015-05-15",
    }


def test_same_day_conflict_keeps_the_annual_report_and_notes_the_other():
    # Arista filed a 10-K and a 10-Q on 2015-05-15; the 10-Q dates a cash fact 2012-12-31
    raw = {
        "cik": 1596532,
        "facts": {
            "us-gaap": {
                "CashAndCashEquivalentsAtCarryingValue": {
                    "units": {
                        "USD": [
                            _cash_fact(88_655_000, "0001596532-15-000011", "10-K", "FY", 2014),
                            _cash_fact(113_664_000, "0001596532-15-000013", "10-Q", "Q1", 2015),
                        ]
                    }
                }
            }
        },
    }
    rows = parse_companyfacts(
        raw,
        "ANET",
        {},
        {"cash": "us-gaap:CashAndCashEquivalentsAtCarryingValue"},
        retrieved_at="2026-10-21T02:00:00Z",
    )
    assert [r["value"] for r in rows] == [88_655_000.0]
    assert rows[0]["same_day_conflict"] == [
        {"document_id": "0001596532-15-000013", "form": "10-Q", "value": 113_664_000.0}
    ]


def test_same_day_conflict_between_two_quarterly_reports_is_left_for_the_selection_to_refuse():
    raw = {
        "cik": 1,
        "facts": {
            "us-gaap": {
                "CashAndCashEquivalentsAtCarryingValue": {
                    "units": {
                        "USD": [
                            _cash_fact(1, "a", "10-Q", "Q1", 2015),
                            _cash_fact(2, "b", "10-Q/A", "Q1", 2015),
                        ]
                    }
                }
            }
        },
    }
    rows = parse_companyfacts(
        raw,
        "X",
        {},
        {"cash": "us-gaap:CashAndCashEquivalentsAtCarryingValue"},
        retrieved_at="2026-10-21T02:00:00Z",
    )
    assert sorted(r["value"] for r in rows) == [1.0, 2.0]
