"""The allocation report must not present a stale transaction ledger as current."""

import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_dashboard", PROJECT_ROOT / "scripts/build_dashboard.py"
)
build_dashboard = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(build_dashboard)


@pytest.mark.parametrize("repriced", [False, True])
def test_pending_snapshot_ignores_the_unreconciled_ledger(tmp_path, monkeypatch, repriced):
    snapshot = json.loads((PROJECT_ROOT / "data/portfolio.example.json").read_text())
    snapshot["capture_status"] = {"history_reconciled": False}
    if repriced:
        spec = importlib.util.spec_from_file_location(
            "reprice_snapshot_for_dashboard", PROJECT_ROOT / "scripts/reprice_snapshot.py"
        )
        reprice = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(reprice)
        quotes = {
            ticker: {"close": Decimal(str(row["price"])), "date": "2026-09-11"}
            for row in snapshot["positions"]
            if row.get("quantity") is not None
            and (ticker := reprice.market_symbol(row["symbol"], row["currency"])) is not None
        }
        snapshot = reprice.reprice(snapshot, quotes, Decimal("150"), "2026-09-11")
    input_path = tmp_path / "snapshot.json"
    input_path.write_text(json.dumps(snapshot), encoding="utf-8")
    # Even a legacy ledger without usable reconciliation must not enter this report.
    ledger = tmp_path / "stale-ledger.json"
    ledger.write_text("{}", encoding="utf-8")
    output = tmp_path / "report.html"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_dashboard.py",
            "--input",
            str(input_path),
            "--ledger",
            str(ledger),
            "--output",
            str(output),
            "--artifact-only",
            "--no-analysis-reference",
            "--no-factor-risk",
        ],
    )
    assert build_dashboard.main() == 0
    artifact = json.loads((tmp_path / "artifact.json").read_text(encoding="utf-8"))
    assert "ledger_performance" not in artifact["snapshot"]["datasets"]
