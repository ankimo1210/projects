"""Cash-flow pricing oracle independent of the curve representation."""
import numpy as np
import pandas as pd
import pytest
from quantcurve.pricing import PricingEngine


def test_direct_discount_pricing_with_negative_rates_and_stub():
    frame=pd.DataFrame([
        dict(instrument_type='deposit',maturity_years=.25,payment_frequency=1,coupon_rate=0),
        dict(instrument_type='ois_swap',maturity_years=2.25,payment_frequency=2,coupon_rate=0),
        dict(instrument_type='bond',maturity_years=1.25,payment_frequency=2,coupon_rate=.03),
    ])
    D=lambda t:np.exp(.004*np.asarray(t)-.0002*np.asarray(t)**2)
    engine=PricingEngine(frame)
    actual=engine.quote_from_discount(D)
    expected=[(1/D(.25)-1)/.25,
              (1-D(2.25))/(.5*sum(D(np.array([.5,1.,1.5,2.])))+.25*D(2.25)),
              1.5*D(.5)+1.5*D(1.)+100.75*D(1.25)]
    np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)
    assert actual[0]<0 and D(.25)>1
    for invalid in (lambda t:np.zeros_like(t),lambda t:np.full_like(t,np.nan),lambda t:1.):
        with pytest.raises(ValueError,match='positive finite'):
            engine.quote_from_discount(invalid)
