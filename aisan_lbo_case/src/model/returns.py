from __future__ import annotations


def calculate_moic(exit_equity_value: float, sponsor_equity: float) -> float:
    if sponsor_equity <= 0:
        raise ValueError("Sponsor equity must be positive to calculate MOIC.")
    return exit_equity_value / sponsor_equity


def calculate_irr_from_moic(moic: float, hold_years: int | float) -> float:
    if moic <= 0:
        return -1.0
    if hold_years <= 0:
        raise ValueError("Hold years must be positive.")
    return moic ** (1 / hold_years) - 1


def calculate_returns(exit_equity_value: float, sponsor_equity: float, hold_years: int | float) -> dict[str, float]:
    moic = calculate_moic(exit_equity_value, sponsor_equity)
    irr = calculate_irr_from_moic(moic, hold_years)
    return {"moic": moic, "irr": irr}
