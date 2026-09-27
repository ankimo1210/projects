import json
from datetime import UTC, datetime

from market_research.cli import main
from market_research.fetch import FetchError, HttpClient


def test_macro_cli_fetches_explicitly_then_reads_snapshot_offline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FRED_API_KEY", "private-key")

    def get(self, url, *, params=None, headers=None):
        return json.dumps(
            {
                "count": 1,
                "offset": 0,
                "limit": 100000,
                "observations": [
                    {
                        "date": "2025-01-01",
                        "realtime_start": "2025-04-01",
                        "realtime_end": "9999-12-31",
                        "value": "100",
                    }
                ],
            }
        ).encode()

    monkeypatch.setattr(HttpClient, "get", get)
    base = ["--data-root", str(tmp_path)]
    args = [
        "fetch-macro",
        "--provider",
        "alfred",
        "--series-id",
        "GDP",
        "--indicator",
        "GDP",
        "--start",
        "2025-01-01",
        "--end",
        "2025-12-31",
        "--unit",
        "billions",
        "--frequency",
        "quarterly",
        "--seasonal-adjustment",
        "sa",
    ]
    assert main(base + args) == 0
    fetched = json.loads(capsys.readouterr().out)
    snapshot_id = fetched["snapshot_id"]
    assert fetched["rows"][0]["value"] == 100
    assert "private-key" not in json.dumps(fetched)

    def offline(self, url, *, params=None, headers=None):
        raise AssertionError("read command attempted network access")

    monkeypatch.setattr(HttpClient, "get", offline)
    assert (
        main([*base, "macro", "--snapshot-id", snapshot_id, "--as-of", "2025-04-02T03:59:59+00:00"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["rows"] == []
    assert (
        main([*base, "macro", "--snapshot-id", snapshot_id, "--as-of", "2025-04-02T04:00:00+00:00"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["rows"][0]["value"] == 100


def test_sec_cli_reads_filing_without_network(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SEC_USER_AGENT", "Research example@example.org")
    facts = {
        "cik": 320193,
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {
                        "USD": [
                            {
                                "end": "2025-09-27",
                                "val": 100,
                                "accn": "0000320193-25-000001",
                                "form": "10-K",
                                "filed": "2025-10-31",
                            }
                        ]
                    }
                }
            }
        },
    }
    monkeypatch.setattr(HttpClient, "get", lambda self, url, **kwargs: json.dumps(facts).encode())
    base = ["--data-root", str(tmp_path)]
    fetch = [
        "fetch-fundamentals",
        "--cik",
        "320193",
        "--taxonomy",
        "us-gaap",
        "--concept",
        "Assets",
        "--unit",
        "USD",
        "--form",
        "10-K",
    ]
    assert main(base + fetch) == 0
    snapshot_id = json.loads(capsys.readouterr().out)["snapshot_id"]
    monkeypatch.setattr(
        HttpClient,
        "get",
        lambda self, url, **kwargs: (_ for _ in ()).throw(
            AssertionError("offline read attempted network")
        ),
    )
    assert (
        main(
            [
                *base,
                "fundamentals",
                "--snapshot-id",
                snapshot_id,
                "--as-of",
                "2025-11-01T04:00:00+00:00",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["rows"][0]["value"] == 100


def test_explicit_stale_fallback_reports_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FRED_API_KEY", "private-key")
    payload = json.dumps(
        {
            "count": 1,
            "offset": 0,
            "limit": 100000,
            "observations": [
                {
                    "date": "2025-01-01",
                    "realtime_start": "2025-04-01",
                    "realtime_end": "9999-12-31",
                    "value": "100",
                }
            ],
        }
    ).encode()
    monkeypatch.setattr(HttpClient, "get", lambda self, url, **kwargs: payload)
    base = [
        "--data-root",
        str(tmp_path),
        "fetch-macro",
        "--provider",
        "alfred",
        "--series-id",
        "GDP",
        "--indicator",
        "GDP",
        "--start",
        "2025-01-01",
        "--end",
        "2025-12-31",
        "--unit",
        "billions",
        "--frequency",
        "quarterly",
        "--seasonal-adjustment",
        "sa",
    ]
    assert main(base) == 0
    capsys.readouterr()

    def fail(self, url, **kwargs):
        raise FetchError("network")

    monkeypatch.setattr(HttpClient, "get", fail)
    assert main([*base, "--allow-stale"]) == 0
    stale = json.loads(capsys.readouterr().out)
    assert stale["stale"] and stale["error"] == "network"
