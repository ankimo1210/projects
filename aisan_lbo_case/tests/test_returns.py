from src.model.returns import calculate_irr_from_moic, calculate_moic, calculate_returns


def test_return_calculations_reconcile():
    moic = calculate_moic(200.0, 100.0)
    assert moic == 2.0
    irr = calculate_irr_from_moic(moic, 5)
    assert round(irr, 6) == round(2 ** (1 / 5) - 1, 6)
    result = calculate_returns(200.0, 100.0, 5)
    assert result["moic"] == moic
    assert result["irr"] == irr
