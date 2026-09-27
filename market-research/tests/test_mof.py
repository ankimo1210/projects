from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.fetch import FetchError
from market_research.mof import CURRENT_URL, HISTORY_URL, MoFRequest, ingest_mof_jgb
from market_research.storage import ResearchStore

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)
HISTORY = """国債金利情報,,
日付,2年,10年
R8.9.24,0.5,1.2
R8.9.25,-,1.3
""".encode("cp932")
CURRENT = """国債金利情報,,
日付,2年,10年
R8.9.25,-,1.3
R8.9.26,0.6,1.4
""".encode("cp932")


class Client:
    def __init__(self, *, fail_current=False, current=CURRENT, history=HISTORY):
        self.fail_current, self.current, self.history = fail_current, current, history
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if url == HISTORY_URL:
            return self.history
        if url == CURRENT_URL:
            if self.fail_current:
                raise FetchError("network")
            return self.current
        raise AssertionError(url)


def test_both_jgb_files_form_one_snapshot_and_missing_tenor_is_not_zero(tmp_path):
    with ResearchStore(tmp_path) as store:
        result = ingest_mof_jgb(store, MoFRequest(2), client=Client(), now=lambda: NOW)
        assert [row.period_start for row in result.rows] == [date(2026, 9, 24), date(2026, 9, 26)]
        assert [row.value for row in result.rows] == [0.5, 0.6]
        assert all(row.release_at == NOW and row.vintage_kind == "snapshot" for row in result.rows)
        assert all(row.raw_hash == result.snapshot.raw_hash for row in result.rows)
        assert store.macro_view("JP_JGB_2Y", NOW - timedelta(microseconds=1), "mof_jgb") == ()
        assert len(store.macro_view("JP_JGB_2Y", NOW, "mof_jgb")) == 2


def test_current_file_failure_never_exposes_historical_partial_and_can_resume(tmp_path):
    request = MoFRequest(10)
    with ResearchStore(tmp_path) as store:
        with pytest.raises(FetchError):
            ingest_mof_jgb(store, request, client=Client(fail_current=True), now=lambda: NOW)
        assert store.macro_view("JP_JGB_10Y", NOW, "mof_jgb") == ()
        assert store.pending_snapshot(request.key).cursor == "current"
        source = Client()
        resumed = ingest_mof_jgb(store, request, client=source, now=lambda: NOW, resume=True)
        assert source.urls == [CURRENT_URL]
        assert [row.value for row in resumed.rows] == [1.2, 1.3, 1.4]


def test_overlap_conflict_is_rejected_instead_of_arbitrarily_choosing_a_file(tmp_path):
    changed = CURRENT.replace(b"1.3", b"9.9")
    with ResearchStore(tmp_path) as store, pytest.raises(ValueError, match="conflicting"):
        ingest_mof_jgb(store, MoFRequest(10), client=Client(current=changed), now=lambda: NOW)
    with ResearchStore(tmp_path) as store:
        assert store.macro_view("JP_JGB_10Y", NOW, "mof_jgb") == ()


@pytest.mark.parametrize(
    ("failed_at", "resumed_at", "old_history", "new_history", "new_current", "missing_day"),
    [
        (
            NOW,
            datetime(2026, 10, 2, 12, tzinfo=UTC),
            HISTORY,
            HISTORY + "R8.9.26,0.6,1.4\n".encode("cp932"),
            "国債金利情報,,\n日付,2年,10年\nR8.10.2,0.7,1.5\n".encode("cp932"),
            date(2026, 9, 26),
        ),
        (
            datetime(2026, 12, 31, 12, tzinfo=UTC),
            datetime(2027, 1, 2, 12, tzinfo=UTC),
            "国債金利情報,,\n日付,2年,10年\nR8.12.29,0.5,1.2\n".encode("cp932"),
            "国債金利情報,,\n日付,2年,10年\nR8.12.29,0.5,1.2\nR8.12.30,0.6,1.4\n".encode("cp932"),
            "国債金利情報,,\n日付,2年,10年\nR9.1.2,0.7,1.5\n".encode("cp932"),
            date(2026, 12, 30),
        ),
    ],
)
def test_resume_across_mof_file_rollover_refetches_history(
    tmp_path, failed_at, resumed_at, old_history, new_history, new_current, missing_day
):
    request = MoFRequest(10)
    with ResearchStore(tmp_path) as store:
        with pytest.raises(FetchError):
            ingest_mof_jgb(
                store,
                request,
                client=Client(fail_current=True, history=old_history),
                now=lambda: failed_at,
            )
        source = Client(history=new_history, current=new_current)
        result = ingest_mof_jgb(store, request, client=source, now=lambda: resumed_at, resume=True)
        assert source.urls == [HISTORY_URL, CURRENT_URL]
        assert missing_day in [row.period_start for row in result.rows]
