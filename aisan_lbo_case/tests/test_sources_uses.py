from src.model.lbo_model import load_model_inputs, run_lbo_case


def test_sources_equal_uses_for_sponsor_default():
    inputs = load_model_inputs()
    assumptions = inputs["assumptions"]
    scenario = inputs["scenarios"]["Sponsor"]
    premium = assumptions["transaction_assumptions"]["default_premium"]
    summary, _ = run_lbo_case("Sponsor", premium, assumptions, scenario, inputs["market_snapshot"])
    assert round(summary["total_sources"], 6) == round(summary["total_uses"], 6)
    assert round(summary["offer_price"] * summary["diluted_shares"] / 1_000_000, 6) == round(
        summary["equity_purchase_price"], 6
    )
