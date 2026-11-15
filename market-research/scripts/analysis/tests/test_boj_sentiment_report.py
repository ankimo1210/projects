"""Data-contract checks for the BOJ paragraph report."""

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "boj_sentiment_report.py"
SPEC = importlib.util.spec_from_file_location("boj_sentiment_report", MODULE_PATH)
boj = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = boj
SPEC.loader.exec_module(boj)


@pytest.fixture
def historical_inputs():
    """A policy balance of +25; economy/government must not enter its denominator."""
    labels = ["hawkish", "hawkish", "dovish", "neutral"]
    snapshot = {
        "model": {"id": "model", "revision": "fixed"},
        "meetings": [{"date": "2026-10-30", "published_on": "2026-11-10"}],
        "paragraphs": [
            {"id": str(i), "meeting": "2026-10-30", "section": "policy", "label": label}
            for i, label in enumerate(labels)
        ]
        + [
            {"id": "economy", "meeting": "2026-10-30", "section": "economy", "label": "dovish"},
            {"id": "government", "meeting": "2026-10-30", "section": "government", "label": None},
        ],
    }
    rates = {
        "sources": [
            {
                "date": "2026-10-30",
                "target_percent": 1.25,
                "url": "https://www.boj.or.jp/decision.pdf",
            }
        ]
    }
    return snapshot, rates


def test_history_uses_only_policy_counts_and_preserves_decision_and_release_dates(
    historical_inputs,
):
    snapshot, rates = historical_inputs
    row = boj.historical_series([snapshot], rates)[0]
    assert row["balance"] == 25
    assert row["n"] == 4
    assert row["counts"] == {"hawkish": 2, "dovish": 1, "neutral": 1}
    assert (row["meeting"], row["published_on"], row["rate_percent"]) == (
        "2026-10-30",
        "2026-11-10",
        1.25,
    )


@pytest.mark.parametrize(
    "problem",
    [
        "missing_rate",
        "duplicate_rate",
        "duplicate_meeting",
        "nonfinite_rate",
        "release_before_meeting",
        "different_model",
    ],
)
def test_history_rejects_ambiguous_or_incomparable_inputs(historical_inputs, problem):
    import copy

    snapshot, rates = historical_inputs
    snapshots = [snapshot]
    if problem == "missing_rate":
        rates["sources"].clear()
    elif problem == "duplicate_rate":
        rates["sources"] *= 2
    elif problem == "duplicate_meeting":
        snapshots.append(copy.deepcopy(snapshot))
    elif problem == "nonfinite_rate":
        rates["sources"][0]["target_percent"] = float("nan")
    elif problem == "release_before_meeting":
        snapshot["meetings"][0]["published_on"] = "2026-10-29"
    else:
        other = copy.deepcopy(snapshot)
        other["model"]["revision"] = "different"
        snapshots.append(other)
    with pytest.raises(ValueError):
        boj.historical_series(snapshots, rates)


def test_current_year_index_keeps_published_pdf_meetings_and_excludes_future_rows():
    html = """<table>
    <tr><td>2026年11月10日</td><td><a href="/mopo/mpmsche_minu/opinion_2026/opi261030.pdf">October</a></td></tr>
    <tr><td>2026年2月2日</td><td><a href="/mopo/mpmsche_minu/opinion_2026/opi260123.htm">January</a></td></tr>
    <tr><td>2026年12月28日</td><td><a href="/mopo/mpmsche_minu/opinion_2026/opi261218.pdf">December</a></td></tr>
    </table>"""
    assert boj.parse_index(html, 2026, date(2026, 11, 11)) == [
        {
            "path": "/mopo/mpmsche_minu/opinion_2026/opi260123.htm",
            "date": "2026-01-23",
            "published_on": "2026-02-02",
        },
        {
            "path": "/mopo/mpmsche_minu/opinion_2026/opi261030.pdf",
            "date": "2026-10-30",
            "published_on": "2026-11-10",
        },
    ]


@pytest.mark.parametrize(
    "language,text,expected",
    [
        (
            "ja",
            """Ⅰ．金融経済情勢に関する意見
（経済情勢）
⚫ 経済は緩やかに回復している。
1
「金融政策決定会合における主な意見」は編集された要約である。
1
\fⅡ．金融政策運営に関する意見
⚫ 現時点での利 上 げは
  避けるべきである。
⚫ 政策金利を引き上げ、
2
\f金融緩和の度合いを調整する。
Ⅲ．政府の意見
（財務省）
⚫ 適切な政策運営を期待する。
以上
3
""",
            [
                ("economy", "経済は緩やかに回復している。"),
                ("policy", "現時点での利上げは避けるべきである。"),
                ("policy", "政策金利を引き上げ、金融緩和の度合いを調整する。"),
                ("government", "適切な政策運営を期待する。"),
            ],
        ),
        (
            "en",
            """I. Opinions on Economic and Financial Developments
Economic Developments
• The economy has recovered moderately.
1
English translation prepared by the Bank's staff.
2
Summary of Opinions is made through a specified process.
1
\fII. Opinions on Monetary Policy
⚫ Raising interest rates should
  be avoided at present.
⚫ The policy interest rate should be raised
2
\fand the degree of monetary accommodation adjusted.
III. Opinions from Government Representatives
Ministry of Finance
⚫ The government expects appropriate policy conduct.
3
""",
            [
                ("economy", "The economy has recovered moderately."),
                ("policy", "Raising interest rates should be avoided at present."),
                (
                    "policy",
                    "The policy interest rate should be raised and the degree of monetary accommodation adjusted.",
                ),
                ("government", "The government expects appropriate policy conduct."),
            ],
        ),
    ],
)
@pytest.mark.parametrize("inline_footnote", [False, True])
def test_pdf_paragraphs_keep_negation_across_pages_without_footnotes(
    language, text, expected, inline_footnote
):
    if inline_footnote:
        text = text.replace("\n1\n", "\n1 ", 1)
    rows = boj.parse_pdf_document(text, language)
    assert [(row["section"], row["text"]) for row in rows] == expected


def test_pdf_english_preserves_dashes_and_suspended_hyphens():
    text = """I. Opinions on Economic and Financial Developments
Economic Developments
⚫ The economy has recovered moderately.
II. Opinions on Monetary Policy
⚫ The medium- to long-term outlook -- both of which matter -- remains uncertain.
⚫ The July-
August period was weak.
⚫ A medium-
to long-term expectation matters.
III. Opinions from Government Representatives
Ministry of Finance
⚫ The government expects appropriate policy conduct.
1
"""
    rows = boj.parse_pdf_document(text, "en")
    assert [row["text"] for row in rows if row["section"] == "policy"] == [
        "The medium- to long-term outlook -- both of which matter -- remains uncertain.",
        "The July-August period was weak.",
        "A medium- to long-term expectation matters.",
    ]


def document(policy="Raise the policy rate.", extra=""):
    return f"""<nav><li>Outside</li></nav><main id="contents"><h1>Meeting</h1>
    <p>February 3, 2025</p><ul><li>PDF download</li></ul>
    <h2>I Economic and Financial Developments</h2><h3>Prices</h3>
    <ul><li>Inflation is 2 percent.<sup>1</sup></li></ul>
    <h2>II Opinions on Monetary Policy</h2><ul><li>{policy}</li>{extra}</ul>
    <h2>III Opinions from Government Representatives</h2><h3>Ministry</h3>
    <ul><li>Government view.</li></ul><ol><li>Footnote.</li></ol></main>"""


def test_extract_preserves_units_and_excludes_navigation_and_footnotes():
    result = boj.parse_document(document())
    assert [(r["section"], r["text"]) for r in result] == [
        ("economy", "Inflation is 2 percent."),
        ("policy", "Raise the policy rate."),
        ("government", "Government view."),
    ]


def test_alignment_rejects_missing_or_reordered_sections():
    rows = boj.parse_document(document())
    with pytest.raises(ValueError, match="alignment"):
        boj.align_documents(rows, rows[:-1], "2025-01-24")
    with pytest.raises(ValueError, match="alignment"):
        boj.align_documents(rows, list(reversed(rows)), "2025-01-24")


def test_alignment_has_stable_ids_and_keeps_government_separate():
    rows = boj.parse_document(document())
    paired = boj.align_documents(rows, rows, "2025-01-24")
    assert [p["id"] for p in paired] == ["2025-01-24-001", "2025-01-24-002", "2025-01-24-003"]
    assert paired[-1]["section"] == "government"
    assert paired[1]["ja"] == paired[1]["en"] == "Raise the policy rate."


def test_prediction_keeps_uncertainty_separate_from_neutral():
    p = boj.prediction({"hawkish": 0.49, "dovish": 0.48, "neutral": 0.03})
    assert p["label"] == "hawkish"
    assert p["review"] is True
    assert p["score"] == pytest.approx(0.01)
    assert p["margin"] == pytest.approx(0.01)


@pytest.mark.parametrize(
    "values",
    [
        {"hawkish": float("nan"), "dovish": 0.2, "neutral": 0.8},
        {"hawkish": 0.8, "dovish": 0.8, "neutral": 0.1},
        {"positive": 0.8, "negative": 0.1, "neutral": 0.1},
    ],
)
def test_invalid_or_generic_sentiment_scores_are_rejected(values):
    with pytest.raises(ValueError, match="probabilities"):
        boj.prediction(values)


def test_long_inputs_fail_instead_of_silently_truncating():
    boj.check_token_lengths([512, 32], 512)
    with pytest.raises(ValueError, match="token"):
        boj.check_token_lengths([513], 512)


def test_summary_counts_policy_paragraphs_only():
    rows = boj.align_documents(
        boj.parse_document(document()), boj.parse_document(document()), "2025-01-24"
    )
    for row in rows:
        row.update(boj.prediction({"dovish": 0.1, "hawkish": 0.8, "neutral": 0.1}))
    summary = boj.summarize(rows, [{"date": "2025-01-24"}])
    assert summary[0]["n"] == 1
    assert summary[0]["counts"] == {"dovish": 0, "hawkish": 1, "neutral": 0}


def test_json_embedding_cannot_end_the_script_element():
    encoded = boj.safe_json({"ja": "</script><img src=x onerror=alert(1)>"})
    assert "</script>" not in encoded
    import json

    assert json.loads(encoded)["ja"].startswith("</script>")


@pytest.mark.parametrize("mistake", ["stale_source", "wrong_quote", "skipped_meeting", None])
def test_reading_review_binds_quotes_to_the_adjacent_meeting(mistake):
    dates = ["2025-07-31", "2025-09-19", "2025-10-30"]
    ids = [f"{date}-015" for date in dates]
    source_hashes = {date: str(i) * 64 for i, date in enumerate(dates, 1)}
    snapshot = {
        "meetings": [
            {"date": date, "documents": {"ja": {"sha256": source_hashes[date]}}} for date in dates
        ],
        "paragraphs": [
            {"id": id_, "meeting": date, "section": "policy", "ja": "政策金利を調整する。"}
            for date, id_ in zip(dates, ids, strict=True)
        ],
    }
    review = {
        "schema": 1,
        "reviewed_meetings": dates[-1:],
        "source_sha256": {date: source_hashes[date] for date in dates[1:]},
        "readings": [
            {"id": ids[-1], "label": None, "evidence": "調整する", "note": "方向を保留。"}
        ],
        "comparisons": [
            {
                "topic": "金利調整",
                "previous_id": ids[1],
                "current_id": ids[2],
                "previous_evidence": "政策金利を調整",
                "current_evidence": "政策金利を調整",
                "note": "同じ表現が続く。",
            }
        ],
    }
    if mistake == "stale_source":
        review["source_sha256"][dates[-1]] = "f" * 64
        message = "source hash"
    elif mistake == "wrong_quote":
        review["readings"][0]["evidence"] = "金利を引き上げる"
        message = "evidence"
    elif mistake == "skipped_meeting":
        review["comparisons"][0]["previous_id"] = ids[0]
        message = "previous meeting"
    else:
        boj.validate_reading_review(snapshot, review)
        return
    with pytest.raises(ValueError, match=message):
        boj.validate_reading_review(snapshot, review)
