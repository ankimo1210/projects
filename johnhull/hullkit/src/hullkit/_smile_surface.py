"""Private Hull GE Ch20: smile axes, surfaces, scenarios and implied distributions."""

import math


def parity_iv_details(spot, strike, rate, yield_rate, maturity, call_price, *, put_price=None):
    """European IVs and quote parity residual; input prices are never rounded.

    The default put is derived from parity. A supplied rounded put is solved
    separately, retaining its residual and IV gap. Near deep-ITM intrinsic
    values floating-point quotes can lose time value, making IV unidentifiable.
    """
    from ._index_currency import carry_implied_vol

    call_iv = carry_implied_vol(call_price, spot, strike, rate, yield_rate, maturity)
    parity_put = max(
        math.fsum(
            (
                call_price,
                strike * math.exp(-rate * maturity),
                -spot * math.exp(-yield_rate * maturity),
            )
        ),
        0,
    )
    put = parity_put if put_price is None else put_price
    # An exact deterministic call plus derived parity put is the same sigma=0
    # model. Do not use a price tolerance that would erase positive OTM quotes.
    put_iv = (
        0.0
        if put_price is None and call_iv == 0
        else carry_implied_vol(put, spot, strike, rate, yield_rate, maturity, kind="put")
    )
    return {
        "parity_put": parity_put,
        "put_price": put,
        "call_iv": call_iv,
        "put_iv": put_iv,
        "parity_residual": put - parity_put,
        "iv_difference": call_iv - put_iv,
    }
