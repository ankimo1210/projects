import json

import numpy as np
import pandas as pd
import pytest
from bond_timing import cli


def write(results, name: str, payload: dict) -> None:
    (results / f"{name}.json").write_text(json.dumps(payload))


def test_stage_order_is_enforced(tmp_path):
    with pytest.raises(cli.StageError, match=r"dev\.json"):
        cli.check_ready("g1", tmp_path, prereg_commit="abc")
    write(tmp_path, "dev", {"p1": "slope"})
    with pytest.raises(cli.StageError, match="PREREG"):
        cli.check_ready("g1", tmp_path, prereg_commit="")
    assert cli.check_ready("g1", tmp_path, prereg_commit="abc")["dev"]["p1"] == "slope"
    assert cli.check_ready("g0", tmp_path, prereg_commit="") == {}


def test_oos_a_requires_prereg_and_a_passed_g1(tmp_path):
    write(tmp_path, "dev", {"p1": "slope"})
    write(tmp_path, "g1", {"pass": False})
    with pytest.raises(cli.StageError, match="G1 did not pass"):
        cli.check_ready("oos-a", tmp_path, prereg_commit="abc")
    write(tmp_path, "g1", {"pass": True})
    assert set(cli.check_ready("oos-a", tmp_path, prereg_commit="abc")) == {"dev", "g1"}


def test_oos_b_runs_once_without_a_reason(tmp_path):
    assert cli.oos_b_target(tmp_path, None) == ("oos_b", {})
    cli.take_lock(tmp_path, "abc123")
    with pytest.raises(cli.StageError, match="already ran"):
        cli.oos_b_target(tmp_path, None)
    write(tmp_path, "oos_b", {"verdict": "no_usable_signal"})
    name, extra = cli.oos_b_target(tmp_path, "fixed a data error")
    assert name == "oos_b_rerun_1"
    assert extra == {"rerun_reason": "fixed a data error", "verdict_of_record": "no_usable_signal"}


def test_results_serialise_numpy_values_and_periods(tmp_path):
    result = {
        "a": np.float64(1.5),
        "b": pd.Period("2000-01", "M"),
        "c": (1, 2),
        "d": np.bool_(True),
    }
    path = cli.write_result("x", result, tmp_path, {"git_commit": "abc"})
    assert json.loads(path.read_text()) == {
        "meta": {"git_commit": "abc"},
        "a": 1.5,
        "b": "2000-01",
        "c": [1, 2],
        "d": True,
    }
