from src.model.lbo_model import run_all_cases
from src.utils.validation import (
    validate_ev_bridge,
    validate_exit_equity,
    validate_share_price_bridge,
    validate_sources_uses,
)


def test_lbo_model_bridges_reconcile():
    summaries, details = run_all_cases()
    assert not summaries.empty
    for row in summaries.to_dict("records"):
        validate_sources_uses(row)
        validate_ev_bridge(row)
        validate_share_price_bridge(row)
        validate_exit_equity(row)
    assert (details["ending_debt"] >= -1e-9).all()
    for _, row in summaries.iterrows():
        detail = details[(details["scenario"] == row["scenario"]) & (details["premium"] == row["premium"])]
        assert (detail["ending_cash"] >= row["min_cash"] - 1e-9).all()
