"""Private Hull Ch7 swap cash, calibration and valuation with explicit sign conventions."""

import numpy as np


def interest_swap_cash(notional, fixed_rate, reference_rates, accruals, *, receive="floating"):
    """Signed interest exchange on one notional; no principal cash is exchanged.

    Reference rates are period-simple annual quotes, already known/forecast by the
    caller. OIS compounding and LIBOR fixing timing are not inferred from this table.
    """
    rates = np.atleast_1d(np.asarray(reference_rates, dtype=float))
    tau = np.broadcast_to(np.asarray(accruals, dtype=float), rates.shape)
    if (
        not np.isfinite([notional, fixed_rate]).all()
        or not np.isfinite(rates).all()
        or not np.isfinite(tau).all()
        or notional < 0
        or np.any(tau <= 0)
        or receive not in ("fixed", "floating")
    ):
        raise ValueError("valid notional/rates/accruals and receive direction required")
    sign = 1 if receive == "floating" else -1
    floating = sign * notional * tau * rates
    fixed = -sign * notional * tau * fixed_rate
    return {"floating": floating, "fixed": fixed, "net": floating + fixed}
