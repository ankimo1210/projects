from pathlib import Path

import pytest

from quantcurve.cleaning import clean_market_data
from quantcurve.io import load_market_data
from quantcurve.fitting import fit_curve

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def raw():
    return load_market_data(ROOT / "data" / "market_observations.csv")


@pytest.fixture(scope="session")
def clean(raw):
    return clean_market_data(raw, "2026-01-15")


@pytest.fixture(scope="session")
def fitted(clean):
    return fit_curve(clean[0], smoothing=.001)
