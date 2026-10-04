"""Private Hull §30.2 frozen-coefficient timing adjustment (30.2–30.3)."""

import math

import numpy as np


def frozen_ratio_density(brownian_driver, signed_ratio_loading, observation):
    """Raw Gaussian numeraire-ratio density, with Var(driver)=observation.

    The loading is signed. This is exact for constant coefficients, while
    Hull's forward-rate-to-ratio loading freezes stochastic coefficients.
    It is not an exact price in a general state-dependent short-rate model.
    """
    if observation < 0:
        raise ValueError("nonnegative observation time required")
    return np.exp(
        signed_ratio_loading * np.asarray(brownian_driver)
        - 0.5 * signed_ratio_loading**2 * observation
    )


def timing_adjusted_payment(
    forward_value,
    value_volatility,
    rate_volatility,
    correlation,
    forward_rate,
    observation,
    payment,
    payment_discount,
    frequency=1,
):
    """Expected value and PV at a later payment, with explicit compounding.

    Rate vol is relative. Ratio loading is -sigma_R*R_F*(payment-observation)
    /(1+R_F/frequency); correlation is between the value and rate drivers.
    A negative loading and a reversed correlation must not both be introduced
    as separate sign corrections. The supplied discount belongs to payment.
    """
    if observation < 0 or payment < observation or frequency <= 0:
        raise ValueError("ordered nonnegative times and positive frequency required")
    if min(value_volatility, rate_volatility) < 0 or abs(correlation) > 1:
        raise ValueError("nonnegative volatilities and correlation in [-1,1] required")
    if 1 + forward_rate / frequency <= 0 or payment_discount <= 0:
        raise ValueError("positive compounding base and payment discount required")
    loading = (
        -rate_volatility * forward_rate * (payment - observation) / (1 + forward_rate / frequency)
    )
    factor = math.exp(correlation * value_volatility * loading * observation)
    expected = forward_value * factor
    return {
        "signed_ratio_loading": loading,
        "factor": factor,
        "expected_value": expected,
        "payment_discount": payment_discount,
        "pv": expected * payment_discount,
    }
