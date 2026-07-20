from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from jhrmbs.config import AppConfig
from jhrmbs.report import _metrics_table, _split_disagreement_note, generate_issue_report


def _metrics(time_winner: str, vintage_winner: str) -> pd.DataFrame:
    rows = []
    for split, winner in (("time", time_winner), ("vintage", vintage_winner)):
        for model_name in ("fixed_psj", "seasoning", "rate", "full"):
            rows.append(
                {
                    "split": split,
                    "model": model_name,
                    "test_rows": 100,
                    "weighted_rmse_cpr_pct": 1.0 if model_name == winner else 2.0,
                    "weighted_mae_cpr_pct": 0.8,
                    "cashflow_cumulative_principal_mae_pct": 1.0,
                    "truncated_wal_mae_years": 0.02,
                }
            )
    return pd.DataFrame(rows)


def test_metrics_table_shows_test_rows() -> None:
    rendered = _metrics_table(_metrics("rate", "rate"), "rate")
    assert "test 行数" in rendered


def test_split_disagreement_note_flags_reversal() -> None:
    note = _split_disagreement_note(_metrics("rate", "seasoning"))
    assert note is not None
    assert "rate" in note and "seasoning" in note

    assert _split_disagreement_note(_metrics("rate", "rate")) is None


def test_generate_issue_report_renders_sensitivity_and_reversal_warning(
    pipeline_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    import jhrmbs.forecast as forecast_module
    import jhrmbs.report as report_module

    calls = {"count": 0}
    original = forecast_module.forecast_issue

    def _counting(*args: Any, **kwargs: Any) -> pd.DataFrame:
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(report_module, "forecast_issue", _counting)
    monkeypatch.setattr(
        "jhrmbs.cashflow_service.forecast_issue", _counting
    )
    path = generate_issue_report(pipeline_config, "JHF-001")
    html_text = path.read_text(encoding="utf-8")
    assert "感応度" in html_text
    assert "split 間で最良モデルが一致しません" in html_text
    # base forecast once + two sensitivity shifts; the model cashflow reuses the base
    assert calls["count"] == 3
