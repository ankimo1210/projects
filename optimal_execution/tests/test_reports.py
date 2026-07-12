from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import optimal_execution.report as report_module
from optimal_execution.config import Config
from optimal_execution.provenance import config_fingerprint, model_fingerprint
from optimal_execution.report import build_reports


def _summary(ids: list[str], means: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "strategy_id": ids,
            "n_paths": [20] * len(ids),
            "is_mean_bps": means,
            "is_std_bps": [2.0 + i for i in range(len(ids))],
            "cvar95_bps": [m + 4.0 for m in means],
            "is_mean_ci_lo_bps": [m - 0.2 for m in means],
            "is_mean_ci_hi_bps": [m + 0.2 for m in means],
            "cleanup_qty": [10.0] * len(ids),
            "fill_rate": [0.5] * len(ids),
        }
    )


def _fake_frames() -> dict[str, pd.DataFrame]:
    schedule_rows = []
    for strategy_id, curve in {
        "twap": [1.0, 0.5, 0.0],
        "ac": [1.0, 0.35, 0.0],
        "ow": [1.0, 0.55, 0.0],
    }.items():
        for k, inventory in enumerate(curve):
            schedule_rows.append(
                {"strategy_id": strategy_id, "time_s": 900 * k, "inventory_fraction": inventory}
            )
    frontier = pd.DataFrame(
        {
            "lambda": [1e-8, 1e-6, 1e-4],
            "kappa_T": [0.1, 1.0, 10.0],
            "cost_sd_bps": [20.0, 12.0, 3.0],
            "expected_cost_bps": [2.0, 2.5, 8.0],
        }
    )
    impact_rows = []
    for name, offset in (
        ("temporary_only", 0.01),
        ("permanent_only", 0.02),
        ("transient_only", 0.03),
        ("all", 0.05),
    ):
        for k in range(3):
            impact_rows.append(
                {
                    "impact_model": name,
                    "time_s": 900 * k,
                    "execution_price": 100 - offset * (k + 1),
                    "impacted_mid": 100 - offset * k,
                    "transient_state": offset * k,
                }
            )
    classical = _summary(["twap", "ac", "ow"], [2.4, 2.1, 2.3])
    classical_path = pd.DataFrame(
        {
            "strategy_id": np.repeat(["twap", "ac", "ow"], 20),
            "is_bps": np.concatenate(
                [np.linspace(0, 5, 20), np.linspace(-0.2, 4.4, 20), np.linspace(0, 4.8, 20)]
            ),
        }
    )
    lob = _summary(["twap_mkt", "heuristic", "limit_only"], [3.0, 2.7, 3.4])
    trace = pd.DataFrame(
        {
            "strategy_id": ["heuristic"] * 4,
            "episode": [0] * 4,
            "time_s": [450, 900, 1350, 1800],
            "bid_depth": [3000, 2500, 3300, 3100],
            "ask_depth": [3200, 2900, 2400, 3400],
            "imbalance": [-0.03, -0.07, 0.16, -0.05],
            "transient_impact": [0.01, 0.03, 0.015, 0.0],
        }
    )
    reactive = _summary(["twap_reactive", "twap_replay"], [4.0, 2.8])
    reactive["mode"] = ["reactive", "replay"]
    stress_parts = []
    for regime, bump in (("in_distribution", 0.0), ("high_vol", 1.0)):
        part = _summary(
            ["twap_mkt", "ac_mkt", "heuristic", "rl_residual_s1210", "rl_free_s1210"],
            [3.0 + bump, 2.8 + bump, 2.7 + bump, 2.2 + bump, 2.4 + bump],
        )
        part["regime"] = regime
        stress_parts.append(part)
    stress = pd.concat(stress_parts, ignore_index=True)
    ablation = _summary(["full_model", "without_imbalance", "without_recent_flow"], [2.2, 2.4, 2.8])
    ablation["feature_removed"] = ["none", "imbalance", "recent_flow"]
    ablation["delta_vs_full_bps"] = [0.0, 0.2, 0.6]
    miss = _summary(
        ["twap_mkt", "ac_mkt", "heuristic", "rl_residual_s1210", "rl_free_s1210"],
        [5.0, 4.8, 3.2, 3.6, 3.4],
    )
    return {
        "schedules": pd.DataFrame(schedule_rows),
        "frontier": frontier,
        "impact": pd.DataFrame(impact_rows),
        "classical_path": classical_path,
        "classical": classical,
        "lob_trace": trace,
        "lob": lob,
        "reactive": reactive,
        "stress": stress,
        "ablation": ablation,
        "misspecification": miss,
    }


def test_artifact_fingerprint_validation_rejects_stale_inputs(cfg: Config) -> None:
    current = pd.DataFrame(
        {
            "config_fingerprint": [config_fingerprint(cfg)],
            "model_fingerprint": [model_fingerprint()],
        }
    )
    report_module._validate_artifact_fingerprints({"current": current}, cfg)

    stale_cfg = cfg.with_overrides({"annualized_volatility": 0.4})
    with pytest.raises(ValueError, match="do not match"):
        report_module._validate_artifact_fingerprints({"stale": current}, stale_cfg)
    with pytest.raises(ValueError, match="missing fingerprint"):
        report_module._validate_artifact_fingerprints({"legacy": pd.DataFrame({"x": [1]})}, cfg)


def test_bilingual_reports_generate_offline_with_identical_numbers(
    cfg: Config, tmp_path: Path, monkeypatch
) -> None:
    trial = cfg.with_overrides(
        {"artifacts_dir": str(tmp_path / "artifacts"), "reports_dir": str(tmp_path / "reports")}
    )
    frames = _fake_frames()
    monkeypatch.setattr(report_module, "_artifact_frames", lambda _: frames)
    outputs = build_reports(trial)
    assert set(outputs) == {"en", "ja"}
    texts = {locale: path.read_text(encoding="utf-8") for locale, path in outputs.items()}
    assert "Market Microstructure and Optimal Execution" in texts["en"]
    assert "市場マイクロストラクチャーと最適執行" in texts["ja"]
    hashes = [re.search(r'"sha256": "([0-9a-f]+)"', text).group(1) for text in texts.values()]
    assert len(set(hashes)) == 1
    for text in texts.values():
        assert "cdn.plot.ly" not in text
        assert "2.100" in text
        assert len(text) > 100_000
