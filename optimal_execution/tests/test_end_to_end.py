from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from optimal_execution.config import Config
from optimal_execution.experiments import run_classical, run_lob


@pytest.mark.slow
def test_tiny_classical_and_lob_pipeline(cfg: Config, tmp_path: Path) -> None:
    trial = cfg.with_overrides(
        {
            "n_decision_steps": 4,
            "n_scenarios": 8,
            "n_test_scenarios": 12,
            "mc_chunk_size": 6,
            "lob_eval_episodes": 4,
            "lob_example_episodes": 1,
            "artifacts_dir": str(tmp_path / "artifacts"),
            "reports_dir": str(tmp_path / "reports"),
        }
    )
    classical = run_classical(trial)
    lob = run_lob(trial)
    assert set(classical["summary"]["strategy_id"]) == {
        "immediate",
        "twap",
        "vwap",
        "pov",
        "ac",
        "ow",
    }
    assert set(lob["summary"]["strategy_id"]) == {
        "twap_mkt",
        "ac_mkt",
        "pov_mkt",
        "limit_only",
        "heuristic",
    }
    data = tmp_path / "artifacts" / "data"
    metrics = tmp_path / "artifacts" / "metrics"
    figures = tmp_path / "artifacts" / "figures"
    assert (data / "classical_path_tca.parquet").exists()
    assert (data / "lob_path_tca.parquet").exists()
    assert (metrics / "config_snapshot.json").exists()
    assert (figures / "efficient_frontier.png").exists()
    frame = pd.read_parquet(data / "lob_path_tca.parquet")
    assert frame["terminal_inventory"].abs().max() < 1e-6
    assert frame["model_parameters_json"].str.contains("resilience_rho").all()
